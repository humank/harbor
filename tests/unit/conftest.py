"""Shared test fixtures."""

import os

import boto3
import pytest
from moto import mock_aws

from harbor.store.agent_store import AgentStore
from harbor.store.audit_store import AuditStore
from harbor.store.health_store import HealthStore
from harbor.store.policy_store import PolicyStore
from harbor.store.version_store import VersionStore

os.environ["HARBOR_AUTH_DISABLED"] = "true"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"


TABLE_NAME = "harbor-test"


def _create_table(table_name: str) -> None:
    """Create the DynamoDB table with GSIs for testing."""
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "updated_at", "AttributeType": "S"},
            {"AttributeName": "tenant_id", "AttributeType": "S"},
            {"AttributeName": "lifecycle_status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "status-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "updated_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "tenant-index",
                "KeySchema": [
                    {"AttributeName": "tenant_id", "KeyType": "HASH"},
                    {"AttributeName": "updated_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "lifecycle-index",
                "KeySchema": [
                    {"AttributeName": "lifecycle_status", "KeyType": "HASH"},
                    {"AttributeName": "updated_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def store():
    """Provide a moto-backed AgentStore."""
    with mock_aws():
        _create_table(TABLE_NAME)
        yield AgentStore(table_name=TABLE_NAME, region="us-east-1")


@pytest.fixture
def audit_store():
    """Provide a moto-backed AuditStore."""
    with mock_aws():
        _create_table(TABLE_NAME)
        yield AuditStore(table_name=TABLE_NAME, region="us-east-1")


@pytest.fixture
def health_store():
    """Provide a moto-backed HealthStore."""
    with mock_aws():
        _create_table(TABLE_NAME)
        yield HealthStore(table_name=TABLE_NAME, region="us-east-1")


@pytest.fixture
def policy_store():
    """Provide a moto-backed PolicyStore."""
    with mock_aws():
        _create_table(TABLE_NAME)
        yield PolicyStore(table_name=TABLE_NAME, region="us-east-1")


@pytest.fixture
def version_store():
    """Provide a moto-backed VersionStore."""
    with mock_aws():
        _create_table(TABLE_NAME)
        yield VersionStore(table_name=TABLE_NAME, region="us-east-1")
