"""Configuration for the insurance demo agents."""

import os

USE_BEDROCK = os.getenv("USE_BEDROCK", "true").lower() == "true"
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_MODEL_LIGHT = os.getenv("BEDROCK_MODEL_LIGHT", "us.anthropic.claude-haiku-3-20250620-v1:0")

HARBOR_URL = os.getenv("HARBOR_URL", "http://localhost:8100/api/v1")
HARBOR_TENANT = os.getenv("HARBOR_TENANT", "demo-tenant")

AGENT_PORTS = {
    "recommendation": int(os.getenv("PORT_RECOMMENDATION", "8200")),
    "product_catalog": int(os.getenv("PORT_PRODUCT_CATALOG", "8201")),
    "underwriting_risk": int(os.getenv("PORT_UNDERWRITING_RISK", "8202")),
    "premium_calculator": int(os.getenv("PORT_PREMIUM_CALCULATOR", "8203")),
    "compliance_check": int(os.getenv("PORT_COMPLIANCE_CHECK", "8204")),
    "explanation": int(os.getenv("PORT_EXPLANATION", "8205")),
}

# Fallback URLs when Harbor is not available
AGENT_URLS = {name: f"http://localhost:{port}" for name, port in AGENT_PORTS.items()}
