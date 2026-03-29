"""Lambda handler that proxies requests to AgentCore Runtime (A2A protocol).

AgentCore Runtime with A2A protocol expects the InvokeAgentRuntime payload
to be a complete A2A JSON-RPC message. This Lambda wraps the user's prompt
into the proper A2A message/send format.
"""

import json
import os
import uuid
import boto3

AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

client = boto3.client("bedrock-agentcore", region_name=REGION)


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return _error(400, "Invalid JSON body")

    prompt = body.get("prompt", "")
    session_id = body.get("sessionId", "")

    if not prompt:
        return _error(400, "Missing 'prompt'")
    if not session_id:
        return _error(400, "Missing 'sessionId'")
    if not AGENT_RUNTIME_ARN:
        return _error(500, "AGENT_RUNTIME_ARN not configured")

    # Build A2A JSON-RPC message/send payload
    a2a_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": prompt}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }

    payload = json.dumps(a2a_payload).encode()

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=payload,
        )
    except Exception as e:
        return _error(502, f"AgentCore Runtime error: {e}")

    # Collect response
    body_bytes = b""
    for chunk in response["response"].iter_chunks():
        body_bytes += chunk

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        },
        "body": body_bytes.decode("utf-8"),
    }


def _error(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message}),
    }
