from datetime import datetime
from typing import List, Optional


class AccountProvider:
    def __init__(self, account_id: str, account_name: str, enabled: bool = True,
                 permission_level: str = "read-only", tags: Optional[List[str]] = None,
                 linked_at: Optional[datetime] = None, expires_at: Optional[datetime] = None):
        self.account_id = account_id
        self.account_name = account_name
        self.enabled = enabled
        self.permission_level = permission_level
        self.tags = tags or []
        self.linked_at = linked_at or datetime.utcnow()
        self.expires_at = expires_at

    def to_dict(self):
        return {
            "accountId": self.account_id,
            "accountName": self.account_name,
            "enabled": self.enabled,
            "permissionLevel": self.permission_level,
            "tags": self.tags,
            "linkedAt": self.linked_at,
            "expiresAt": self.expires_at,
        }


    def from_dict(data):
        return AccountProvider(
            account_id=data["accountId"],
            account_name=data["accountName"],
            enabled=data.get("enabled", True),
            permission_level=data.get("permissionLevel", "read-only"),
            tags=data.get("tags", []),
            linked_at=data.get("linkedAt"),
            expires_at=data.get("expiresAt"),
        )
