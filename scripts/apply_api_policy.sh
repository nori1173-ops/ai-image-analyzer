#!/bin/bash
set -euo pipefail

PROFILE="your-profile"
REGION="ap-northeast-1"
API_STACK_NAME="image-analysis-api"

API_ID=$(aws cloudformation describe-stacks \
  --stack-name "$API_STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='RestApiId'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

ORIGIN_VERIFY_HEADER="${1:-x-origin-verify}"
ORIGIN_VERIFY_VALUE="${2:-your-origin-verify-secret}"

echo "Applying resource policy to API Gateway: $API_ID"

POLICY=$(cat <<POLICY_EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:${REGION}:*:${API_ID}/*"
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:${REGION}:*:${API_ID}/*",
      "Condition": {
        "StringNotEquals": {
          "aws:Referer": "${ORIGIN_VERIFY_VALUE}"
        }
      }
    }
  ]
}
POLICY_EOF
)

aws apigateway update-rest-api \
  --rest-api-id "$API_ID" \
  --patch-operations "op=replace,path=/policy,value=$(echo "$POLICY" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')" \
  --profile "$PROFILE" \
  --region "$REGION"

echo "Deploying API to apply policy..."
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name prod \
  --profile "$PROFILE" \
  --region "$REGION"

echo "Resource policy applied successfully."
