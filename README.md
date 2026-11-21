# Agent Gatekeeper

A small Python program for an online store (Amazon) that decides what a customer's AI agent may do.

Enrolment: PGD202567787

## What it does
It receives a request (customer, agent name, action, amount) and returns ALLOW, ASK CUSTOMER or BLOCK with a rule number. Every decision is saved in audit_log.csv. Agents can be registered and revoked, and the revoke date and time are saved in agents.json.

## Rules (checked in this order)
1. Revoked agent: BLOCK
2. Unknown agent: BLOCK
3. Missing customer, invalid action or negative amount: BLOCK
4. view_order: ALLOW
5. refund: ASK CUSTOMER
6. place_order or return up to Rs 5000: ALLOW
7. place_order or return above Rs 5000: ASK CUSTOMER

## Commands
py gatekeeper.py register NAME
py gatekeeper.py revoke NAME
py gatekeeper.py request CUSTOMER AGENT ACTION AMOUNT
py gatekeeper.py test
