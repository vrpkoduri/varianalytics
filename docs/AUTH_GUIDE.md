# Authentication & Authorization Guide

**Version:** 1.0 | **Sprint:** 5

---

## Overview

The Variance Agent uses JWT-based authentication with support for two modes:

1. **Dev Mode** (default) — Email + password against local PostgreSQL users
2. **Azure AD Mode** — OAuth 2.0 code exchange when `AZURE_AD_TENANT_ID` is configured

RBAC is enforced at both the API layer (FastAPI middleware) and the UI layer (ProtectedRoute + persona-filtered tabs).

---

## Quick Start (Development)

### 1. Start services
```bash
./scripts/start_dev.sh
```

### 2. Login with demo credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@variance-agent.dev | password123 |
| Analyst | analyst@variance-agent.dev | password123 |
| BU Leader | bu.leader@variance-agent.dev | password123 |
| Director | director@variance-agent.dev | password123 |
| CFO | cfo@variance-agent.dev | password123 |
| Board Viewer | board@variance-agent.dev | password123 |

### 3. API authentication
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@variance-agent.dev","password":"password123"}'

# Use token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## Architecture

```
Frontend (React)
  ├── AuthContext (JWT in-memory)
  ├── ProtectedRoute (role-based guards)
  └── api.ts (auto-attach Bearer token)
         │
         ▼
Gateway (FastAPI)
  ├── JWT Middleware (shared/auth/middleware.py)
  │   ├── get_current_user() → UserContext
  │   ├── require_role(*roles) → 403 if unauthorized
  │   └── require_admin() → admin-only shorthand
  ├── Auth Endpoints (services/gateway/api/auth.py)
  │   ├── POST /auth/login → JWT pair
  │   ├── POST /auth/login/azure-ad → JWT pair (Azure AD)
  │   ├── POST /auth/register → new user (dev mode)
  │   ├── GET /auth/me → user profile
  │   └── POST /auth/refresh → new JWT pair
  └── RBAC Service (shared/auth/rbac.py)
      ├── Persona → Narrative Level mapping
      ├── Persona → Allowed Statuses mapping
      └── BU Scope enforcement
```

---

## JWT Token Structure

### Access Token (1 hour)
```json
{
  "sub": "user-001",
  "email": "analyst@company.com",
  "display_name": "Sarah Chen",
  "roles": ["analyst"],
  "bu_scope": ["ALL"],
  "persona": "analyst",
  "token_type": "access",
  "exp": 1711929600,
  "iat": 1711926000,
  "jti": "uuid"
}
```

### Refresh Token (24 hours)
```json
{
  "sub": "user-001",
  "token_type": "refresh",
  "exp": 1712012400,
  "iat": 1711926000,
  "jti": "uuid"
}
```

---

## RBAC Matrix

### Endpoint Access

| Endpoint | Public | Any Auth | Analyst | Director/CFO | Admin |
|----------|--------|----------|---------|-------------|-------|
| POST /auth/login | X | | | | |
| POST /auth/register | X | | | | |
| GET /auth/me | | X | | | |
| GET /dimensions/* | | X | | | |
| POST /chat/* | | X | | | |
| GET /config/* (read) | | X | | | |
| PUT /config/* (write) | | | | | X |
| GET /review/* | | | X | | X |
| POST /review/actions | | | X | | X |
| GET /approval/* | | | | X | X |
| POST /approval/actions | | | | X | X |
| GET /admin/* | | | | | X |
| POST /admin/* | | | | | X |
| */notifications/* | | | | | X |

### Persona Data Filtering

| Persona | Statuses | Narrative Levels | BU Scope |
|---------|----------|-----------------|----------|
| Analyst | All | Detail, Midlevel, Summary, Oneliner | All (or scoped) |
| BU Leader | Reviewed, Approved | Midlevel, Summary, Oneliner | Own BU only |
| Director | Reviewed, Approved | Midlevel, Summary, Oneliner | All |
| CFO | Approved | Summary, Oneliner | All |
| HR Finance | Draft, Reviewed, Approved | Detail, Midlevel, Oneliner | HC domain only |
| Board Viewer | Approved | Board, Summary | All |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, password_hash, Azure AD OID) |
| `roles` | System and custom roles with persona/narrative mapping |
| `user_roles` | User-role assignments with BU scope |
| `permissions` | Fine-grained resource/action permissions per role |

---

## Azure AD Setup (Production)

1. Register an application in Azure AD (Entra ID)
2. Configure redirect URI: `https://your-domain.com/auth/callback`
3. Set environment variables:
   ```env
   AZURE_AD_TENANT_ID=your-tenant-id
   AZURE_AD_CLIENT_ID=your-client-id
   AZURE_AD_CLIENT_SECRET=your-client-secret
   ```
4. The login page will automatically show "Sign in with Microsoft" button
5. New Azure AD users are auto-created with default analyst role
6. Admin assigns additional roles via the Admin panel

---

## Security Notes

- JWT tokens are stored in memory (not localStorage) on the frontend
- Access tokens expire in 1 hour; refresh tokens in 24 hours
- Dev mode fallback (no token required) only works when `ENVIRONMENT=development`
- Production should set `SECRET_KEY` to a strong random value
- CORS is open in dev; should be restricted in production
