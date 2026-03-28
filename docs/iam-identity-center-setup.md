# Harbor — IAM Identity Center Integration Guide

This guide walks your Cloud Team through integrating Harbor with an existing IAM Identity Center (SSO) deployment, so users authenticate via your enterprise IdP and land in Harbor with the correct tenant and role claims.

---

## Prerequisites

- IAM Identity Center enabled in the Management Account
- Harbor deployed to the Shared Services account with a Cognito User Pool provisioned
- Enterprise IdP (Active Directory, Okta, Azure AD, etc.) already connected to IAM Identity Center
- Admin access to both the IAM Identity Center console and the Cognito console

---

## Step 1: Create a SAML Application in IAM Identity Center

1. Open the **IAM Identity Center** console in the Management Account.
2. Go to **Applications → Add application → Add custom SAML 2.0 application**.
3. Configure the application:

| Field | Value |
|---|---|
| Application name | `Harbor` |
| Description | Agent Platform Management |
| Application ACS URL | `https://{cognito-domain}.auth.{region}.amazoncognito.com/saml2/idpresponse` |
| Application SAML audience (Entity ID) | `urn:amazon:cognito:sp:{user-pool-id}` |

4. Click **Submit**.
5. On the application detail page, download the **IAM Identity Center SAML metadata file** — you'll upload this to Cognito in the next step.

---

## Step 2: Configure Cognito SAML Identity Provider

1. Open the **Cognito** console in the Shared Services account.
2. Select the Harbor User Pool → **Sign-in experience** → **Federated identity providers** → **Add identity provider**.
3. Choose **SAML** and configure:

| Field | Value |
|---|---|
| Provider name | `IAMIdentityCenter` |
| Metadata document | Upload the XML file from Step 1 |

4. Under **Attribute mapping**, map the SAML assertions to Cognito user attributes:

| SAML Attribute | Cognito Attribute | Notes |
|---|---|---|
| `Subject` (NameID) | `email` | IAM IC sends email as NameID by default |
| `email` | `email` | Explicit email claim |
| `custom:tenant_id` | `custom:tenant_id` | Mapped from IAM IC attribute (see Step 5) |
| `custom:role` | `custom:role` | Mapped from IAM IC group membership (see Step 5) |

5. Save the identity provider.

---

## Step 3: Update Cognito App Client

1. In the Harbor User Pool, go to **App integration** → select the SPA app client.
2. Under **Hosted UI**, edit the configuration:
   - **Identity providers**: Enable `IAMIdentityCenter` (and optionally disable Cognito user pool sign-in if SSO is the only auth method).
   - **Callback URL(s)**: Add your production domain:
     ```
     https://{harbor-domain}/callback
     ```
   - **Sign-out URL(s)**:
     ```
     https://{harbor-domain}/logout
     ```
   - **OAuth 2.0 grant types**: Ensure `Authorization code grant` is selected (PKCE flow).
   - **OpenID Connect scopes**: `openid`, `email`, `profile`.
3. Save changes.

---

## Step 4: Create Permission Sets and Group Mappings

In IAM Identity Center, create permission sets that correspond to Harbor roles:

| Permission Set | Harbor Role (`custom:role`) | Intended Users |
|---|---|---|
| `HarborViewer` | `viewer` | All users (read-only access) |
| `HarborDeveloper` | `developer` | Agent developers |
| `HarborAdmin` | `project_admin` | Team leads, project owners |
| `HarborRiskOfficer` | `risk_officer` | Risk team (prod approval) |
| `HarborComplianceOfficer` | `compliance_officer` | Compliance team (prod approval) |

Then create or reuse IAM Identity Center **groups** and assign them:

1. Go to **Groups** → create groups like `Harbor-Viewers`, `Harbor-Developers`, `Harbor-Admins`, `Harbor-Risk`, `Harbor-Compliance`.
2. Assign users from your enterprise IdP to the appropriate groups.
3. Under the Harbor application, assign each group and map it to the corresponding permission set.

---

## Step 5: Configure SAML Attribute Statements

In the IAM Identity Center Harbor application, go to **Attribute mappings** and add these attribute statements:

| Application attribute | Maps to | Format |
|---|---|---|
| `Subject` | `${user:email}` | `emailAddress` |
| `email` | `${user:email}` | `unspecified` |
| `custom:role` | `${user:groups}` | `unspecified` |
| `custom:tenant_id` | `${user:AD_GUID}` or custom attribute | `unspecified` |

For `custom:role`, IAM Identity Center sends group names. You have two options:

**Option A — Direct group name mapping**: Configure your Cognito pre-token-generation Lambda trigger to translate group names (e.g., `Harbor-Developers`) into Harbor role values (e.g., `developer`).

**Option B — Custom attribute in IdP**: If your enterprise IdP (AD/Okta) has a dedicated attribute for Harbor role, map it directly.

For `custom:tenant_id`, map this to the AWS account ID associated with the user's project. This typically comes from:
- A custom attribute in your IdP (recommended)
- The department field, if your org maps departments to AWS accounts
- A Cognito pre-token-generation Lambda that resolves account ID from org metadata

---

## Step 6: Test SSO Login

1. Open the **IAM Identity Center access portal** (`https://{sso-start-url}`).
2. Sign in with your enterprise credentials.
3. Click the **Harbor** application tile.
4. You should be redirected to the Harbor UI, authenticated.
5. Verify the JWT contains the expected claims by checking the browser console or the Harbor `/api/v1/agents` response:
   - `email` — user's email
   - `custom:tenant_id` — the correct AWS account ID
   - `custom:role` — the correct Harbor role (e.g., `developer`)

To decode the JWT manually:

```bash
# Paste the id_token from browser storage
echo "{id_token}" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Redirect fails after IdP login | Callback URL mismatch | Verify the ACS URL in IAM IC matches Cognito's SAML endpoint exactly |
| `custom:tenant_id` is empty in JWT | Attribute mapping missing | Check IAM IC attribute statements and Cognito attribute mapping |
| `custom:role` shows group name instead of role | No translation layer | Add a pre-token-generation Lambda to map group names → role values |
| User gets 401 from Harbor API | JWT expired or wrong audience | Verify the app client ID matches the `aud` claim; check token expiry |
| User can log in but sees no agents | Wrong `tenant_id` | Confirm the tenant_id in the JWT matches the DynamoDB partition key prefix |
| SAML assertion error in Cognito | Metadata XML stale | Re-download metadata from IAM IC and re-upload to Cognito |
| User not appearing in Harbor | Group not assigned to application | In IAM IC, ensure the user's group is assigned to the Harbor application |
