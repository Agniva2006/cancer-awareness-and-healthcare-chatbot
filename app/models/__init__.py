"""ORM models package. Importing this module registers all tables."""

from app.models.audit import AuditLog
from app.models.billing import BillingEvent, Order, Plan, Subscription, UsageEvent
from app.models.chat import Conversation, Message
from app.models.knowledge import KnowledgeDocument
from app.models.user import PendingEmailAction
from app.models.user import UserSession as UserSession  # avoid shadowing DB concept
from app.models.user import User

__all__ = [
    "User",
    "UserSession",
    "PendingEmailAction",
    "Conversation",
    "Message",
    "KnowledgeDocument",
    "Plan",
    "Subscription",
    "Order",
    "UsageEvent",
    "BillingEvent",
    "AuditLog",
]
