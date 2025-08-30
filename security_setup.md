# Security Setup Guide

## Required Security Configuration

### 1. Proxy Authentication (CRITICAL)
```bash
# Set in production environment
PROXY_SHARED_SECRET=your-strong-random-secret-here
X_PROXY_SECRET_HEADER=X-Proxy-Secret
```

**⚠️ REQUIRED**: App will return 500 error in production if `PROXY_SHARED_SECRET` is not set.

### 2. User Header Mapping
```bash
# Map to your reverse proxy's user header
X_USER_ID_HEADER=X-User-Email
```

### 3. Security Headers (Optional)
```bash
# All enabled by default - customize as needed
SECURITY_NOSNIFF_ENABLED=true
SECURITY_XFO_ENABLED=true
SECURITY_XFO_VALUE=SAMEORIGIN
SECURITY_REFERRER_POLICY_ENABLED=true
SECURITY_REFERRER_POLICY_VALUE=no-referrer
SECURITY_CSP_ENABLED=true
SECURITY_CSP_VALUE="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
```

## Reverse Proxy Configuration

Your reverse proxy (nginx/Apache/Traefik) must:

1. **Set proxy secret header**:
   ```nginx
   proxy_set_header X-Proxy-Secret your-strong-random-secret-here;
   ```

2. **Set user email header**:
   ```nginx
   proxy_set_header X-User-Email $authenticated_user_email;
   ```

3. **Block direct access** - only allow traffic through proxy

## Admin User Management

- Only users in "admin" group can create new users via `POST /api/users/`
- Admin access is determined by `is_user_in_group(email, "admin")`
- Configure your auth system to return proper group memberships

## File Security

- Filenames are automatically sanitized in download headers
- Content-Disposition headers prevent injection attacks
- No additional configuration needed

## Production Checklist

- [ ] `PROXY_SHARED_SECRET` set to strong random value
- [ ] `X_USER_ID_HEADER` matches your proxy's user header
- [ ] Reverse proxy configured with secret and user headers
- [ ] Direct access to app blocked (only proxy traffic allowed)
- [ ] Admin group membership properly configured in auth system
- [ ] Security headers customized for your domain (especially CSP)

## Disable Debug Mode

```bash
DEBUG=false
SKIP_HEADER_CHECK=false
```

**Never run in production with debug mode enabled.**