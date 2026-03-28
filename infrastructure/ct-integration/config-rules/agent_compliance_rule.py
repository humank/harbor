"""AWS Config custom rule: checks Lambda/ECS resources are registered in Harbor."""

import json
import os
import urllib.request

import boto3

HARBOR_API_URL = os.environ["HARBOR_API_URL"]
config_client = boto3.client("config")


def _get_agent_from_harbor(agent_id: str) -> dict | None:
    """Fetch agent record from Harbor API. Returns None on any failure."""
    try:
        url = f"{HARBOR_API_URL}/api/v1/agents/{agent_id}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _evaluate(configuration_item: dict) -> tuple[str, str]:
    """Return (ComplianceType, Annotation) for a single resource."""
    tags = configuration_item.get("tags") or {}

    if tags.get("harbor-agent") != "true":
        return "NOT_APPLICABLE", "Resource is not a harbor agent"

    agent_id = tags.get("harbor-agent-id", configuration_item["resourceId"])
    agent = _get_agent_from_harbor(agent_id)

    if agent is None:
        return "NON_COMPLIANT", "Harbor API unreachable or agent not registered"

    if agent.get("lifecycle_status") != "published":
        return "NON_COMPLIANT", f"Agent lifecycle_status is '{agent.get('lifecycle_status')}', expected 'published'"

    return "COMPLIANT", "Agent is registered and published"


def handler(event, context):
    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]

    compliance_type, annotation = _evaluate(configuration_item)

    config_client.put_evaluations(
        Evaluations=[
            {
                "ComplianceResourceType": configuration_item["resourceType"],
                "ComplianceResourceId": configuration_item["resourceId"],
                "ComplianceType": compliance_type,
                "Annotation": annotation,
                "OrderingTimestamp": configuration_item.get(
                    "configurationItemCaptureTime",
                    configuration_item.get("resourceCreationTime", ""),
                ),
            }
        ],
        ResultToken=event["resultToken"],
    )
