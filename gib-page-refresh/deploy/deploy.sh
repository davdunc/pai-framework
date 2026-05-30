#!/usr/bin/env bash
# Build, package, and deploy the gib-page-refresh CloudFormation stack.
#
# Usage:
#   GITLAB_TOKEN=glpat-... ./deploy/deploy.sh

set -euo pipefail

PROFILE="${AWS_PROFILE:-pai-linux}"
REGION="${AWS_REGION:-us-east-2}"
STACK="${STACK_NAME:-gib-page-refresh}"
BUCKET="${STAGING_BUCKET:-davdunc-pai-backup}"
SCHEDULE_EXPR="${SCHEDULE_EXPRESSION:-cron(5 11 ? * MON-FRI *)}"
GITLAB_PROJECT_PATH="${GITLAB_PROJECT_PATH:-rubackedup-com/davidduncan.org}"
GITLAB_BRANCH="${GITLAB_BRANCH:-main}"
TELOS_S3_PREFIX="${TELOS_S3_PREFIX:-claude/PAI/USER/TELOS/}"

if [[ -z "${GITLAB_TOKEN:-}" ]]; then
  echo "ERROR: GITLAB_TOKEN must be set (Project Access Token with write_repository scope)." >&2
  exit 1
fi

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_SRC="$PROJECT_ROOT/lambda"
TEMPLATE="$PROJECT_ROOT/cloudformation/gib-page-refresh.yaml"

TS="$(date -u +%Y%m%d-%H%M%S)"
ZIP_LOCAL="/tmp/gib-page-refresh-${TS}.zip"
ZIP_KEY="cfn-staging/gib-page-refresh/gib-page-refresh-${TS}.zip"

echo "== build lambda zip =="
( cd "$LAMBDA_SRC" && zip -qr "$ZIP_LOCAL" . )
ls -lh "$ZIP_LOCAL"

echo "== upload to s3://$BUCKET/$ZIP_KEY =="
aws --profile "$PROFILE" s3 cp "$ZIP_LOCAL" "s3://$BUCKET/$ZIP_KEY" --region "$REGION" --quiet

echo "== validate template =="
aws --profile "$PROFILE" cloudformation validate-template \
  --template-body "file://$TEMPLATE" --region "$REGION" >/dev/null

echo "== deploy stack =="
aws --profile "$PROFILE" cloudformation deploy \
  --stack-name "$STACK" \
  --template-file "$TEMPLATE" \
  --parameter-overrides \
      CodeS3Bucket="$BUCKET" \
      CodeS3Key="$ZIP_KEY" \
      TelosS3Bucket="$BUCKET" \
      TelosS3Prefix="$TELOS_S3_PREFIX" \
      GitlabProjectPath="$GITLAB_PROJECT_PATH" \
      GitlabBranch="$GITLAB_BRANCH" \
      GitlabToken="$GITLAB_TOKEN" \
      ScheduleExpression="$SCHEDULE_EXPR" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

echo "== outputs =="
aws --profile "$PROFILE" cloudformation describe-stacks \
  --stack-name "$STACK" --region "$REGION" \
  --query 'Stacks[0].Outputs' --output table
