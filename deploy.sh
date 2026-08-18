#!/bin/bash
set -euo pipefail

if [ -z "${AWS_PROFILE:-}" ]; then
  echo "ERROR: AWS_PROFILE environment variable is not set."
  echo "Set it with: export AWS_PROFILE=your_profile_name"
  exit 1
fi

ENV="${1:-dev}"
REGION="ap-northeast-1"
LAYER_ARN="arn:aws:lambda:ap-northeast-1:210000000001:layer:ExamplePowertoolsPython:74"
ALLOWED_IMAGE_BUCKETS="${ALLOWED_IMAGE_BUCKETS:-}"
ANTHROPIC_WORKSPACE_ID="${ANTHROPIC_WORKSPACE_ID:-wrkspc_00000000000000000000000000}"
DEFAULT_MODEL="${DEFAULT_MODEL:-anthropic.claude-sonnet-5}"

case "$ENV" in
  dev)
    SAM_CONFIG_ENV=""
    STACK_NAME="image-analysis-dev"
    LOG_LEVEL="DEBUG"
    SUB_DOMAIN="image-analysis-dev"
    MODEL_CATALOG_BUCKET="ai-model-selector-dev-data-210000000001"
    ;;
  prod)
    SAM_CONFIG_ENV="--config-env production"
    STACK_NAME="image-analysis-api"
    LOG_LEVEL="INFO"
    SUB_DOMAIN="image-analysis"
    MODEL_CATALOG_BUCKET="ai-model-selector-data-210000000001"
    ;;
  *)
    echo "Usage: bash deploy.sh [dev|prod]"
    echo "  dev  - Deploy to development environment (default)"
    echo "  prod - Deploy to production environment"
    exit 1
    ;;
esac

ORIGIN_VERIFY_SSM_PATH="/${STACK_NAME}/origin-verify"

echo "=== Deploying to: $ENV ==="
echo "Stack: $STACK_NAME"
echo ""

echo "=== Step 1b: Origin verify secret (SSM) ==="
if ! aws ssm get-parameter --name "$ORIGIN_VERIFY_SSM_PATH" --profile "$AWS_PROFILE" --region "$REGION" > /dev/null 2>&1; then
  echo "Origin verify secret not found. Generating a new one at $ORIGIN_VERIFY_SSM_PATH"
  GENERATED_SECRET=$(openssl rand -hex 16)
  aws ssm put-parameter \
    --name "$ORIGIN_VERIFY_SSM_PATH" \
    --type String \
    --value "$GENERATED_SECRET" \
    --profile "$AWS_PROFILE" \
    --region "$REGION" > /dev/null
  echo "Generated and stored origin verify secret."
fi
ORIGIN_VERIFY_VALUE=$(aws ssm get-parameter \
  --name "$ORIGIN_VERIFY_SSM_PATH" \
  --query "Parameter.Value" \
  --output text \
  --profile "$AWS_PROFILE" \
  --region "$REGION")

echo ""
echo "=== Step 2: SAM build ==="
sam build --profile "$AWS_PROFILE" --region "$REGION"

echo ""
echo "=== Step 3: Deploy (nested stacks) ==="
PARAM_OVERRIDES=(
  "LogLevel=${LOG_LEVEL}"
  "SubDomain=${SUB_DOMAIN}"
  "ExamplePowertoolsPython=${LAYER_ARN}"
  "OriginVerifyValue=${ORIGIN_VERIFY_VALUE}"
  "DefaultModel=${DEFAULT_MODEL}"
  "ModelCatalogBucket=${MODEL_CATALOG_BUCKET}"
)
if [ -n "$ALLOWED_IMAGE_BUCKETS" ]; then
  PARAM_OVERRIDES+=("AllowedImageBuckets=${ALLOWED_IMAGE_BUCKETS}")
fi
if [ -n "$ANTHROPIC_WORKSPACE_ID" ]; then
  PARAM_OVERRIDES+=("AnthropicWorkspaceId=${ANTHROPIC_WORKSPACE_ID}")
fi
sam deploy --profile "$AWS_PROFILE" --region "$REGION" $SAM_CONFIG_ENV \
  --parameter-overrides "${PARAM_OVERRIDES[@]}"

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
echo "=== Step 4b: Build frontend (must run after Amplify config generation) ==="
if [ -d "frontend/node_modules" ]; then
  npm --prefix frontend run build
else
  echo "WARNING: frontend/node_modules not found. Skipping frontend build."
fi

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
