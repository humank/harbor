# Harbor — CDK Infrastructure Standards

All infrastructure code in `infrastructure/` MUST follow these standards.

---

## Tech Stack

- **AWS CDK v2** with TypeScript.
- **Single CDK app** in `infrastructure/bin/harbor.ts`.
- **Constructs library**: `aws-cdk-lib` only. No experimental modules unless necessary.

## Project Structure

```
infrastructure/
├── bin/
│   └── harbor.ts            # CDK app entry point
├── lib/
│   ├── harbor-stack.ts      # Main stack (all resources)
│   ├── constructs/          # Custom L3 constructs (if needed)
│   └── config.ts            # Environment config (account, region, table name)
├── package.json
├── tsconfig.json
└── cdk.json
```

## Stack Design

Single stack `HarborStack` containing all resources:

1. **DynamoDB Table**
   - Table name from config (default: `harbor-agent-registry`)
   - PK: `pk` (String), SK: `sk` (String)
   - GSI: `status-index` (PK: `status`, SK: `updated_at`)
   - Billing: PAY_PER_REQUEST
   - Point-in-time recovery: enabled
   - Removal policy: RETAIN (production) or DESTROY (dev)

2. **Lambda Function**
   - Runtime: Python 3.12
   - Handler: `harbor.main.handler` (Mangum)
   - Memory: 256 MB
   - Timeout: 30 seconds
   - Architecture: ARM64 (Graviton, cheaper)
   - Bundling: Docker-based (for native dependencies)
   - Environment: TABLE_NAME, AWS_REGION
   - IAM: DynamoDB read/write on the table + indexes

3. **API Gateway (HTTP API)**
   - Routes: `ANY /api/{proxy+}` → Lambda integration
   - CORS: Allow frontend origin
   - Throttling: 100 req/s burst, 50 req/s sustained
   - Stage: `$default` (no stage prefix)

4. **S3 Bucket (Frontend)**
   - Block all public access
   - Versioning enabled
   - Encryption: S3-managed (SSE-S3)
   - Auto-delete objects on stack destroy (dev only)

5. **CloudFront Distribution**
   - Default behavior: S3 origin (frontend)
   - `/api/*` behavior: API Gateway origin
   - OAC for S3 access
   - HTTPS only, TLS 1.2 minimum
   - Default root object: `index.html`
   - Custom error response: 403/404 → /index.html (SPA routing)

6. **WAF WebACL**
   - AWS Managed Rules: CommonRuleSet
   - Rate limiting: 1000 requests per 5 minutes per IP
   - Associated with CloudFront distribution

7. **Cognito User Pool** (optional, gated by config flag)
   - Self-signup disabled (admin-only)
   - Email as username
   - API Gateway authorizer integration

## Naming Conventions

- Stack name: `HarborStack`
- Resource IDs: PascalCase (`AgentRegistryTable`, `ApiFunction`, `FrontendBucket`)
- Physical names: kebab-case with `harbor-` prefix (`harbor-agent-registry`, `harbor-api`)
- Tags: `Project=Harbor`, `Environment=dev|prod`

## Configuration

Use a config object, not hardcoded values:

```typescript
// lib/config.ts
export interface HarborConfig {
  tableName: string;
  environment: 'dev' | 'prod';
  enableAuth: boolean;
}

export const devConfig: HarborConfig = {
  tableName: 'harbor-agent-registry',
  environment: 'dev',
  enableAuth: false,
};
```

## Security Rules

- Lambda function has LEAST PRIVILEGE IAM policy.
- S3 bucket is NOT public. Access only via CloudFront OAC.
- API Gateway has throttling configured.
- WAF protects CloudFront.
- No secrets in CDK code. Use SSM Parameter Store or Secrets Manager.
- Enable CloudTrail for API audit (account-level, not stack-level).

## Deploy & Destroy

- Deploy: `cd infrastructure && npx cdk deploy --profile <profile>`
- Destroy: `cd infrastructure && npx cdk destroy --profile <profile>`
- Diff: `cd infrastructure && npx cdk diff`
- Synth: `cd infrastructure && npx cdk synth`

## Testing

- CDK snapshot tests in `infrastructure/test/`.
- CDK assertion tests for critical resource properties.
- Run: `cd infrastructure && npm test`
