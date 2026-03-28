"""EventBridge event emitter for Harbor lifecycle and policy events."""

import os
from typing import Any

import boto3
import structlog

logger = structlog.get_logger(__name__)

EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "harbor-events")
SOURCE = "harbor"


class EventEmitter:
    """Emit events to EventBridge."""

    def __init__(self, bus_name: str | None = None, region: str | None = None) -> None:
        self.bus_name = bus_name or EVENT_BUS_NAME
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-init EventBridge client."""
        if self._client is None:
            self._client = boto3.client("events", region_name=self.region)
        return self._client

    def emit(self, detail_type: str, detail: dict[str, Any]) -> None:
        """Put a single event to EventBridge."""
        try:
            self.client.put_events(
                Entries=[
                    {
                        "Source": SOURCE,
                        "DetailType": detail_type,
                        "Detail": _serialize(detail),
                        "EventBusName": self.bus_name,
                    }
                ]
            )
            logger.info("event_emitted", detail_type=detail_type)
        except Exception:
            logger.exception("event_emit_failed", detail_type=detail_type)

    def lifecycle_changed(
        self,
        tenant_id: str,
        agent_id: str,
        from_state: str,
        to_state: str,
        actor: str,
    ) -> None:
        """Emit AgentLifecycleChanged event."""
        self.emit(
            "AgentLifecycleChanged",
            {
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "from_state": from_state,
                "to_state": to_state,
                "actor": actor,
            },
        )

    def policy_violation(
        self,
        tenant_id: str,
        agent_id: str,
        policy_type: str,
        reason: str,
    ) -> None:
        """Emit PolicyViolation event."""
        self.emit(
            "PolicyViolation",
            {
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "policy_type": policy_type,
                "reason": reason,
            },
        )


def _serialize(detail: dict[str, Any]) -> str:
    import json

    return json.dumps(detail, default=str)
