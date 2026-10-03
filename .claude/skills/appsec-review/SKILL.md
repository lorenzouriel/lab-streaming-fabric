---
name: appsec-review
description: |
  Application-security review of code, configs, and CI/CD pipelines against current
  standards: OWASP Top 10:2025, OWASP Top 10 for LLM Applications 2025, OWASP Top 10 for
  Agentic Applications 2026, SLSA v1.2 (build and source tracks), and STRIDE threat
  modeling. Produces severity-ranked findings with CWE references, CVSS, and concrete
  remediation using a fixed report template. Use when the user asks to review code for
  vulnerabilities, threat-model a feature or architecture, audit authentication or
  authorization, check dependency or supply-chain posture, assess an LLM/RAG/agent
  system's security, or verify SLSA compliance. Do not use for the built-in
  /security-review of a pending branch diff, for incident response or exploit
  development, or for cloud-provider IAM or Fabric governance work — that is
  fabric-security-specialist and the cloud agents.
---

# AppSec Review

Evidence-based security review. Every finding cites file and line, a CWE, and a fix. No
finding without a reachable code path or config that proves it.

## Procedure

1. **Scope.** Identify what is under review (diff, module, service, pipeline, AI system) and its trust boundaries: who calls it, what data it holds, what it calls out to. State scope in one line.
2. **Classify surface.** Load only the references that apply:

   | Surface | Reference |
   |---|---|
   | Web/API/backend code, auth, data handling | `references/owasp-top10-2025.md` |
   | LLM calls, RAG, vector stores, prompts | `references/owasp-ai-threats.md` (LLM section) |
   | Agents, tools, MCP servers, memory, multi-agent | `references/owasp-ai-threats.md` (Agentic section) |
   | CI/CD, dependencies, build/release, SBOM | `references/supply-chain-slsa.md` |
   | Headers, secrets, crypto, secure-code snippets | `references/secure-patterns.md` |

3. **Threat model (only for design-level asks or new components).** Walk STRIDE per trust boundary: Spoofing→authN, Tampering→integrity, Repudiation→audit log, Information disclosure→encryption/authZ, Denial of service→rate/quotas, Elevation of privilege→authZ. Record each threat with its mitigation or "accepted".
4. **Review.** Read the code. Trace untrusted input to sinks (query, shell, template, deserializer, URL fetch, file path, LLM prompt, tool call). Trace secrets and PII to storage and logs. Check authZ on every route and object access, not only authN.
5. **Verify each candidate finding.** Confirm reachability and that no upstream control neutralizes it. Drop findings you cannot substantiate; list them as "needs runtime confirmation" instead of asserting.
6. **Report.** Fill `assets/report-template.md`, one block per finding, ranked Critical→Low. Finish with a summary table and the top three fixes to do first.

## Severity

Use CVSS v4.0 base score to justify the band: Critical 9.0–10.0, High 7.0–8.9, Medium 4.0–6.9, Low 0.1–3.9. Adjust down only with a stated compensating control; adjust up when the affected data is regulated or the endpoint is unauthenticated and internet-facing.

## Rules

- Prefer the fix that removes the class of bug (parameterized queries, allowlists, deny-by-default) over input blacklists.
- Never print a real secret found in code; show the first 4 characters and rotate advice.
- Do not run exploit code against systems you were not asked to test. Proof-of-concept steps stay minimal and non-destructive.
- Cite standards by ID (A01:2025, LLM06:2025, ASI02, SLSA Build L3) so findings map to auditors' checklists.
- Older checklists still circulate with outdated items (OWASP 2021 numbering, SLSA "Level 4", `X-XSS-Protection: 1`). Use the references here, not memory.

## Handoffs

| Need | Route |
|---|---|
| Fix implementation | the relevant dev agent (`python-developer`, `dotnet-specialist`, ...) |
| General code quality alongside security | `code-reviewer` agent |
| Fabric RLS, masking, governance | `fabric-security-specialist` agent |
| Pipeline hardening in Azure DevOps/Terraform | `ci-cd-specialist` agent |
