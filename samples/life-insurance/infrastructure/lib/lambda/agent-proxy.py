"""Lambda handler that proxies requests to AgentCore Runtime with streaming response.

This Lambda uses response streaming (via Function URL or API Gateway HTTP API)
to forward SSE events from AgentCore Runtime to the frontend, avoiding the 29s
API Gateway timeout for long-running agent interactions.
"""

import json
import os
import boto3


AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

client = boto3.client("bedrock-agentcore", region_name=REGION)


def handler(event, context):
    """Standard Lambda handler for API Gateway HTTP API integration.

    Receives a JSON body with {prompt, sessionId} and returns the
    AgentCore Runtime streaming response as text/event-stream.
    """
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return _error(400, "Invalid JSON body")

    prompt = body.get("prompt", "")
    session_id = body.get("sessionId", "")

    if not prompt:
        return _error(400, "Missing 'prompt' in request body")
    if not session_id:
        return _error(400, "Missing 'sessionId' in request body")
    if not AGENT_RUNTIME_ARN:
        return _error(500, "AGENT_RUNTIME_ARN not configured")

    payload = json.dumps({"prompt": prompt}).encode()

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=payload,
        )
    except Exception as e:
        return _error(502, f"AgentCore Runtime error: {e}")

    content_type = response.get("contentType", "application/json")

    # Collect streaming response
    chunks = []
    if "text/event-stream" in content_type:
        for line in response["response"].iter_lines(chunk_size=10):
            if line:
                chunks.append(line.decode("utf-8"))
        body_str = "\n".join(chunks)
    else:
        raw = []
        for chunk in response.get("response", []):
            raw.append(chunk.decode("utf-8"))
        body_str = "".join(raw)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": content_type,
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        },
        "body": body_str,
    }


def _error(status, message):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": message}),
    }
