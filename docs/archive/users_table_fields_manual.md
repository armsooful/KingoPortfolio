# Users Table Field Values Manual

This manual documents the allowed input values for selected fields in the `users` table.

## Scope

Fields covered:
- `vip_tier`
- `membership_plan`
- `role`
- `is_admin`

## Field Values

### vip_tier

Allowed values:
- `bronze`
- `silver`
- `gold`
- `platinum`
- `diamond`

Default: `bronze`

Notes:
- Used for VIP benefits and limits.
- Derived from activity points and asset thresholds in the tier system.

### membership_plan

Allowed values:
- `free`
- `starter`
- `pro`
- `enterprise`

Default: `free`

Notes:
- Used for feature gating and monthly usage limits.
- Typically updated on payment events.

### role

Allowed values:
- `user`
- `premium`
- `admin`

Default: `user`

Notes:
- `is_admin = true` is treated as `role = 'admin'` for backward compatibility.
- Some admin routes currently validate only `user` or `admin`, so `premium` may be rejected there.

### is_admin

Allowed values:
- `true`
- `false`

Default: `false`

Notes:
- Legacy field kept for backward compatibility with older admin checks.

## References

- `backend/app/models/user.py`
- `backend/app/schemas.py`
- `backend/app/utils/tier_permissions.py`
- `backend/docs/reference/RBAC_IMPLEMENTATION.md`
- `backend/docs/TIER_SYSTEM_GUIDE.md`
