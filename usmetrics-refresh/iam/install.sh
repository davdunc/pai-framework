#!/usr/bin/env bash
# Install (or update) the PAI-USMetricsRefresh-Deploy managed policy.
#
# Substitutes the __ACCOUNT_ID__ placeholder in the source JSON with the
# active AWS account, then either creates the policy (first install) or
# creates a new policy version + sets it as default (subsequent updates).
#
# Usage:
#   AWS_PROFILE=personal ./iam/install.sh
#
# Defaults to profile=personal (the admin profile that can write IAM).

set -euo pipefail

PROFILE="${AWS_PROFILE:-personal}"
POLICY_NAME="PAI-USMetricsRefresh-Deploy"

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$PROJECT_ROOT/iam/${POLICY_NAME}.json"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: source policy not found: $SRC" >&2
  exit 1
fi

echo "== resolve account id =="
ACCOUNT_ID="$(aws --profile "$PROFILE" sts get-caller-identity --query Account --output text)"
if [[ -z "$ACCOUNT_ID" || "$ACCOUNT_ID" == "None" ]]; then
  echo "ERROR: failed to resolve account id under profile $PROFILE" >&2
  exit 1
fi
echo "  account: $ACCOUNT_ID"

TMP="$(mktemp -t usmetrics-deploy-policy.XXXXXX.json)"
trap 'rm -f "$TMP"' EXIT
sed "s/__ACCOUNT_ID__/${ACCOUNT_ID}/g" "$SRC" > "$TMP"

POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws --profile "$PROFILE" iam get-policy --policy-arn "$POLICY_ARN" >/dev/null 2>&1; then
  echo "== policy exists; creating new version =="
  aws --profile "$PROFILE" iam create-policy-version \
    --policy-arn "$POLICY_ARN" \
    --policy-document "file://$TMP" \
    --set-as-default \
    --query 'PolicyVersion.{Version:VersionId,Default:IsDefaultVersion,Created:CreateDate}' \
    --output table
else
  echo "== policy does not exist; creating =="
  aws --profile "$PROFILE" iam create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document "file://$TMP" \
    --description "CFN + Lambda + Scheduler deploy permissions for usmetrics-* resources" \
    --tags Key=Purpose,Value=usmetrics-notion-refresh Key=ManagedBy,Value=PAI \
    --query 'Policy.{Arn:Arn,Created:CreateDate}' \
    --output table

  echo
  echo "Next: attach to each workstation user that should deploy this stack, e.g."
  echo "  aws --profile $PROFILE iam attach-user-policy \\"
  echo "    --user-name pai-workstation-linux --policy-arn $POLICY_ARN"
fi
