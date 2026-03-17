# Security Policy

## Supported Scope

SplitMind-AI is a research project. Security fixes are handled on a best-effort basis.

## Reporting a Vulnerability

Please do not open public issues for security-sensitive problems.

Include the following in your report:

- affected component or file path
- reproduction steps
- expected impact
- any suggested mitigation

Examples of in-scope reports:

- prompt or runtime flows that bypass explicit safety checks
- memory persistence bugs that expose unintended user data
- dependency or configuration issues with clear security impact
- code paths that allow unsafe state to reach response generation

## Response Expectations

- Initial triage target: within 7 days
- Follow-up timing depends on severity and maintainer availability
- Coordinated disclosure is preferred until a fix or mitigation is ready

## Model and Safety Note

Behavioral safety issues can come from prompts, contracts, state updates, routing logic, or model/provider changes. Reports are most useful when they isolate which layer failed.
