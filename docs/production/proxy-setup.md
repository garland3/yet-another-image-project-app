# Production Reverse Proxy Setup

This document describes how to configure a reverse proxy (nginx, Apache, etc.) for production deployment of the Image Project Manager application.

## Overview

The application uses **header-based authentication** via a reverse proxy. The proxy is responsible for:

1. Authenticating users (via OAuth2, SAML, LDAP, etc.)
2. Setting authentication headers on requests to the backend
3. Forwarding requests to the FastAPI backend
4. Serving static frontend assets (optional)

## Authentication Flow

```
User Browser --> Reverse Proxy (authenticates) --> FastAPI Backend
                      |
                      v
                 Sets Headers:
                 - X-User-Email: user@example.com
                 - X-Proxy-Secret: <shared-secret>
```

## Required Configuration

### 1. Environment Variables

Configure the following in your backend `.env` file:

```bash
# Disable debug mode for production
DEBUG=false
SKIP_HEADER_CHECK=false

# Shared secret between proxy and backend
PROXY_SHARED_SECRET=<generate-strong-random-secret>

# Header names (customize if needed)
X_USER_ID_HEADER=X-User-Email
X_PROXY_SECRET_HEADER=X-Proxy-Secret

# Optional: URL for auth server (for reference/documentation)
AUTH_SERVER_URL=https://auth.yourcompany.com
```

### 2. Generate Shared Secret

The `PROXY_SHARED_SECRET` must be a strong random value shared between the proxy and backend:

```bash
# Generate a secure random secret (Linux/Mac)
openssl rand -hex 32

# Example output:
# a7f3d9e2c4b8f1a6e9d4c2b7f5a8e3d1c9b6f4a2e7d5c3b1f8a6e4d2c7b5f3a9
```

**Important:** Keep this secret secure and never commit it to version control.

### 3. Backend Security Validation

The backend middleware (`backend/middleware/auth.py`) performs the following checks:

1. **Shared Secret Validation:** Verifies `X-Proxy-Secret` matches `PROXY_SHARED_SECRET`
2. **User Header Validation:** Extracts and validates email format from `X-User-Email`
3. **Group Membership:** Checks user permissions via `core/group_auth.py`

If validation fails, the backend returns `401 Unauthorized`.

## Reverse Proxy Configuration

### Nginx Configuration

See `nginx-example.conf` in this directory for a complete example.

Key requirements:
- Authenticate users before forwarding requests
- Set `X-User-Email` header with authenticated user's email
- Set `X-Proxy-Secret` header with shared secret
- Forward all other headers (especially `Host`, `X-Real-IP`, `X-Forwarded-For`)
- Handle WebSocket upgrades if needed (future feature)

### Apache Configuration

For Apache with `mod_auth_openidc` or similar:

```apache
<VirtualHost *:443>
    ServerName yourdomain.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem

    # Authentication (example with OpenID Connect)
    OIDCProviderMetadataURL https://auth.example.com/.well-known/openid-configuration
    OIDCClientID your-client-id
    OIDCClientSecret your-client-secret
    OIDCRedirectURI https://yourdomain.com/oauth2callback
    OIDCCryptoPassphrase <random-passphrase>

    <Location />
        AuthType openid-connect
        Require valid-user

        # Set authentication headers
        RequestHeader set X-User-Email "%{OIDC_CLAIM_email}e"
        RequestHeader set X-Proxy-Secret "your-shared-secret-here"

        # Proxy to backend
        ProxyPass http://localhost:8000/
        ProxyPassReverse http://localhost:8000/
    </Location>
</VirtualHost>
```

## Group Authorization Integration

The application uses group-based access control. Each project belongs to a group (`meta_group_id`), and users must be members of that group to access it.

### Customizing Group Membership Checks

Edit `backend/core/group_auth.py` and replace the `_check_group_membership` function:

```python
def _check_group_membership(user_email: str, group_id: str) -> bool:
    """
    Replace this function with your actual auth system integration.

    Examples:
    - Query LDAP/Active Directory
    - Call external auth service API
    - Query database with user roles
    - Call OAuth2 userinfo endpoint
    """
    # Example: Call external auth service
    response = requests.get(
        f"{settings.AUTH_SERVER_URL}/api/user/{user_email}/groups",
        headers={"Authorization": f"Bearer {settings.AUTH_API_TOKEN}"}
    )
    user_groups = response.json().get("groups", [])
    return group_id in user_groups
```

### Group Membership Caching

Group membership checks are cached for 5 minutes by default (configurable in `backend/core/group_auth_helper.py`). This reduces load on external auth systems.

## Security Considerations

### 1. Shared Secret Protection

- Use a strong random value (at least 32 bytes of entropy)
- Store securely (environment variables, secrets manager)
- Rotate periodically (requires coordinated update on proxy and backend)
- Never log or expose in error messages

### 2. Header Validation

The backend validates:
- Email format (RFC 5322 compliant)
- Shared secret exact match (constant-time comparison)
- Headers must come from trusted proxy only

### 3. Network Security

- Backend should ONLY accept connections from the reverse proxy
- Use firewall rules to restrict access (e.g., `iptables`, security groups)
- Consider using Unix sockets instead of TCP for local communication

Example firewall rule (iptables):
```bash
# Allow only localhost and proxy server to access backend port 8000
iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -s <proxy-server-ip> -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### 4. HTTPS/TLS

- Always use HTTPS in production
- Configure proper TLS settings (TLS 1.2+, strong ciphers)
- Use certificates from a trusted CA
- Enable HSTS (Strict-Transport-Security header)

### 5. Additional Security Headers

The backend automatically sets security headers via `SecurityHeadersMiddleware`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy` (configurable)

Configure these in your `.env` file if needed.

## Testing the Setup

### 1. Test Authentication

Without proper headers (should fail):
```bash
curl -i http://localhost:8000/api/projects
# Expected: 401 Unauthorized
```

With valid headers (should succeed):
```bash
curl -i \
  -H "X-User-Email: user@example.com" \
  -H "X-Proxy-Secret: your-shared-secret" \
  http://localhost:8000/api/projects
# Expected: 200 OK with project list
```

### 2. Test Invalid Secret

```bash
curl -i \
  -H "X-User-Email: user@example.com" \
  -H "X-Proxy-Secret: wrong-secret" \
  http://localhost:8000/api/projects
# Expected: 401 Unauthorized
```

### 3. Check Logs

Backend logs authentication attempts:
```bash
tail -f backend/logs/app.json | grep -i auth
```

## Deployment Checklist

- [ ] Generate strong `PROXY_SHARED_SECRET`
- [ ] Configure `.env` with production settings
- [ ] Set `DEBUG=false` and `SKIP_HEADER_CHECK=false`
- [ ] Configure reverse proxy with authentication
- [ ] Set required headers (`X-User-Email`, `X-Proxy-Secret`)
- [ ] Implement custom `_check_group_membership` function
- [ ] Configure firewall rules to restrict backend access
- [ ] Enable HTTPS/TLS on reverse proxy
- [ ] Test authentication flow end-to-end
- [ ] Configure logging and monitoring
- [ ] Set up database backups
- [ ] Configure S3/MinIO for production storage
- [ ] Run database migrations (`alembic upgrade head`)
- [ ] Test group-based access control

## Troubleshooting

### Issue: 401 Unauthorized

**Possible causes:**
1. Missing or incorrect `X-Proxy-Secret` header
2. Missing or invalid `X-User-Email` header
3. Header names don't match configuration (`X_USER_ID_HEADER`, `X_PROXY_SECRET_HEADER`)

**Solution:** Check backend logs and verify header values match configuration.

### Issue: 403 Forbidden

**Possible causes:**
1. User not in required group for project access
2. `_check_group_membership` returning false

**Solution:** Verify group membership in your auth system and check logs.

### Issue: 500 Internal Server Error

**Possible causes:**
1. `PROXY_SHARED_SECRET` not configured
2. Database connection failure
3. S3/MinIO unavailable

**Solution:** Check backend logs (`backend/logs/app.json`) for detailed error messages.

## Additional Resources

- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- Nginx Auth Request Module: http://nginx.org/en/docs/http/ngx_http_auth_request_module.html
- OAuth2 Proxy: https://oauth2-proxy.github.io/oauth2-proxy/
- Apache mod_auth_openidc: https://github.com/zmartzone/mod_auth_openidc
