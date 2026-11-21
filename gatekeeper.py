#!/usr/bin/env python3
"""
Gatekeeper: AI Agent Governance for Online Store (Amazon)
Enrolment: PGD202567787

A command-line program that receives and evaluates requests from customers' AI agents.
Validates requests against governance rules, manages agent registration/revocation,
records audit trails in CSV format, and runs built-in test suites.
"""

import sys
import os
import json
import csv
from datetime import datetime

# Mandatory Enrolment Identifier
ENROLMENT_ID = "PGD202567787"

# File storage paths (co-located with script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_FILE = os.path.join(BASE_DIR, "agents.json")
AUDIT_LOG_FILE = os.path.join(BASE_DIR, "audit_log.csv")

VALID_ACTIONS = ("view_order", "place_order", "return", "refund")


def load_agents() -> dict:
    """Load agents mapping from agents.json."""
    if not os.path.exists(AGENTS_FILE):
        return {}
    try:
        with open(AGENTS_FILE, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                # Normalize list of agent dicts if found
                return {item["name"]: item for item in data if isinstance(item, dict) and "name" in item}
            return {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_agents(agents: dict) -> None:
    """Save agents mapping to agents.json."""
    with open(AGENTS_FILE, mode="w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2)


def find_agent(agent_name: str, agents: dict):
    """
    Look up agent by name (exact match first, then case-insensitive).
    Returns (matched_key, agent_dict) or (None, None).
    """
    if not agent_name:
        return None, None
    name_str = str(agent_name).strip()
    if name_str in agents:
        return name_str, agents[name_str]
    for key, val in agents.items():
        if key.strip().lower() == name_str.lower():
            return key, val
    return None, None


def register_agent(name: str) -> dict:
    """Register or reactivate an AI agent."""
    name = str(name).strip()
    agents = load_agents()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing_key, existing_data = find_agent(name, agents)
    target_key = existing_key if existing_key else name

    registered_at = (
        existing_data.get("registered_at")
        if (existing_data and existing_data.get("registered_at"))
        else now_ts
    )

    agent_entry = {
        "name": target_key,
        "status": "ACTIVE",
        "registered_at": registered_at,
        "revoked_at": None,
    }
    agents[target_key] = agent_entry
    save_agents(agents)
    return agent_entry


def revoke_agent(name: str) -> dict:
    """Revoke an AI agent."""
    name = str(name).strip()
    agents = load_agents()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing_key, existing_data = find_agent(name, agents)
    target_key = existing_key if existing_key else name

    registered_at = (
        existing_data.get("registered_at")
        if (existing_data and existing_data.get("registered_at"))
        else now_ts
    )

    agent_entry = {
        "name": target_key,
        "status": "REVOKED",
        "registered_at": registered_at,
        "revoked_at": now_ts,
    }
    agents[target_key] = agent_entry
    save_agents(agents)
    return agent_entry


def evaluate_request(customer: str, agent: str, action: str, amount_raw: any):
    """
    Evaluate agent request strictly according to rules 1-7 in order.
    Returns: (decision, rule_number, reason)
    """
    agents = load_agents()
    _, agent_data = find_agent(agent, agents)

    # 1) revoked agent = BLOCK
    if agent_data and str(agent_data.get("status", "")).strip().upper() == "REVOKED":
        return "BLOCK", 1, "revoked agent"

    # 2) unknown agent = BLOCK
    if not agent_data:
        return "BLOCK", 2, "unknown agent"

    # 3) missing customer, invalid action or negative amount = BLOCK
    customer_str = str(customer).strip() if customer is not None else ""
    is_missing_customer = (
        customer_str == "" or customer_str.lower() in ("none", "null")
    )

    action_str = str(action).strip().lower() if action is not None else ""
    is_invalid_action = action_str not in VALID_ACTIONS

    try:
        # Strip potential currency prefixes/commas
        cleaned_amount = (
            str(amount_raw)
            .strip()
            .replace("Rs.", "")
            .replace("Rs", "")
            .replace("₹", "")
            .replace(",", "")
            .strip()
        )
        amount = float(cleaned_amount)
        is_negative_or_invalid_amount = amount < 0
    except (ValueError, TypeError):
        is_negative_or_invalid_amount = True
        amount = None

    if is_missing_customer or is_invalid_action or is_negative_or_invalid_amount:
        return "BLOCK", 3, "missing customer, invalid action or negative amount"

    # 4) view_order = ALLOW
    if action_str == "view_order":
        return "ALLOW", 4, "view_order"

    # 5) refund = ASK CUSTOMER
    if action_str == "refund":
        return "ASK CUSTOMER", 5, "refund"

    # 6) place_order or return up to Rs 5000 = ALLOW
    if action_str in ("place_order", "return") and amount <= 5000:
        return "ALLOW", 6, "place_order or return up to Rs 5000"

    # 7) place_order or return above Rs 5000 = ASK CUSTOMER
    if action_str in ("place_order", "return") and amount > 5000:
        return "ASK CUSTOMER", 7, "place_order or return above Rs 5000"

    # Fallback (safety catch)
    return "BLOCK", 3, "missing customer, invalid action or negative amount"


def log_audit(request_str: str, decision: str, rule_str: str) -> None:
    """Append decision to audit_log.csv with columns: time, request, decision, rule."""
    file_exists = os.path.exists(AUDIT_LOG_FILE) and os.path.getsize(AUDIT_LOG_FILE) > 0
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(AUDIT_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["time", "request", "decision", "rule"])
        writer.writerow([now_ts, request_str, decision, rule_str])


def process_request(customer: str, agent: str, action: str, amount_raw: any):
    """Evaluate request, record in audit_log.csv, and return (decision, rule_num, reason)."""
    decision, rule_num, reason = evaluate_request(customer, agent, action, amount_raw)
    rule_str = f"Rule {rule_num}: {reason}"
    request_str = f"{customer} {agent} {action} {amount_raw}".strip()
    log_audit(request_str, decision, rule_str)
    return decision, rule_num, reason


def run_tests() -> bool:
    """
    Run 6 test cases required by specification:
    1. known agent view order -> ALLOW (Rule 4)
    2. unknown agent -> BLOCK (Rule 2)
    3. order above limit -> ASK CUSTOMER (Rule 7)
    4. order below limit -> ALLOW (Rule 6)
    5. revoked agent -> BLOCK (Rule 1)
    6. refund -> ASK CUSTOMER (Rule 5)
    Prints expected vs actual with PASS or FAIL.
    """
    known_agent = "ShoppingAssistant"
    revoked_agent = "OldCompromisedBot"
    unknown_agent = "RogueExternalBot"

    # Seed test agents into agents.json
    agents = load_agents()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    agents[known_agent] = {
        "name": known_agent,
        "status": "ACTIVE",
        "registered_at": now_ts,
        "revoked_at": None,
    }
    agents[revoked_agent] = {
        "name": revoked_agent,
        "status": "REVOKED",
        "registered_at": now_ts,
        "revoked_at": now_ts,
    }
    if unknown_agent in agents:
        del agents[unknown_agent]

    save_agents(agents)

    test_cases = [
        {
            "name": "known agent view order",
            "customer": "Customer_A",
            "agent": known_agent,
            "action": "view_order",
            "amount": 0,
            "expected_decision": "ALLOW",
            "expected_rule": 4,
            "expected_reason": "view_order",
        },
        {
            "name": "unknown agent",
            "customer": "Customer_B",
            "agent": unknown_agent,
            "action": "place_order",
            "amount": 1000,
            "expected_decision": "BLOCK",
            "expected_rule": 2,
            "expected_reason": "unknown agent",
        },
        {
            "name": "order above limit",
            "customer": "Customer_C",
            "agent": known_agent,
            "action": "place_order",
            "amount": 7500,
            "expected_decision": "ASK CUSTOMER",
            "expected_rule": 7,
            "expected_reason": "place_order or return above Rs 5000",
        },
        {
            "name": "order below limit",
            "customer": "Customer_D",
            "agent": known_agent,
            "action": "place_order",
            "amount": 2500,
            "expected_decision": "ALLOW",
            "expected_rule": 6,
            "expected_reason": "place_order or return up to Rs 5000",
        },
        {
            "name": "revoked agent",
            "customer": "Customer_E",
            "agent": revoked_agent,
            "action": "place_order",
            "amount": 1000,
            "expected_decision": "BLOCK",
            "expected_rule": 1,
            "expected_reason": "revoked agent",
        },
        {
            "name": "refund",
            "customer": "Customer_F",
            "agent": known_agent,
            "action": "refund",
            "amount": 1200,
            "expected_decision": "ASK CUSTOMER",
            "expected_rule": 5,
            "expected_reason": "refund",
        },
    ]

    all_passed = True
    print("\n--- Running Gatekeeper Verification Suite (6 Cases) ---")

    for idx, tc in enumerate(test_cases, start=1):
        actual_decision, actual_rule, actual_reason = process_request(
            tc["customer"], tc["agent"], tc["action"], tc["amount"]
        )

        expected_desc = f"{tc['expected_decision']} (Rule {tc['expected_rule']}: {tc['expected_reason']})"
        actual_desc = f"{actual_decision} (Rule {actual_rule}: {actual_reason})"

        is_pass = (
            actual_decision == tc["expected_decision"]
            and actual_rule == tc["expected_rule"]
        )

        if not is_pass:
            all_passed = False

        status_str = "PASS" if is_pass else "FAIL"

        print(f"\nCase {idx}: {tc['name']}")
        print(f"  Expected: {expected_desc}")
        print(f"  Actual:   {actual_desc}")
        print(f"  Expected vs Actual: [{expected_desc}] vs [{actual_desc}] -> {status_str}")
        print(f"  Status:   {status_str}")

    print("\n" + "=" * 50)
    print(f"Test Suite Result: {'ALL PASS' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 50 + "\n")
    return all_passed


def print_usage():
    """Print command line usage guide."""
    print("Usage:")
    print("  python gatekeeper.py register NAME")
    print("  python gatekeeper.py revoke NAME")
    print("  python gatekeeper.py request CUSTOMER AGENT ACTION AMOUNT")
    print("  python gatekeeper.py test")
    print("\nActions:")
    print("  view_order, place_order, return, refund")


def main():
    # Print Enrolment ID every time the program runs
    print(f"Enrolment: {ENROLMENT_ID}")

    args = sys.argv[1:]
    if not args:
        print_usage()
        return

    cmd = args[0].strip().lower()

    if cmd == "register":
        if len(args) < 2:
            print("Error: Missing agent name. Usage: python gatekeeper.py register NAME")
            sys.exit(1)
        name = args[1]
        register_agent(name)
        print(f"Agent '{name}' registered successfully.")

    elif cmd == "revoke":
        if len(args) < 2:
            print("Error: Missing agent name. Usage: python gatekeeper.py revoke NAME")
            sys.exit(1)
        name = args[1]
        revoke_agent(name)
        print(f"Agent '{name}' revoked successfully.")

    elif cmd == "request":
        if len(args) < 5:
            # If arguments are missing, evaluate as missing fields to trigger Rule 3
            customer = args[1] if len(args) > 1 else ""
            agent = args[2] if len(args) > 2 else ""
            action = args[3] if len(args) > 3 else ""
            amount = args[4] if len(args) > 4 else ""
        else:
            customer, agent, action, amount = args[1], args[2], args[3], args[4]

        decision, rule_num, reason = process_request(customer, agent, action, amount)
        print(f"Decision: {decision}")
        print(f"Rule: Rule {rule_num}")
        print(f"Reason: {reason}")

    elif cmd == "test":
        success = run_tests()
        if not success:
            sys.exit(1)

    else:
        print(f"Error: Unknown command '{args[0]}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
