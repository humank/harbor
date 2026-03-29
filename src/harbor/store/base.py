"""Base store — shared DynamoDB table access and cursor utilities."""

import base64
import json
import os
from typing import Any

import boto3

DEFAULT_TABLE = "harbor-agent-registry"


class BaseStore:
    """Shared DynamoDB table access for all store classes."""

    def __init__(self, table_name: str | None = None, region: str | None = None) -> None:
        self.table_name = table_name or os.environ.get("HARBOR_TABLE", DEFAULT_TABLE)
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._table: Any = None

    @property
    def table(self) -> Any:
        """Lazy-init DynamoDB table resource."""
        if self._table is None:
            self._table = boto3.resource("dynamodb", region_name=self.region).Table(self.table_name)
        return self._table

    @staticmethod
    def _agent_pk(tenant_id: str, agent_id: str) -> str:
        return f"TENANT#{tenant_id}#AGENT#{agent_id}"

    @staticmethod
    def encode_cursor(key: dict[str, Any] | None) -> str | None:
        """Encode LastEvaluatedKey as a cursor string."""
        if not key:
            return None
        return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()

    @staticmethod
    def decode_cursor(cursor: str) -> dict[str, Any]:
        """Decode a cursor string back to LastEvaluatedKey."""
        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())  # type: ignore[no-any-return]
