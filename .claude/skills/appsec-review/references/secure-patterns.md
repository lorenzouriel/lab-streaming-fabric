# Secure patterns and configuration

Source of parameters: OWASP Cheat Sheet Series (https://cheatsheetseries.owasp.org/) — Password Storage, Session Management, HTTP Headers, SSRF Prevention.

## Security headers

```http
Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
X-Frame-Options: DENY            # legacy; frame-ancestors in CSP is the modern control
X-XSS-Protection: 0              # disable; the legacy auditor can introduce XSS. Rely on CSP
```

Do not recommend `X-XSS-Protection: 1; mode=block` — OWASP now advises turning it off. Remove `Server` and `X-Powered-By` version disclosure. Tune CSP per app (nonces/hashes for inline scripts) and roll out with `Content-Security-Policy-Report-Only` first.

## Password hashing (OWASP Password Storage)

Prefer Argon2id. Equivalent-strength minimum configurations:

| Memory (m) | Iterations (t) | Parallelism (p) |
|---|---|---|
| 46 MiB (47104) | 1 | 1 |
| 19 MiB (19456) | 2 | 1 |
| 12 MiB (12288) | 3 | 1 |
| 9 MiB (9216) | 4 | 1 |
| 7 MiB (7168) | 5 | 1 |

Fallbacks: scrypt (N=2^17, r=8, p=1), bcrypt cost ≥ 10 (72-byte input limit), PBKDF2-HMAC-SHA256 ≥ 600,000 iterations for FIPS environments.

## Session cookie

```http
Set-Cookie: __Host-SessionID=<random>; Secure; HttpOnly; SameSite=Strict; Path=/
```

`__Host-` forces `Secure`, no `Domain`, `Path=/`. Use `SameSite=Lax` when top-level cross-site navigation must keep the session. Session IDs ≥ 128 bits from a CSPRNG; regenerate on login.

## Code patterns

Secrets:
```python
# Bad
password = "hardcoded123"
# Good — env or secret manager, fail fast when missing
password = os.environ["DB_PASSWORD"]
```

SQL:
```python
# Bad
cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")
# Good — placeholder syntax depends on the driver (?, %s, :name)
cursor.execute("SELECT * FROM users WHERE id = %s", (user_input,))
```

Errors (fail closed, no leakage):
```python
# Bad — leaks internals, and fails open if the check itself raises
try:
    allowed = check_permission(user, resource)
except Exception as e:
    return {"error": str(e)}
# Good
try:
    allowed = check_permission(user, resource)
except Exception:
    logger.exception("permission check failed")
    return {"error": "internal error"}, 500   # deny; never default to allowed
```

Outbound fetch (SSRF):
```python
ALLOWED_HOSTS = {"api.example.com"}
def safe_fetch(url):
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked")
    for info in socket.getaddrinfo(p.hostname, 443):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("blocked")
    return requests.get(url, timeout=5, allow_redirects=False)
```
Resolve-then-connect has a DNS-rebinding window; pin the resolved IP in the connection or route egress through a filtering proxy for high-risk cases.

Path traversal:
```python
base = Path("/srv/uploads").resolve()
target = (base / user_name).resolve()
if not target.is_relative_to(base):
    raise PermissionError
```

## Logging hygiene

Log event, actor, resource, outcome, correlation ID. Never log passwords, tokens, keys, session IDs, full card numbers, or raw request bodies on auth routes. Strip CR/LF from user-controlled values.
