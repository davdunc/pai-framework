#!/usr/bin/env bash
# Build, package, and deploy the usmetrics-notion-refresh CloudFormation stack.
#
# Usage:
#   NOTION_TOKEN=ntn_... FRED_API_KEY=... EIA_API_KEY=... ./deploy/deploy.sh
#
# Defaults to AWS_PROFILE=pai-linux, REGION=us-east-2.

set -euo pipefail

PROFILE="${AWS_PROFILE:-pai-linux}"
REGION="${AWS_REGION:-us-east-2}"
STACK="${STACK_NAME:-usmetrics-notion-refresh}"
BUCKET="${STAGING_BUCKET:-davdunc-pai-backup}"
NOTION_PAGE_ID="${NOTION_PAGE_ID:-36e973b9-8fae-8159-9cac-c16f85164ca5}"
SCHEDULE_EXPR="${SCHEDULE_EXPRESSION:-cron(0 11 * * ? *)}"

if [[ -z "${NOTION_TOKEN:-}" || -z "${FRED_API_KEY:-}" ]]; then
  echo "ERROR: NOTION_TOKEN and FRED_API_KEY must be set in the environment." >&2
  exit 1
fi
EIA_API_KEY="${EIA_API_KEY:-}"

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_SRC="$PROJECT_ROOT/lambda"
TEMPLATE="$PROJECT_ROOT/cloudformation/usmetrics-notion-refresh.yaml"

TS="$(date -u +%Y%m%d-%H%M%S)"
ZIP_LOCAL="/tmp/usmetrics-notion-refresh-${TS}.zip"
ZIP_KEY="cfn-staging/usmetrics-refresh/usmetrics-notion-refresh-${TS}.zip"

echo "== build lambda zip =="
( cd "$LAMBDA_SRC" && zip -qr "$ZIP_LOCAL" . )
ls -lh "$ZIP_LOCAL"

echo "== upload to s3://$BUCKET/$ZIP_KEY =="
aws --profile "$PROFILE" s3 cp "$ZIP_LOCAL" "s3://$BUCKET/$ZIP_KEY" --region "$REGION" --quiet

echo "== validate template =="
aws --profile "$PROFILE" cloudformation validate-template \
  --template-body "file://$TEMPLATE" \
  --region "$REGION" >/dev/null

echo "== deploy stack =="
aws --profile "$PROFILE" cloudformation deploy \
  --stack-name "$STACK" \
  --template-file "$TEMPLATE" \
  --parameter-overrides \
      CodeS3Bucket="$BUCKET" \
      CodeS3Key="$ZIP_KEY" \
      NotionPageId="$NOTION_PAGE_ID" \
      NotionToken="$NOTION_TOKEN" \
      FredApiKey="$FRED_API_KEY" \
      EiaApiKey="$EIA_API_KEY" \
      ScheduleExpression="$SCHEDULE_EXPR" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

echo "== outputs =="
aws --profile "$PROFILE" cloudformation describe-stacks \
  --stack-name "$STACK" --region "$REGION" \
  --query 'Stacks[0].Outputs' --output table

echo
echo "Done. Test invoke:"
echo "  aws --profile $PROFILE lambda invoke --function-name usmetrics-notion-refresh \\"
echo "    --cli-binary-format raw-in-base64-out --region $REGION /tmp/usmetrics-response.json"
echo "  cat /tmp/usmetrics-response.json"
