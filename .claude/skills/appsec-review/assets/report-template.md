# Security Review — <scope>

Date: <YYYY-MM-DD> · Reviewer: Claude · Standards: OWASP Top 10:2025, <LLM 2025 / Agentic 2026 / SLSA v1.2 as applicable>

## Scope and assumptions
<systems reviewed, trust boundaries, what was not reviewed>

## Summary
| # | Severity | CVSS v4.0 | Title | Standard mapping |
|---|---|---|---|---|
| 1 | Critical | 9.3 | <title> | A05:2025, CWE-89 |

Fix first: <top three, one line each>

---

## Finding N: <brief description>

**Severity:** Critical | High | Medium | Low  
**CVSS v4.0:** <score> (`<vector>`)  
**Mapping:** <A0X:2025 / LLM0X:2025 / ASI0X / SLSA level>, <CWE-XXX>

**Location:** `path/to/file.py:42`

**Description:** <what is wrong and why the code path is reachable>

**Impact:** <what an attacker gains>

**Proof of concept:** <minimal, non-destructive steps or input; omit if only config evidence>

**Remediation:** <specific change, with a code diff where useful>

**References:** [CWE-XXX](https://cwe.mitre.org/data/definitions/XXX.html) · <CVE or OWASP cheat sheet link>

---

## Needs runtime confirmation
<candidates that could not be proven from static review>

## Threat model (if performed)
| Boundary | STRIDE | Threat | Mitigation | Status |
|---|---|---|---|---|
