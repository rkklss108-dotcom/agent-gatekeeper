# Prompts

1. I asked the coding agent (Google Antigravity) to build gatekeeper.py for an online store (Amazon) with 7 rules, an audit log (audit_log.csv), agent register and revoke commands with timestamps (agents.json), my enrolment number PGD202567787 on every run, and a test command with 6 cases.

2. I asked the agent to run: register MyShopper, a 9000 order, revoke MyShopper, then a 100 order, and show the output.

## One thing I checked myself
I ran register, then a 9000 order (ASK CUSTOMER, Rule 7), then revoke, then a 100 order, and confirmed the revoked agent was blocked with Rule 1. I also checked that audit_log.csv saved the date and time of each request.
