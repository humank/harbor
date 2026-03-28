import os
import uuid
from datetime import datetime, timezone

import boto3

REGION = os.environ.get("REGION", "us-east-1")
sh_client = boto3.client("securityhub", region_name=REGION)

SEVERITY_BY_POLICY = {
    "communication": "HIGH",
    "capability": "MEDIUM",
    "schedule": "LOW",
}


def _base_finding(account_id, generator_id, title, description, severity, agent_id):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "SchemaVersion": "2018-10-08",
        "Id": str(uuid.uuid4()),
        "ProductArn": f"arn:aws:securityhub:{REGION}:{account_id}:product/{account_id}/default",
        "GeneratorId": generator_id,
        "AwsAccountId": account_id,
        "CreatedAt": now,
        "UpdatedAt": now,
        "Title": title,
        "Description": description,
        "Severity": {"Label": severity},
        "Types": ["Software and Configuration Checks/Governance"],
        "Resources": [{"Type": "Other", "Id": agent_id, "Region": REGION}],
        "CompanyName": "Harbor",
        "ProductName": "Harbor Agent Governance",
    }


def handler(event, context):
    try:
        detail_type = event.get("detail-type", "")
        detail = event.get("detail", {})
        account_id = event.get("account", context.invoked_function_arn.split(":")[4])

        finding = None

        if detail_type == "PolicyViolation":
            policy_type = detail.get("policy_type", "unknown")
            finding = _base_finding(
                account_id=account_id,
                generator_id="harbor-policy-engine",
                title=f"Harbor Policy Violation: {policy_type}",
                description=detail.get("reason", "No reason provided"),
                severity=SEVERITY_BY_POLICY.get(policy_type, "MEDIUM"),
                agent_id=detail.get("agent_id", "unknown"),
            )

        elif detail_type == "AgentLifecycleChanged" and detail.get("to_state") == "suspended":
            agent_id = detail.get("agent_id", "unknown")
            finding = _base_finding(
                account_id=account_id,
                generator_id="harbor-policy-engine",
                title=f"Harbor Agent Suspended: {agent_id}",
                description=f"Agent {agent_id} was suspended by {detail.get('actor', 'unknown')}",
                severity="CRITICAL",
                agent_id=agent_id,
            )

        if finding:
            resp = sh_client.batch_import_findings(Findings=[finding])
            print(f"Imported finding: {finding['Title']}, failed={resp.get('FailedCount', 0)}")
        else:
            print(f"Ignored event: detail-type={detail_type}")

    except Exception as e:
        print(f"Error processing event: {e}")
        raise
