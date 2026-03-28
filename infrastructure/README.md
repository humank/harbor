"""CDK stack for Harbor DynamoDB table."""

# Usage:
#   cdk deploy --app "python infrastructure/stack.py"
#
# Or create the table manually via AWS CLI:
#
#   aws dynamodb create-table \
#     --table-name harbor-agent-registry \
#     --attribute-definitions \
#       AttributeName=pk,AttributeType=S \
#       AttributeName=sk,AttributeType=S \
#       AttributeName=status,AttributeType=S \
#       AttributeName=updated_at,AttributeType=S \
#     --key-schema \
#       AttributeName=pk,KeyType=HASH \
#       AttributeName=sk,KeyType=RANGE \
#     --global-secondary-indexes \
#       '[{"IndexName":"status-index","KeySchema":[{"AttributeName":"status","KeyType":"HASH"},{"AttributeName":"updated_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
#     --billing-mode PAY_PER_REQUEST
