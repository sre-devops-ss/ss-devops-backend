from account_provider import AccountProvider
class UserProvider:
    def __init__(self, user_id: str, username: Optional[str], groups: List[str],
                 allowed_accounts: List[AllowedAccount],
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.id = user_id  # Cognito `sub`
        self.username = username
        self.groups = groups
        self.allowed_accounts = allowed_accounts
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "_id": self.id,
            "username": self.username,
            "groups": self.groups,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "allowedAccounts": [acc.to_dict() for acc in self.allowed_accounts],
        }


    def from_dict(data):
        return UserProvider(
            user_id=data["_id"],
            username=data.get("username"),
            groups=data.get("groups", []),
            allowed_accounts=[AccountProvider.from_dict(a) for a in data.get("allowedAccounts", [])],
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

    def has_group(self, group: str) -> bool:
        return group in self.groups

    def get_permission_for_account(self, account_id: str) -> Optional[str]:
        for acc in self.allowed_accounts:
            if acc.account_id == account_id and acc.enabled:
                return acc.permission_level
        return None


