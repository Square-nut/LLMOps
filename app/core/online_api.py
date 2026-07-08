from app.core.config import settings


class OnlineApiDisabledError(PermissionError):
    pass


def require_online_api(action: str) -> None:
    if not settings.allow_online_api:
        raise OnlineApiDisabledError(
            f"Online API is disabled. Set ALLOW_ONLINE_API=true in .env before {action}."
        )
