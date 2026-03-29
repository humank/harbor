"""Streaming agent-proxy Lambda handler.

Wraps user prompt into A2A JSON-RPC message/send, invokes AgentCore Runtime,
and yields SSE chunks as they arrive — enabling end-to-end streaming through
REST API Gateway with responseTransferMode=STREAM.
"""

import json
import os
import uuid

import boto3

AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")
client = boto3.client("bedrock-agentcore", region_name=REGION)

# 8 null bytes — delimiter between HTTP metadata and streaming body
# required by Lambda custom runtime streaming protocol
METADATA_DELIMITER = b"\x00" * 8


def handler(event, _context):
    """Yield HTTP metadata + SSE chunks for Lambda response streaming."""
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        yield from _error_response(400, "Invalid JSON body")
        return

    prompt = body.get("prompt", "")
    session_id = body.get("sessionId", "")

    if not prompt:
        yield from _error_response(400, "Missing 'prompt'")
        return
    if not session_id:
        yield from _error_response(400, "Missing 'sessionId'")
        return
    if not AGENT_RUNTIME_ARN:
        yield from _error_response(500, "AGENT_RUNTIME_ARN not configured")
        return

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

    # --- HTTP metadata (status + headers) ---
    yield json.dumps({
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
    }).encode()
    yield METADATA_DELIMITER

    # --- Invoke AgentCore Runtime and stream SSE ---
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=json.dumps(a2a_payload).encode(),
        )

        content_type = response.get("contentType", "")

        if "text/event-stream" in content_type:
            # AgentCore returns SSE — pass through directly
            for line in response["response"].iter_lines(chunk_size=64):
                if line:
                    decoded = line.decode("utf-8")
                    yield f"data: {decoded}\n\n".encode()
        else:
            # AgentCore returns JSON — wrap as single SSE event
            body_bytes = b""
            for chunk in response["response"].iter_chunks():
                body_bytes += chunk
            yield f"data: {body_bytes.decode('utf-8')}\n\n".encode()

        yield b"data: [DONE]\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n".encode()
        yield b"data: [DONE]\n\n"


def _error_response(status, message):
    """Yield a non-streaming error response."""
    yield json.dumps({
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }).encode()
    yield METADATA_DELIMITER
    yield json.dumps({"error": message}).encode()
