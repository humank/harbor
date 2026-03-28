# Harbor — Enterprise Integration Guide

## Overview

Harbor deploys as a management plane in the **Shared Services OU** of a Control Tower landing zone. It provides agent registration, discovery, and governance for workload accounts across the organization.

```
┌──────────────────────────────────────────────────────────┐
│  Management Account (Control Tower)                      │
│  ├── SCPs, StackSets, Guardrails                         │
│                                                          │
│  Shared Services OU                                      │
│  └── Harbor Central Account                              │
│      ├── API Gateway + Lambda (FastAPI)                   │
│      ├── DynamoDB (harbor-agent-registry)                 │
│      ├── Cognito (SSO via IAM Identity Center)            │
│      ├── EventBridge (harbor-events bus)                  │
│      └── CloudFront + S3 (Management UI)                  │
│                                                          │
│  Workload OU                                             │
│  ├── BU-Dev Account ──┐                                  │
│  ├── BU-Staging Account ── harbor-agent-reporter role     │
│  └── BU-Prod Account ─┘   (deployed via StackSet)        │
└──────────────────────────────────────────────────────────┘
```

Workload accounts assume the `harbor-agent-reporter` IAM role to call the Harbor API and put events to the Harbor EventBridge bus. SCPs prevent workload accounts from modifying Harbor Central resources.

## Prerequisites

- Control Tower landing zone operational with Shared Services OU and Workload OU
- Shared Services account identified for Harbor deployment
- AWS Organization ID known (`o-xxxxxxxxxx`) — needed for cross-account EventBridge
- IAM Identity Center configured with enterprise IdP (Okta, Azure AD, etc.)
- AWS CLI v2 installed with profiles for Management and Shared Services accounts
- Node.js 18+ and npm (for CDK)
- Python 3.12+ (for backend)

## Deployment Order

| Step | What | Where | Time |
|------|------|-------|------|
| 1 | Deploy Harbor Central (CDK) | Shared Services account | ~10 min |
| 2 | Deploy StackSet (workload IAM role) | Management account → Workload OU | ~5 min |
| 3 | Attach SCPs | Management account → Workload OU | ~2 min |
| 4 | Configure IAM Identity Center SSO | Management account + Cognito | ~15 min |
| 5 | Enable Security Hub integration | Shared Services account | ~5 min |
| 6 | Deploy Config Rules | Management account → Workload OU | ~5 min |

---

## Step 1: Deploy Harbor Central

Deploy the Harbor CDK stack to the Shared Services account.

### 1a. Set the Organization ID

Edit `infrastructure/lib/config.ts` and set `orgId` to your AWS Organization ID. This enables cross-account EventBridge access for workload accounts.

```typescript
export const prodConfig: HarborConfig = {
  tableName: "harbor-agent-registry",
  environment: "prod",
  enableAuth: true,
  orgId: "o-xxxxxxxxxx",  // ← your org ID
};
```

### 1b. Deploy

```bash
cd infrastructure
npm install
AWS_PROFILE=harbor-shared-services npx cdk deploy --require-approval broadening
```

Or use the deploy script:

```bash
AWS_PROFILE=harbor-shared-services ./scripts/deploy.sh
```

### 1c. Note the outputs

The stack outputs values needed for subsequent steps:

```
HarborStack.ApiUrl          = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
HarborStack.UserPoolId      = us-east-1_XXXXXXXXX
HarborStack.SpaClientId     = xxxxxxxxxxxxxxxxxxxxxxxxxx
HarborStack.M2mClientId     = xxxxxxxxxxxxxxxxxxxxxxxxxx
HarborStack.EventBusName    = harbor-events
HarborStack.TableName       = harbor-agent-registry
HarborStack.FrontendBucketName = harbor-frontend
HarborStack.DistributionUrl = https://dxxxxxxxxxx.cloudfront.net
HarborStack.AlertTopicArn   = arn:aws:sns:us-east-1:XXXXXXXXXXXX:harbor-alerts
```

Save these — you'll need `ApiUrl`, `EventBusName`, and `UserPoolId` in later steps.

---

## Step 2: Deploy StackSet (Workload Account Role)

The StackSet deploys a `harbor-agent-reporter` IAM role to every workload account. This role allows agents to call the Harbor API and put events to the Harbor EventBridge bus.

**Template:** `infrastructure/ct-integration/stacksets/harbor-workload-role.yaml`

### 2a. Deploy via CloudFormation StackSet

From the **Management account** (or delegated admin):

```bash
HARBOR_ACCOUNT_ID="111111111111"       # Shared Services account ID
API_GW_ARN="arn:aws:execute-api:us-east-1:${HARBOR_ACCOUNT_ID}:xxxxxxxxxx/*"
EVENT_BUS_ARN="arn:aws:events:us-east-1:${HARBOR_ACCOUNT_ID}:event-bus/harbor-events"
WORKLOAD_OU_ID="ou-xxxx-xxxxxxxx"      # Workload OU ID

aws cloudformation create-stack-set \
  --stack-set-name harbor-workload-role \
  --template-body file://infrastructure/ct-integration/stacksets/harbor-workload-role.yaml \
  --parameters \
    ParameterKey=HarborCentralAccountId,ParameterValue=$HARBOR_ACCOUNT_ID \
    ParameterKey=HarborApiGatewayArn,ParameterValue=$API_GW_ARN \
    ParameterKey=HarborEventBusArn,ParameterValue=$EVENT_BUS_ARN \
  --capabilities CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --profile ct-management
```

```bash
aws cloudformation create-stack-instances \
  --stack-set-name harbor-workload-role \
  --deployment-targets OrganizationalUnitIds=$WORKLOAD_OU_ID \
  --regions us-east-1 \
  --profile ct-management
```

### 2b. Verify

Pick any workload account and confirm the role exists:

```bash
aws iam get-role --role-name harbor-agent-reporter --profile workload-dev
```

The role allows assumption by principals tagged with `harbor-agent: "true"` and grants:
- `execute-api:Invoke` on the Harbor API Gateway
- `events:PutEvents` on the Harbor EventBridge bus
- `cognito-idp:InitiateAuth` for M2M token exchange

---

## Step 3: Attach SCPs

Two SCPs protect Harbor resources and enforce tagging governance.

### 3a. Deny Modify Harbor Central

**File:** `infrastructure/ct-integration/scps/deny-modify-harbor-central.json`

This SCP prevents workload accounts from modifying Harbor Central resources (DynamoDB, Lambda, API Gateway, S3, CloudFront, Cognito, EventBridge, SNS, WAF).

Replace the placeholder with your Shared Services account ID:

```bash
HARBOR_ACCOUNT_ID="111111111111"

sed "s/HARBOR_ACCOUNT_ID/$HARBOR_ACCOUNT_ID/g" \
  infrastructure/ct-integration/scps/deny-modify-harbor-central.json > /tmp/deny-modify.json
```

Attach to the Workload OU:

```bash
POLICY_ID=$(aws organizations create-policy \
  --name "deny-modify-harbor-central" \
  --description "Prevent workload accounts from modifying Harbor Central resources" \
  --type SERVICE_CONTROL_POLICY \
  --content file:///tmp/deny-modify.json \
  --query 'Policy.PolicySummary.Id' --output text \
  --profile ct-management)

aws organizations attach-policy \
  --policy-id $POLICY_ID \
  --target-id $WORKLOAD_OU_ID \
  --profile ct-management
```

### 3b. Enforce Agent Tagging

**File:** `infrastructure/ct-integration/scps/enforce-agent-tagging.json`

This SCP requires `harbor-agent`, `harbor-tenant-id`, and `harbor-environment` tags on Lambda functions, ECS services/tasks, and Bedrock agents. No placeholder replacement needed.

```bash
POLICY_ID=$(aws organizations create-policy \
  --name "enforce-harbor-agent-tagging" \
  --description "Require Harbor tags on agent compute resources" \
  --type SERVICE_CONTROL_POLICY \
  --content file://infrastructure/ct-integration/scps/enforce-agent-tagging.json \
  --query 'Policy.PolicySummary.Id' --output text \
  --profile ct-management)

aws organizations attach-policy \
  --policy-id $POLICY_ID \
  --target-id $WORKLOAD_OU_ID \
  --profile ct-management
```

### 3c. Verify

From a workload account, attempt to delete the Harbor DynamoDB table (should be denied):

```bash
aws dynamodb delete-table --table-name harbor-agent-registry \
  --profile workload-dev 2>&1 | grep -i "denied"
```

And attempt to create a Lambda without Harbor tags (should be denied):

```bash
aws lambda create-function \
  --function-name test-no-tags \
  --runtime python3.12 \
  --handler index.handler \
  --role arn:aws:iam::XXXXXXXXXXXX:role/test-role \
  --zip-file fileb://dummy.zip \
  --profile workload-dev 2>&1 | grep -i "denied"
```

---

## Step 4: Configure SSO

See **[docs/iam-identity-center-setup.md](./iam-identity-center-setup.md)** for detailed steps.

Summary:

1. Create a SAML application in IAM Identity Center for Harbor
2. Configure Cognito User Pool with a SAML identity provider pointing to IAM IC
3. Map IAM IC groups to Cognito custom attributes (`custom:role`):
   - `harbor-admins` → `admin`
   - `harbor-reviewers` → `compliance_officer` / `risk_officer`
   - `harbor-developers` → `developer`
4. Update the SPA client callback URLs in Cognito to include the CloudFront distribution URL

After configuration, users authenticate via:
```
CloudFront URL → Cognito Hosted UI → IAM Identity Center → Enterprise IdP
```

---

## Step 5: Security Hub Integration

The Security Hub integration creates custom findings for policy violations and agent suspensions.

**Handler:** `infrastructure/ct-integration/security-hub-findings/handler.py`

### 5a. Deploy the Lambda

This can be added to the Harbor CDK stack or deployed separately. For a quick standalone deployment:

```bash
cd infrastructure/ct-integration/security-hub-findings

zip handler.zip handler.py

aws lambda create-function \
  --function-name harbor-security-hub-findings \
  --runtime python3.12 \
  --handler handler.handler \
  --role arn:aws:iam::$HARBOR_ACCOUNT_ID:role/harbor-security-hub-lambda-role \
  --zip-file fileb://handler.zip \
  --environment "Variables={REGION=us-east-1}" \
  --timeout 30 \
  --profile harbor-shared-services
```

The Lambda role needs `securityhub:BatchImportFindings` permission.

### 5b. Add EventBridge rules

Route `PolicyViolation` and `AgentLifecycleChanged` events to the Lambda:

```bash
aws events put-rule \
  --name harbor-security-hub-policy-violation \
  --event-bus-name harbor-events \
  --event-pattern '{"source":["harbor"],"detail-type":["PolicyViolation"]}' \
  --profile harbor-shared-services

aws events put-targets \
  --rule harbor-security-hub-policy-violation \
  --event-bus-name harbor-events \
  --targets "Id=security-hub-lambda,Arn=arn:aws:lambda:us-east-1:${HARBOR_ACCOUNT_ID}:function:harbor-security-hub-findings" \
  --profile harbor-shared-services

aws events put-rule \
  --name harbor-security-hub-lifecycle \
  --event-bus-name harbor-events \
  --event-pattern '{"source":["harbor"],"detail-type":["AgentLifecycleChanged"]}' \
  --profile harbor-shared-services

aws events put-targets \
  --rule harbor-security-hub-lifecycle \
  --event-bus-name harbor-events \
  --targets "Id=security-hub-lambda,Arn=arn:aws:lambda:us-east-1:${HARBOR_ACCOUNT_ID}:function:harbor-security-hub-findings" \
  --profile harbor-shared-services
```

### 5c. Verify

Trigger a policy violation (e.g., via the Harbor API) and check Security Hub:

```bash
aws securityhub get-findings \
  --filters '{"CompanyName":[{"Value":"Harbor","Comparison":"EQUALS"}]}' \
  --profile harbor-shared-services
```

Findings are created with severity based on policy type:
- `communication` violations → HIGH
- `capability` violations → MEDIUM
- `schedule` violations → LOW
- Agent suspensions → CRITICAL

---

## Step 6: Deploy Config Rules

The Config custom rule checks that Lambda/ECS resources tagged as Harbor agents are actually registered and published in Harbor.

**Handler:** `infrastructure/ct-integration/config-rules/agent_compliance_rule.py`

### 6a. Deploy to workload accounts via StackSet

Package the Lambda and deploy as a Config custom rule to workload accounts:

```bash
cd infrastructure/ct-integration/config-rules
zip agent_compliance_rule.zip agent_compliance_rule.py

# Upload to an S3 bucket accessible by workload accounts
aws s3 cp agent_compliance_rule.zip s3://harbor-deployment-artifacts/config-rules/ \
  --profile harbor-shared-services
```

Create a StackSet (or add to the existing workload StackSet) that deploys:
- The Lambda function with `HARBOR_API_URL` environment variable
- An AWS Config custom rule targeting `AWS::Lambda::Function` and `AWS::ECS::Service`

Set the environment variable to the Harbor API URL from Step 1:

```
HARBOR_API_URL=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/api/v1
```

### 6b. Verify

In a workload account, create a Lambda tagged with `harbor-agent: "true"` but not registered in Harbor:

```bash
aws configservice get-compliance-details-by-resource \
  --resource-type AWS::Lambda::Function \
  --resource-id <function-name> \
  --profile workload-dev
```

Expected result: `NON_COMPLIANT` with annotation "Harbor API unreachable or agent not registered".

---

## Post-Deployment Verification Checklist

Run through each item after completing all steps:

- [ ] Harbor UI accessible at CloudFront URL via SSO login
- [ ] Agent registration works from a workload account using `harbor-agent-reporter` role
- [ ] Cross-account EventBridge events flow from workload accounts to `harbor-events` bus
- [ ] SCPs block workload accounts from modifying Harbor Central resources
- [ ] SCPs enforce `harbor-agent`, `harbor-tenant-id`, `harbor-environment` tags
- [ ] Security Hub findings appear for policy violations
- [ ] Config rules evaluate agent compliance in workload accounts
- [ ] SNS alerts fire on lifecycle transitions and policy violations (`harbor-alerts` topic)

---

## Rollback

Reverse the deployment in this order to avoid lockouts:

```bash
# 1. Remove SCPs first (prevents accidental lockout)
aws organizations detach-policy --policy-id <deny-modify-policy-id> --target-id $WORKLOAD_OU_ID --profile ct-management
aws organizations detach-policy --policy-id <enforce-tagging-policy-id> --target-id $WORKLOAD_OU_ID --profile ct-management
aws organizations delete-policy --policy-id <deny-modify-policy-id> --profile ct-management
aws organizations delete-policy --policy-id <enforce-tagging-policy-id> --profile ct-management

# 2. Delete Config rule StackSet instances
aws cloudformation delete-stack-instances \
  --stack-set-name harbor-config-rules \
  --deployment-targets OrganizationalUnitIds=$WORKLOAD_OU_ID \
  --regions us-east-1 --no-retain-stacks --profile ct-management

# 3. Delete workload role StackSet instances
aws cloudformation delete-stack-instances \
  --stack-set-name harbor-workload-role \
  --deployment-targets OrganizationalUnitIds=$WORKLOAD_OU_ID \
  --regions us-east-1 --no-retain-stacks --profile ct-management

# 4. Delete Security Hub Lambda and EventBridge rules
aws lambda delete-function --function-name harbor-security-hub-findings --profile harbor-shared-services
aws events remove-targets --rule harbor-security-hub-policy-violation --ids security-hub-lambda --event-bus-name harbor-events --profile harbor-shared-services
aws events remove-targets --rule harbor-security-hub-lifecycle --ids security-hub-lambda --event-bus-name harbor-events --profile harbor-shared-services
aws events delete-rule --name harbor-security-hub-policy-violation --event-bus-name harbor-events --profile harbor-shared-services
aws events delete-rule --name harbor-security-hub-lifecycle --event-bus-name harbor-events --profile harbor-shared-services

# 5. Delete StackSets
aws cloudformation delete-stack-set --stack-set-name harbor-workload-role --profile ct-management
aws cloudformation delete-stack-set --stack-set-name harbor-config-rules --profile ct-management

# 6. Destroy Harbor CDK stack (DynamoDB retained in prod)
cd infrastructure && npx cdk destroy --profile harbor-shared-services
```

> **Warning:** In production, the DynamoDB table has `RemovalPolicy.RETAIN`. You must delete it manually if full cleanup is needed.
