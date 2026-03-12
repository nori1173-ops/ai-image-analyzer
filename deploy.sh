#!/bin/bash
set -euo pipefail

if [ -z "${AWS_PROFILE:-}" ]; then
  echo "ERROR: AWS_PROFILE environment variable is not set."
  echo "Set it with: export AWS_PROFILE=your_profile_name"
  exit 1
fi

ENV="${1:-dev}"
REGION="ap-northeast-1"
SSM_PARAM_PATH="/image-analysis/openai-api-key"

case "$ENV" in
  dev)
    SAM_CONFIG_ENV=""
    STACK_NAME="image-analysis-dev"
    ;;
  prod)
    SAM_CONFIG_ENV="--config-env production"
    STACK_NAME="image-analysis-api"
    ;;
  *)
    echo "Usage: bash deploy.sh [dev|prod]"
    echo "  dev  - Deploy to development environment (default)"
    echo "  prod - Deploy to production environment"
    exit 1
    ;;
esac

echo "=== Deploying to: $ENV ==="
echo "Stack: $STACK_NAME"
echo ""

echo "=== Step 1: SSM Parameter existence check ==="
if ! aws ssm get-parameter --name "$SSM_PARAM_PATH" --profile "$AWS_PROFILE" --region "$REGION" > /dev/null 2>&1; then
  echo "ERROR: SSM Parameter $SSM_PARAM_PATH does not exist."
  echo "Create it with:"
  echo "  aws ssm put-parameter --name $SSM_PARAM_PATH --type SecureString --value YOUR_KEY --profile $AWS_PROFILE --region $REGION"
  exit 1
fi
echo "SSM Parameter found."

echo ""
echo "=== Step 2: SAM build ==="
sam build --profile "$AWS_PROFILE" --region "$REGION"

echo ""
echo "=== Step 3: Deploy (nested stacks) ==="
sam deploy --profile "$AWS_PROFILE" --region "$REGION" $SAM_CONFIG_ENV

echo ""
echo "=== Step 4: Generate frontend Amplify config ==="
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" \
  --output text \
  --profile "$AWS_PROFILE" \
  --region "$REGION")
USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolClientId'].OutputValue" \
  --output text \
  --profile "$AWS_PROFILE" \
  --region "$REGION")
cat > frontend/src/amplifyconfiguration.ts << AMPLIFY_EOF
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: '${USER_POOL_ID}',
      userPoolClientId: '${USER_POOL_CLIENT_ID}',
    }
  }
}

export default amplifyConfig
AMPLIFY_EOF
echo "Generated frontend/src/amplifyconfiguration.ts"

echo ""
echo "=== Step 5: Sync frontend to S3 ==="
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text \
  --profile "$AWS_PROFILE" \
  --region "$REGION")

if [ -d "frontend/dist" ]; then
  aws s3 sync frontend/dist/ "s3://${BUCKET_NAME}/" \
    --delete \
    --profile "$AWS_PROFILE" \
    --region "$REGION"
  echo "Frontend synced to s3://${BUCKET_NAME}/"
else
  echo "WARNING: frontend/dist/ not found. Skipping S3 sync."
fi

echo ""
echo "=== Step 6: CloudFront invalidation ==="
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" \
  --output text \
  --profile "$AWS_PROFILE" \
  --region "$REGION")

aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*" \
  --profile "$AWS_PROFILE"

echo ""
echo "=== Deploy completed ($ENV) ==="
CUSTOM_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='CustomDomainUrl'].OutputValue" \
  --output text \
  --profile "$AWS_PROFILE" \
  --region "$REGION" 2>/dev/null || echo "N/A")
echo "Custom URL: $CUSTOM_URL"
