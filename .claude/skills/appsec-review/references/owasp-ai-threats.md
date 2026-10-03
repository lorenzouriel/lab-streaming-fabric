# OWASP AI threat catalogs — review checklist

Sources: OWASP GenAI Security Project, https://genai.owasp.org/ (LLM Top 10 2025; Top 10 for Agentic Applications, announced 2025-12-09). Verify current editions before quoting IDs in a formal report.

## Top 10 for LLM Applications 2025

| ID | Risk | Review question / control |
|---|---|---|
| LLM01 | Prompt Injection | Is untrusted text (user input, web pages, files, emails, tool output) ever concatenated into instructions? Separate roles/channels, treat model output as untrusted, constrain tool scope, add human approval for high-impact actions. Indirect injection via retrieved documents counts. |
| LLM02 | Sensitive Information Disclosure | Can PII, secrets, or other tenants' data reach the prompt, training set, logs, or response? Redact before prompting, enforce per-user retrieval authZ, filter outputs. |
| LLM03 | Supply Chain | Model, dataset, adapter, and plugin provenance verified? Pin model versions and digests; prefer safetensors over pickle; scan third-party models. |
| LLM04 | Data and Model Poisoning | Who can write to training/fine-tuning/RAG corpora? Validate and version data, monitor for anomalies, gate ingestion. |
| LLM05 | Improper Output Handling | Is model output rendered as HTML, run as SQL/shell/code, or used as a URL without validation? Encode and validate like any untrusted input. |
| LLM06 | Excessive Agency | Does the LLM hold more tools, permissions, or autonomy than the task needs? Minimize tools, use per-user scoped credentials, require confirmation for irreversible actions. |
| LLM07 | System Prompt Leakage | Does the system prompt contain secrets, keys, or authZ logic? Move them out; assume the prompt is extractable. |
| LLM08 | Vector and Embedding Weaknesses | Is retrieval access-controlled per user/tenant? Guard against embedding inversion, cross-tenant leakage, and poisoned documents. |
| LLM09 | Misinformation | Are high-stakes answers grounded, cited, and verifiable? Add validation and human review where wrong answers cause harm. |
| LLM10 | Unbounded Consumption | Token, request, and cost limits per user; timeouts; guard against denial-of-wallet and model extraction via query volume. |

## Top 10 for Agentic Applications 2026

| ID | Risk | Review question / control |
|---|---|---|
| ASI01 | Agent Goal Hijack | Can injected content redirect the agent's objective? Lock goals in system-level config, validate plans against policy, monitor for goal drift. |
| ASI02 | Tool Misuse and Exploitation | Can tools be called with attacker-chosen arguments or chained harmfully? Typed schemas, argument validation, allowlists, rate limits, per-tool scopes. |
| ASI03 | Identity and Privilege Abuse | Do agents use shared or over-broad credentials? Give each agent its own short-lived, least-privilege identity; no ambient user tokens; audit delegation. |
| ASI04 | Agentic Supply Chain Vulnerabilities | Are MCP servers, plugins, tools, skills, and prompts vetted and pinned? Watch for tool poisoning and rug-pull updates; sign and review third-party components. |
| ASI05 | Unexpected Code Execution (RCE) | Does the agent generate and run code or shell commands? Sandbox (container/microVM), no network or secrets by default, deny-by-default filesystem. |
| ASI06 | Memory & Context Poisoning | Can persistent memory, RAG stores, or shared context be written by untrusted sources? Segment memory per user/session, validate writes, allow expiry and rollback. |
| ASI07 | Insecure Inter-Agent Communication | Are agent-to-agent messages authenticated, integrity-protected, and schema-validated? Prevent spoofing and replay between agents. |
| ASI08 | Cascading Failures | Can one bad output propagate through chained agents and amplify? Circuit breakers, step budgets, isolation, blast-radius limits. |
| ASI09 | Human-Agent Trust Exploitation | Can the agent's confident output manipulate approvers? Show provenance and risk in approval prompts; avoid rubber-stamp fatigue on high-impact actions. |
| ASI10 | Rogue Agents | Can an agent deviate from intended behavior undetected? Behavioral monitoring, kill switch, full action logging, periodic re-attestation. |

## Agent/MCP review quick pass

- [ ] Inventory every tool and MCP server; record what each can read, write, and execute
- [ ] Each tool scoped to least privilege; destructive tools behind human approval
- [ ] Secrets never placed in prompts, tool descriptions, or agent memory
- [ ] Tool descriptions and returned content treated as untrusted (tool-poisoning vector)
- [ ] All actions logged with agent identity, inputs, outputs, and approver
- [ ] Step, time, and cost budgets enforced; kill switch tested
