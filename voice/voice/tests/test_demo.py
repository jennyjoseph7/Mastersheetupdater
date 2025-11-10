from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


from enum import Enum

class EscalationReason(Enum):
    TIMEOUT = "timeout"
    USER_REQUEST = "user_request"
    BOT_FAILURE = "bot_failure"


@dataclass
class EscalationEvent:
    session_id: str
    message_id: str
    reason: EscalationReason
    user_query: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)



event = EscalationEvent(
    session_id="sess-001",
    message_id="msg-123",
    reason=EscalationReason.BOT_FAILURE,
    user_query="The bot isn't responding properly",
    metadata={"retry_count": 3}
)

print(event)