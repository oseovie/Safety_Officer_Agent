from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SAFETY_MANAGER = "safety_manager"
    SUPERVISOR = "supervisor"
    AUDITOR = "auditor"
    WORKER = "worker"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.OWNER: {"*"},
    Role.ADMIN: {"*"},
    Role.SAFETY_MANAGER: {
        "incident:write",
        "hazard:write",
        "inspection:write",
        "action:write",
        "document:write",
        "employee:write",
        "audit:write",
        "analytics:read",
    },
    Role.SUPERVISOR: {"incident:write", "hazard:write", "inspection:write", "action:write", "analytics:read"},
    Role.AUDITOR: {"audit:write", "document:read", "analytics:read"},
    Role.WORKER: {"incident:write", "hazard:write", "inspection:read"},
}


def has_permission(role: str, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(Role(role), set())
    return "*" in permissions or permission in permissions
