"""Fixed public account errors; never expose provider responses or credentials."""

_REASONS = {401: "authentication_failed", 402: "insufficient_balance", 403: "permission_denied"}


class ProviderAccountError(RuntimeError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.reason = _REASONS[status_code]
        action = ("Top up the configured provider account before rerunning."
                  if status_code == 402 else "Check the configured provider credentials and permissions before rerunning.")
        super().__init__(f"AI provider account blocked: {self.reason} (HTTP {status_code}). "
                         f"{action} Publication stopped; failed analysis is not a score of zero.")


def account_error(exc):
    """Classify explicit HTTP status only, never words in untrusted error text."""
    if isinstance(exc, ProviderAccountError):
        return exc
    status = getattr(exc, "status_code", None)
    if type(status) is int and status in _REASONS:
        return ProviderAccountError(status)
    return None
