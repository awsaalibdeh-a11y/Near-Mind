"""NearMind WhatsApp bridge.

This package is the *only* place NearMind talks to real people. It wraps the
workspace ``whatsapp`` MCP server (``lharries/whatsapp-mcp``) behind a small,
typed interface the Flask backend can call, and adds the parts the upstream MCP
deliberately does not have:

* an **availability** model that real neighbours control with ``STOP``/``BUSY``,
* **rate limiting / anti-spam** guardrails,
* **schema-validated inbound events** so a free-text reply can never corrupt
  agent state,
* an **honest identity model** — one linked account, explicit simulation flags.

Nothing here creates its own WhatsApp client. The MCP stays an implementation
detail behind :class:`bridge.transport.WhatsAppTransport`.

See ``docs/BRIDGE.md`` for the interface, the state machine, and the numbers.
"""

from .availability import (
    Availability,
    AvailabilityState,
    AvailabilityStore,
    ExpiryResult,
)
from .commands import CommandKind, ParsedCommand, parse_command
from .core import (
    BridgeStatus,
    InboundBatch,
    ResolvedContact,
    WhatsAppBridge,
)
from .config import BridgeConfig
from .events import (
    ContactRef,
    InboundEvent,
    InboundKind,
    OutboundReceipt,
    OutboundResult,
    SendOutcome,
    ValidationFailure,
    validate_inbound,
)
from .limiter import RateDecision, RateLimiter, SendRefusal
from .transport import (
    DRY_RUN_ONLY,
    FakeTransport,
    McpStdioTransport,
    TransportMessage,
    WhatsAppTransport,
)

__all__ = [
    "Availability",
    "AvailabilityState",
    "AvailabilityStore",
    "ExpiryResult",
    "CommandKind",
    "ParsedCommand",
    "WhatsAppBridge",
    "BridgeStatus",
    "InboundBatch",
    "ResolvedContact",
    "parse_command",
    "BridgeConfig",
    "ContactRef",
    "InboundEvent",
    "InboundKind",
    "OutboundReceipt",
    "OutboundResult",
    "SendOutcome",
    "ValidationFailure",
    "validate_inbound",
    "RateDecision",
    "RateLimiter",
    "SendRefusal",
    "DRY_RUN_ONLY",
    "FakeTransport",
    "McpStdioTransport",
    "TransportMessage",
    "WhatsAppTransport",
]
