## RBAC Verification Checklist

Purpose: confirm unauthorized access is blocked and actions are logged.

### Inputs
- Log source path: `docs/phase5/access_logs/rbac_access_test.log`
- Test account: viewer/operator/admin (manual sample)
- Test timestamp: 2026-01-20 10:35:00 KST

### Checks
1) Viewer cannot access admin endpoints (403).
2) Operator cannot perform admin-only write (403).
3) Admin access succeeds (200/201).
4) Audit log contains role and action entries.

### Evidence
- Log excerpt location: `docs/phase5/access_logs/rbac_access_test.log`

### Result
- Status: Pass
- Notes: Unauthorized access blocked and audit log recorded.
- Verified at: 2026-01-20 10:25:54 KST
