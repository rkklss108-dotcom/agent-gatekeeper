#!/usr/bin/env python3
"""
Amazon AI Agent Gatekeeper - Web Dashboard
Enrolment: PGD202567787

A lightweight web dashboard built using only the Python standard library (http.server).
Imports governance logic directly from gatekeeper.py.
Runs at http://127.0.0.1:5000
"""

import sys
import os
import json
import csv
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Import governance logic directly from gatekeeper.py
try:
    from gatekeeper import (
        ENROLMENT_ID,
        load_agents,
        save_agents,
        register_agent,
        revoke_agent,
        evaluate_request,
        process_request,
        AUDIT_LOG_FILE,
        AGENTS_FILE,
        VALID_ACTIONS,
    )
except ImportError:
    # Ensure current directory is in path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gatekeeper import (
        ENROLMENT_ID,
        load_agents,
        save_agents,
        register_agent,
        revoke_agent,
        evaluate_request,
        process_request,
        AUDIT_LOG_FILE,
        AGENTS_FILE,
        VALID_ACTIONS,
    )

HOST = "127.0.0.1"
PORT = 5000


def get_audit_log_records() -> list:
    """Read all entries from audit_log.csv."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    records = []
    try:
        with open(AUDIT_LOG_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    except Exception:
        pass
    return records


def compute_summary_metrics() -> dict:
    """Compute summary card metrics from agents.json and audit_log.csv."""
    agents = load_agents()
    total_agents = len(agents)
    active_agents = sum(
        1 for a in agents.values() if str(a.get("status", "")).upper() == "ACTIVE"
    )
    revoked_agents = sum(
        1 for a in agents.values() if str(a.get("status", "")).upper() == "REVOKED"
    )

    logs = get_audit_log_records()
    allow_count = sum(
        1 for r in logs if str(r.get("decision", "")).strip().upper() == "ALLOW"
    )
    ask_customer_count = sum(
        1
        for r in logs
        if str(r.get("decision", "")).strip().upper() == "ASK CUSTOMER"
    )
    block_count = sum(
        1 for r in logs if str(r.get("decision", "")).strip().upper() == "BLOCK"
    )

    return {
        "total_agents": total_agents,
        "active_agents": active_agents,
        "revoked_agents": revoked_agents,
        "allow_count": allow_count,
        "ask_customer_count": ask_customer_count,
        "block_count": block_count,
    }


def execute_dashboard_tests() -> list:
    """Execute the 6 required test cases and return structured results."""
    known_agent = "ShoppingAssistant"
    revoked_agent = "OldCompromisedBot"
    unknown_agent = "RogueExternalBot"

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

    results = []
    for tc in test_cases:
        actual_decision, actual_rule, actual_reason = process_request(
            tc["customer"], tc["agent"], tc["action"], tc["amount"]
        )
        expected_desc = (
            f"{tc['expected_decision']} (Rule {tc['expected_rule']}: {tc['expected_reason']})"
        )
        actual_desc = f"{actual_decision} (Rule {actual_rule}: {actual_reason})"
        is_pass = (
            actual_decision == tc["expected_decision"]
            and actual_rule == tc["expected_rule"]
        )
        results.append(
            {
                "name": tc["name"],
                "expected": expected_desc,
                "actual": actual_desc,
                "status": "PASS" if is_pass else "FAIL",
            }
        )
    return results


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Amazon AI Agent Gatekeeper Dashboard</title>
  <style>
    :root {
      --amazon-dark: #131921;
      --amazon-subdark: #232f3e;
      --amazon-orange: #ff9900;
      --amazon-yellow: #febd69;
      --bg-gray: #f8f9fa;
      --card-bg: #ffffff;
      --border-color: #e5e7eb;
      --text-main: #1f2937;
      --text-muted: #6b7280;
      --color-allow: #10b981;
      --color-block: #ef4444;
      --color-ask: #f59e0b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg-gray); color: var(--text-main); min-height: 100vh; padding-bottom: 50px; }

    /* Top Navigation Header */
    header {
      background-color: var(--amazon-dark);
      color: #ffffff;
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.15);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 1.35rem;
      font-weight: 700;
      letter-spacing: -0.5px;
    }
    .brand-title span.amazon { color: var(--amazon-orange); }
    .enrolment-pill {
      background-color: var(--amazon-subdark);
      border: 1px solid #374151;
      color: var(--amazon-yellow);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 0.88rem;
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    .container {
      max-width: 1200px;
      margin: 24px auto;
      padding: 0 16px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Summary Cards */
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
    }
    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 18px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .metric-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: 0.5px;
    }
    .metric-value {
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-main);
    }
    .metric-card.allow .metric-value { color: var(--color-allow); }
    .metric-card.ask .metric-value { color: var(--color-ask); }
    .metric-card.block .metric-value { color: var(--color-block); }

    /* Action Grid */
    .action-grid {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 24px;
    }
    @media (max-width: 850px) {
      .action-grid { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 22px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--amazon-subdark);
    }

    /* Forms */
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    label {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-main);
    }
    input, select {
      padding: 10px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 0.95rem;
      background-color: #fff;
    }
    input:focus, select:focus {
      outline: none;
      border-color: var(--amazon-orange);
      box-shadow: 0 0 0 2px rgba(255, 153, 0, 0.2);
    }
    .btn {
      padding: 10px 18px;
      border: none;
      border-radius: 6px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.15s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .btn-primary {
      background-color: var(--amazon-orange);
      color: #111827;
    }
    .btn-primary:hover { background-color: #e68a00; }
    .btn-danger {
      background-color: #fee2e2;
      color: #dc2626;
      border: 1px solid #fca5a5;
    }
    .btn-danger:hover { background-color: #fecaca; }
    .btn-dark {
      background-color: var(--amazon-subdark);
      color: #ffffff;
    }
    .btn-dark:hover { background-color: #111827; }

    /* Result Banner */
    .result-banner {
      margin-top: 16px;
      padding: 16px;
      border-radius: 8px;
      display: none;
      border-left: 5px solid transparent;
    }
    .result-banner.ALLOW {
      background-color: #ecfdf5;
      border-color: var(--color-allow);
      color: #065f46;
    }
    .result-banner.ASK {
      background-color: #fffbeb;
      border-color: var(--color-ask);
      color: #92400e;
    }
    .result-banner.BLOCK {
      background-color: #fef2f2;
      border-color: var(--color-block);
      color: #991b1b;
    }
    .result-header {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }
    .result-detail {
      font-size: 0.9rem;
    }

    /* Tables */
    .table-container {
      overflow-x: auto;
      max-height: 380px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.88rem;
    }
    th {
      background-color: #f9fafb;
      padding: 10px 14px;
      font-weight: 600;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
    }
    td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-color);
      vertical-align: middle;
    }
    tr:hover td { background-color: #fcfcfc; }

    /* Badges */
    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.3px;
    }
    .badge-ALLOW { background: #d1fae5; color: #065f46; }
    .badge-ASK { background: #fef3c7; color: #92400e; }
    .badge-BLOCK { background: #fee2e2; color: #991b1b; }
    .badge-ACTIVE { background: #d1fae5; color: #065f46; }
    .badge-REVOKED { background: #fee2e2; color: #991b1b; }

    /* Test Results */
    .test-box {
      margin-top: 16px;
      display: none;
    }
    .test-row {
      padding: 10px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.88rem;
    }
    .test-row:last-child { border-bottom: none; }
    .test-details { display: flex; flex-direction: column; gap: 2px; }
    .test-name { font-weight: 600; }
    .test-meta { color: var(--text-muted); font-size: 0.8rem; }
    .badge-PASS { background-color: #10b981; color: white; }
    .badge-FAIL { background-color: #ef4444; color: white; }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header>
    <div class="brand-title">
      🛒 <span class="amazon">Amazon</span> AI Agent Gatekeeper
    </div>
    <div class="enrolment-pill">
      Enrolment: PGD202567787
    </div>
  </header>

  <div class="container">

    <!-- Summary Cards -->
    <div class="summary-grid">
      <div class="metric-card">
        <span class="metric-title">Total Agents</span>
        <span class="metric-value" id="total-agents">-</span>
      </div>
      <div class="metric-card">
        <span class="metric-title">Active Agents</span>
        <span class="metric-value" id="active-agents" style="color: var(--color-allow);">-</span>
      </div>
      <div class="metric-card">
        <span class="metric-title">Revoked Agents</span>
        <span class="metric-value" id="revoked-agents" style="color: var(--color-block);">-</span>
      </div>
      <div class="metric-card allow">
        <span class="metric-title">ALLOW Count</span>
        <span class="metric-value" id="allow-count">-</span>
      </div>
      <div class="metric-card ask">
        <span class="metric-title">ASK CUSTOMER</span>
        <span class="metric-value" id="ask-count">-</span>
      </div>
      <div class="metric-card block">
        <span class="metric-title">BLOCK Count</span>
        <span class="metric-value" id="block-count">-</span>
      </div>
    </div>

    <!-- Main Workspace Grid -->
    <div class="action-grid">

      <!-- Check Request Form -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">🔍 Check Agent Request</h2>
          <span style="font-size:0.8rem; color:var(--text-muted);">Rules 1–7 Order</span>
        </div>
        <form id="check-form" onsubmit="submitRequest(event)">
          <div class="form-row">
            <div class="form-group">
              <label for="req-customer">Customer</label>
              <input type="text" id="req-customer" placeholder="e.g. Asha" required>
            </div>
            <div class="form-group">
              <label for="req-agent">Agent Name</label>
              <input type="text" id="req-agent" placeholder="e.g. MyShopper" required>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="req-action">Action</label>
              <select id="req-action">
                <option value="view_order">view_order (Rule 4)</option>
                <option value="place_order">place_order (Rules 6/7)</option>
                <option value="return">return (Rules 6/7)</option>
                <option value="refund">refund (Rule 5)</option>
              </select>
            </div>
            <div class="form-group">
              <label for="req-amount">Amount (Rupees ₹)</label>
              <input type="number" id="req-amount" placeholder="0" min="0" step="any" value="0">
            </div>
          </div>
          <button type="submit" class="btn btn-primary" style="width: 100%;">Evaluate Request</button>
        </form>

        <!-- Evaluation Result Banner -->
        <div id="result-banner" class="result-banner">
          <div class="result-header">
            <span id="res-decision">DECISION</span>
            <span id="res-rule" style="font-size: 0.95rem; font-weight: normal;">Rule -</span>
          </div>
          <div class="result-detail" id="res-reason">Reason details...</div>
        </div>
      </div>

      <!-- Agent Management -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">🤖 Manage AI Agents</h2>
        </div>
        <form id="register-form" onsubmit="submitRegister(event)" style="margin-bottom: 20px;">
          <div class="form-group">
            <label for="reg-name">Register New Agent</label>
            <div style="display: flex; gap: 8px;">
              <input type="text" id="reg-name" placeholder="Agent Name" style="flex: 1;" required>
              <button type="submit" class="btn btn-dark">Register</button>
            </div>
          </div>
        </form>

        <form id="revoke-form" onsubmit="submitRevoke(event)">
          <div class="form-group">
            <label for="rev-name">Revoke Agent</label>
            <div style="display: flex; gap: 8px;">
              <input type="text" id="rev-name" placeholder="Agent Name to Revoke" style="flex: 1;" required>
              <button type="submit" class="btn btn-danger">Revoke</button>
            </div>
          </div>
        </form>

        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border-color);">
          <button type="button" class="btn btn-primary" style="width: 100%;" onclick="runTests()">
            ⚡ Run 6 Tests (Verification Suite)
          </button>
        </div>
      </div>

    </div>

    <!-- Test Suite Results Box -->
    <div class="card test-box" id="test-box">
      <div class="card-header">
        <h2 class="card-title">🧪 6-Case Verification Results</h2>
        <span id="test-summary-badge" class="badge badge-PASS">PASS</span>
      </div>
      <div id="test-list"></div>
    </div>

    <!-- Data Tables Grid -->
    <div class="action-grid">

      <!-- Agents Table -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">📋 Registered Agents</h2>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Status</th>
                <th>Registered At</th>
                <th>Revoked At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="agents-tbody">
              <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Audit Log Table -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">📜 Audit Log (audit_log.csv)</h2>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Request</th>
                <th>Decision</th>
                <th>Rule</th>
              </tr>
            </thead>
            <tbody id="audit-tbody">
              <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

  </div>

  <script>
    async function loadData() {
      try {
        const res = await fetch('/api/data');
        const data = await res.json();

        // Populate Summary Metrics
        document.getElementById('total-agents').innerText = data.summary.total_agents;
        document.getElementById('active-agents').innerText = data.summary.active_agents;
        document.getElementById('revoked-agents').innerText = data.summary.revoked_agents;
        document.getElementById('allow-count').innerText = data.summary.allow_count;
        document.getElementById('ask-count').innerText = data.summary.ask_customer_count;
        document.getElementById('block-count').innerText = data.summary.block_count;

        // Populate Agents Table
        const agentsTbody = document.getElementById('agents-tbody');
        const agentKeys = Object.keys(data.agents);
        if (agentKeys.length === 0) {
          agentsTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #9ca3af;">No agents registered yet.</td></tr>';
        } else {
          agentsTbody.innerHTML = agentKeys.map(k => {
            const ag = data.agents[k];
            const isRevoked = (ag.status || '').toUpperCase() === 'REVOKED';
            const badgeClass = isRevoked ? 'badge-REVOKED' : 'badge-ACTIVE';
            const actionBtn = isRevoked 
              ? `<button class="btn btn-dark" style="padding: 3px 8px; font-size: 0.75rem;" onclick="quickRegister('${k}')">Activate</button>`
              : `<button class="btn btn-danger" style="padding: 3px 8px; font-size: 0.75rem;" onclick="quickRevoke('${k}')">Revoke</button>`;

            return `<tr>
              <td><strong>${k}</strong></td>
              <td><span class="badge ${badgeClass}">${ag.status || 'ACTIVE'}</span></td>
              <td>${ag.registered_at || '-'}</td>
              <td>${ag.revoked_at || '-'}</td>
              <td>${actionBtn}</td>
            </tr>`;
          }).join('');
        }

        // Populate Audit Log Table
        const auditTbody = document.getElementById('audit-tbody');
        if (data.audit_log.length === 0) {
          auditTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #9ca3af;">No audit log records found.</td></tr>';
        } else {
          // Display in reverse chronological order
          const reversed = [...data.audit_log].reverse();
          auditTbody.innerHTML = reversed.map(r => {
            const dec = (r.decision || '').trim();
            const badgeStyle = dec.includes('ALLOW') ? 'badge-ALLOW' : (dec.includes('ASK') ? 'badge-ASK' : 'badge-BLOCK');
            return `<tr>
              <td style="white-space: nowrap;">${r.time || ''}</td>
              <td><code>${r.request || ''}</code></td>
              <td><span class="badge ${badgeStyle}">${dec}</span></td>
              <td>${r.rule || ''}</td>
            </tr>`;
          }).join('');
        }

      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      }
    }

    async function submitRequest(e) {
      e.preventDefault();
      const customer = document.getElementById('req-customer').value;
      const agent = document.getElementById('req-agent').value;
      const action = document.getElementById('req-action').value;
      const amount = document.getElementById('req-amount').value;

      const res = await fetch('/api/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer, agent, action, amount })
      });
      const data = await res.json();

      const banner = document.getElementById('result-banner');
      const decSpan = document.getElementById('res-decision');
      const ruleSpan = document.getElementById('res-rule');
      const reasonSpan = document.getElementById('res-reason');

      const dec = data.decision || 'BLOCK';
      banner.className = 'result-banner ' + (dec.includes('ALLOW') ? 'ALLOW' : (dec.includes('ASK') ? 'ASK' : 'BLOCK'));
      decSpan.innerText = 'Decision: ' + dec;
      ruleSpan.innerText = 'Rule ' + data.rule_num;
      reasonSpan.innerText = 'Reason: ' + data.reason;
      banner.style.display = 'block';

      loadData();
    }

    async function submitRegister(e) {
      e.preventDefault();
      const name = document.getElementById('reg-name').value;
      if (!name) return;
      await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      document.getElementById('reg-name').value = '';
      loadData();
    }

    async function submitRevoke(e) {
      e.preventDefault();
      const name = document.getElementById('rev-name').value;
      if (!name) return;
      await fetch('/api/revoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      document.getElementById('rev-name').value = '';
      loadData();
    }

    async function quickRegister(name) {
      await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      loadData();
    }

    async function quickRevoke(name) {
      await fetch('/api/revoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      loadData();
    }

    async function runTests() {
      const res = await fetch('/api/run-tests');
      const data = await res.json();

      const box = document.getElementById('test-box');
      const list = document.getElementById('test-list');
      const summaryBadge = document.getElementById('test-summary-badge');

      const allPassed = data.results.every(r => r.status === 'PASS');
      summaryBadge.className = 'badge ' + (allPassed ? 'badge-PASS' : 'badge-FAIL');
      summaryBadge.innerText = allPassed ? '6/6 ALL PASSED' : 'SOME TESTS FAILED';

      list.innerHTML = data.results.map((r, i) => `
        <div class="test-row">
          <div class="test-details">
            <span class="test-name">Case ${i+1}: ${r.name}</span>
            <span class="test-meta">Expected: ${r.expected}</span>
            <span class="test-meta">Actual:   ${r.actual}</span>
          </div>
          <div>
            <span class="badge badge-${r.status}">${r.status}</span>
          </div>
        </div>
      `).join('');

      box.style.display = 'block';
      loadData();
    }

    // Initial Load & polling
    loadData();
    setInterval(loadData, 5000);
  </script>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Gatekeeper Web Dashboard."""

    def log_message(self, format, *args):
        # Override to keep console clean
        return

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_content: str):
        body = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        if url.path == "/" or url.path == "/index.html":
            self._send_html(HTML_PAGE)

        elif url.path == "/api/data":
            agents = load_agents()
            logs = get_audit_log_records()
            summary = compute_summary_metrics()
            self._send_json(
                200,
                {
                    "enrolment": ENROLMENT_ID,
                    "agents": agents,
                    "audit_log": logs,
                    "summary": summary,
                },
            )

        elif url.path == "/api/run-tests":
            results = execute_dashboard_tests()
            self._send_json(200, {"results": results})

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b""

        payload = {}
        if post_body:
            try:
                payload = json.loads(post_body.decode("utf-8"))
            except Exception:
                pass

        if url.path == "/api/check":
            customer = payload.get("customer", "")
            agent = payload.get("agent", "")
            action = payload.get("action", "")
            amount = payload.get("amount", 0)

            decision, rule_num, reason = process_request(
                customer, agent, action, amount
            )
            self._send_json(
                200,
                {
                    "decision": decision,
                    "rule_num": rule_num,
                    "reason": reason,
                },
            )

        elif url.path == "/api/register":
            name = payload.get("name", "").strip()
            if name:
                agent_entry = register_agent(name)
                self._send_json(200, {"success": True, "agent": agent_entry})
            else:
                self._send_json(
                    400, {"success": False, "error": "Agent name is required"}
                )

        elif url.path == "/api/revoke":
            name = payload.get("name", "").strip()
            if name:
                agent_entry = revoke_agent(name)
                self._send_json(200, {"success": True, "agent": agent_entry})
            else:
                self._send_json(
                    400, {"success": False, "error": "Agent name is required"}
                )

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def run_server():
    """Start the Gatekeeper dashboard HTTP server."""
    print(f"Enrolment: {ENROLMENT_ID}")
    print(f"Amazon AI Agent Gatekeeper Dashboard running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to terminate.")

    HTTPServer.allow_reuse_address = True
    server = HTTPServer((HOST, PORT), DashboardRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
        server.server_close()


if __name__ == "__main__":
    run_server()
