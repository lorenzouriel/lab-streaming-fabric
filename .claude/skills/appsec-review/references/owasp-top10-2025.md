# OWASP Top 10:2025 — review checklist

Source: https://top10.owasp.org/2025/ (first major update since 2021; two new categories, SSRF merged into A01).

Changes vs 2021: A02 Security Misconfiguration rose #5→#2; A03 Software Supply Chain Failures replaces "Vulnerable and Outdated Components" with a broader scope; A10 Mishandling of Exceptional Conditions is new; SSRF (2021 A10) is now part of A01; A07 renamed "Authentication Failures"; A09 renamed "Security Logging & Alerting Failures".

## A01 Broken Access Control (includes SSRF)
- [ ] AuthZ enforced server-side on every request; deny by default
- [ ] Object-level checks (IDOR/BOLA): ownership verified per record, not only per route
- [ ] Function-level checks: admin routes and methods restricted; no client-side-only gating
- [ ] CORS allowlist, no `*` with credentials; CSRF protection on cookie-authenticated state changes
- [ ] Path traversal blocked: canonicalize, then verify prefix
- [ ] SSRF: outbound URLs validated against an allowlist of hosts; resolved IPs must be public (block loopback, link-local `169.254.169.254`, RFC1918); no redirects followed blindly; non-HTTP schemes (`file://`, `gopher://`) rejected; cloud metadata protected (IMDSv2)

## A02 Security Misconfiguration
- [ ] No default credentials; debug/dev endpoints and verbose errors off in production
- [ ] Unused features, ports, sample apps, directory listing disabled
- [ ] Security headers set (see `secure-patterns.md`)
- [ ] Cloud storage/buckets not public; least-privilege IAM; hardened container images (non-root, read-only FS)
- [ ] XML parsers configured against XXE; config identical and reviewed across environments

## A03 Software Supply Chain Failures
- [ ] Lockfiles committed; versions pinned; installs use `--frozen-lockfile` / `--require-hashes`
- [ ] SBOM generated per release; dependencies scanned (SCA) in CI with a failing threshold
- [ ] Only trusted registries; typosquatting and dependency-confusion controls (scoped/private namespaces)
- [ ] CI/CD: actions pinned by commit SHA, least-privilege tokens, protected branches, required review, no secrets in logs
- [ ] Artifacts signed and provenance attested (see `supply-chain-slsa.md`)
- [ ] Abandoned or unmaintained packages flagged; install scripts reviewed

## A04 Cryptographic Failures
- [ ] TLS 1.2+ (prefer 1.3) everywhere; HSTS on
- [ ] Sensitive data encrypted at rest with AES-256-GCM or equivalent AEAD; keys in KMS/HSM/vault, rotated
- [ ] No MD5/SHA-1/DES/ECB for security purposes; RSA ≥ 2048, prefer Ed25519/ECDSA P-256
- [ ] Randomness from a CSPRNG (`secrets`, `crypto.randomBytes`), never `random`/`Math.random`
- [ ] No hardcoded keys or secrets; secrets absent from repo history
- [ ] Passwords hashed with Argon2id (preferred), scrypt, or bcrypt — never encrypted, never fast hashes

## A05 Injection
- [ ] SQL/NoSQL/LDAP/OS commands use parameterization or safe APIs; no string concatenation into interpreters
- [ ] Shell calls avoid `shell=True`/`exec` with user data; argument arrays used
- [ ] Contextual output encoding for HTML/JS/URL/CSS; templating autoescape on; CSP as defense in depth
- [ ] Deserialization of untrusted data avoided (`pickle`, Java native, .NET `BinaryFormatter`, YAML `load`)
- [ ] ORM raw-query escape hatches and dynamic ORDER BY / column names allowlisted
- [ ] Prompt injection handled under `owasp-ai-threats.md` when LLMs are involved

## A06 Insecure Design
- [ ] Threat model exists for the feature; abuse cases written next to use cases
- [ ] Business-logic limits: rate limits, quotas, per-user resource caps, anti-automation on sensitive flows
- [ ] Tenant isolation designed in, not bolted on
- [ ] Fail-safe defaults; defense in depth; secure-by-default configuration
- [ ] Security requirements traceable to tests

## A07 Authentication Failures
- [ ] Passwords: length ≥ 8 with MFA, ≥ 15 without (NIST 800-63B); allow long passphrases; check against breached-password lists; no forced periodic rotation or composition rules
- [ ] MFA supported, phishing-resistant (passkeys/WebAuthn) preferred for privileged users
- [ ] Brute-force and credential-stuffing protection: rate limiting, lockout/backoff, generic error messages
- [ ] Sessions: ID regenerated on login and privilege change; invalidated on logout; idle and absolute timeouts; cookie `Secure; HttpOnly; SameSite`, `__Host-` prefix
- [ ] JWT: algorithm pinned (reject `none`), `exp`/`aud`/`iss` validated, short TTL, revocation strategy, keys rotated
- [ ] Account recovery does not leak account existence and uses single-use expiring tokens

## A08 Software or Data Integrity Failures
- [ ] Code, images, and updates verified by signature/digest before use
- [ ] No unsafe deserialization of untrusted objects; integrity checks on serialized state sent to clients
- [ ] CI/CD pipeline changes require review; build and deploy identities separated
- [ ] Subresource Integrity on third-party scripts; no auto-update from unauthenticated channels

## A09 Security Logging & Alerting Failures
- [ ] Auth events, access-control failures, input-validation failures, admin actions logged with who/what/when/where
- [ ] Logs exclude secrets, tokens, full PANs, and unnecessary PII; log injection prevented (encode newlines)
- [ ] Logs centralized, append-only or tamper-evident, retained per policy
- [ ] Alerts wired to actionable thresholds and tested; an incident response runbook and owner exist

## A10 Mishandling of Exceptional Conditions
- [ ] Failures fail closed: authZ/validation errors deny, never allow by default
- [ ] All error paths handled; no swallowed exceptions (`except: pass`, empty `catch`)
- [ ] Clients receive generic errors; stack traces, SQL, paths stay in server logs
- [ ] Resources released on error (files, locks, transactions rolled back); partial-failure states leave data consistent
- [ ] Timeouts, retries with backoff and caps, circuit breakers on external calls
- [ ] Null/empty/overflow/out-of-range inputs tested; race conditions (TOCTOU) considered on security checks
