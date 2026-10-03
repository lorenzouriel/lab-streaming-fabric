# Supply chain and SLSA v1.2

Source: https://slsa.dev/spec/v1.2/ (status Approved). SLSA v1.0 removed the old "Level 4" from the Build track; the Build track is L1–L3. v1.2 reintroduces a Source track. Older checklists listing "Build L4 / hermetic / two-person review" describe the retired v0.1 model; two-person review now lives in the Source track.

## Build track

| Level | Name | Requirements to verify |
|---|---|---|
| L0 | None | No guarantees |
| L1 | Provenance exists | Build is scripted; provenance describing how the artifact was built is generated automatically (may be unsigned) |
| L2 | Hosted build platform | Build runs on a hosted platform that generates and signs the provenance; consumers can verify the signature |
| L3 | Hardened builds | Runs are isolated from one another; signing secrets are inaccessible to user-defined build steps; provenance is non-falsifiable |

Checks per level:
- L1: build script in version control; provenance emitted for every release artifact (in-toto/SLSA provenance format)
- L2: builds on GitHub Actions/GitLab/Azure DevOps hosted runners, not a developer laptop; provenance signed by the platform identity (Sigstore/cosign or equivalent); verification step exists in the deploy path
- L3: ephemeral, isolated runners; reusable trusted builders (e.g. `slsa-github-generator`); no cache poisoning across runs; secrets not readable by the build

## Source track (v1.2)

Progressive levels covering version control, retained history, and review. Review that the repository enforces: version control with immutable history, protected branches, mandatory code review by a second person for the top level, and retained source provenance. Confirm exact level wording in the spec before citing a level number in a formal report.

## Pipeline hardening checklist

- [ ] GitHub Actions/pipeline steps pinned by full commit SHA; third-party actions reviewed
- [ ] Workflow token permissions minimal (`permissions:` read-only by default); no `pull_request_target` with untrusted checkout
- [ ] OIDC federation to cloud instead of long-lived credentials
- [ ] Branch protection: required reviews, status checks, signed commits where policy demands
- [ ] Separate build and deploy identities; production deploy needs approval
- [ ] Dependencies locked with hashes; private registry or proxy with allowlist; dependency-confusion guards
- [ ] SBOM (CycloneDX or SPDX) produced per release and stored with the artifact
- [ ] Artifacts and images signed (cosign) and verified at admission (policy controller)
- [ ] Vulnerability scanning (SCA, container, IaC) with a failing gate and an exception process
- [ ] Secrets scanning on push and in history; rotation runbook

## Recent threat patterns to check for

- Compromised maintainer accounts publishing malicious versions; self-propagating package worms that steal CI/npm tokens — mitigate with MFA, short-lived tokens, delayed adoption of brand-new versions, `ignore-scripts` where feasible
- Poisoned GitHub Actions and tag re-pointing — pin by SHA
- Typosquatting and dependency confusion — scoped packages, registry allowlists
- Malicious AI-ecosystem components (MCP servers, agent skills, models in pickle format) — see `owasp-ai-threats.md` ASI04 and LLM03
