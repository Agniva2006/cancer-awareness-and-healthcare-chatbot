"""Email sending, abstracted behind a provider interface.

Providers:
- ``console`` (default/dev): logs the email instead of sending. Zero config.
- SMTP and provider APIs (Brevo/Resend/SendGrid) plug in later behind the same
  protocol — endpoints never know which one is active.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES: Dict[str, str] = {
    "verify_email": (
        "Welcome to {app_name}!\n\n"
        "Please verify your email address by opening this link (valid {hours}h):\n"
        "{base_url}/auth/verify-email?token={token}\n\n"
        "If you did not create an account, you can ignore this email."
    ),
    "reset_password": (
        "A password reset was requested for your {app_name} account.\n\n"
        "Open this link to choose a new password (valid {hours}h):\n"
        "{base_url}/auth/reset-password?token={token}\n\n"
        "If you did not request this, no action is needed."
    ),
}


class EmailProvider(ABC):
    """Interface every email backend implements (Dependency Inversion)."""

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailProvider(EmailProvider):
    """Dev provider: writes the email to the application log."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("[EMAIL → %s] %s\n%s", to, subject, body)


def get_email_provider() -> EmailProvider:
    """Factory — extend with SMTP/API providers as they are added."""
    if settings.EMAIL_PROVIDER == "console":
        return ConsoleEmailProvider()
    logger.warning(
        "Unknown EMAIL_PROVIDER %r; falling back to console", settings.EMAIL_PROVIDER
    )
    return ConsoleEmailProvider()


def send_template_email(to: str, template: str, token: str) -> None:
    """Render one of the known templates and hand it to the active provider."""
    body = TEMPLATES[template].format(
        app_name=settings.APP_NAME,
        base_url=settings.APP_BASE_URL,
        token=token,
        hours=settings.EMAIL_TOKEN_EXPIRE_HOURS,
    )
    subject = {
        "verify_email": f"Verify your {settings.APP_NAME} account",
        "reset_password": f"Reset your {settings.APP_NAME} password",
    }[template]
    get_email_provider().send(to=to, subject=subject, body=body)
