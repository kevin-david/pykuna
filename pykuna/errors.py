class KunaError(Exception):
    pass


class AuthenticationError(KunaError):
    """Raised when authentication fails."""

    pass


class UnauthorizedError(KunaError):
    """No longer raised: KunaAPI re-authenticates instead. Kept for compatibility."""

    pass
