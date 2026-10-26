#!/usr/bin/env bash
# One-time setup for keyless GitHub Actions -> GCP auth (Workload Identity Federation).
# Run once, as the project owner, from a machine with gcloud, bq and gh logged in.
#
# Creates, idempotently:
#   - a service account the workflow runs as (job user on the project, owner of the one dataset)
#   - a workload identity pool and a GitHub OIDC provider that only trusts this repository
#   - the IAM binding that lets that repository's workflows impersonate the service account
#   - the three repository variables .github/workflows/rebuild.yml reads (none is a secret)
#
# No service-account key is ever created or stored.
set -euo pipefail

PROJECT=${GCP_PROJECT_ID:-powerwatch-2026ldm}
DATASET=${BQ_DATASET:-powerwatch}
REPO=${GITHUB_REPO:-loudiman/powerwatch}
SA_NAME=powerwatch-ci
SA="$SA_NAME@$PROJECT.iam.gserviceaccount.com"
POOL=github
PROVIDER=powerwatch

NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
echo "project $PROJECT ($NUMBER), repo $REPO"

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com --project "$PROJECT"

gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "$SA_NAME" --project "$PROJECT" --display-name "PowerWatch CI (GitHub Actions)"

# Run query and load jobs in the project.
gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA" \
  --role roles/bigquery.jobUser --condition=None >/dev/null
# Own the one dataset: create/replace its tables and read or update its default expiry.
bq --project_id="$PROJECT" query --use_legacy_sql=false --format=none \
  "GRANT \`roles/bigquery.dataOwner\` ON SCHEMA \`$PROJECT.$DATASET\` TO \"serviceAccount:$SA\""

gcloud iam workload-identity-pools describe "$POOL" --location global --project "$PROJECT" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create "$POOL" --location global --project "$PROJECT" --display-name "GitHub Actions"

gcloud iam workload-identity-pools providers describe "$PROVIDER" --workload-identity-pool "$POOL" \
  --location global --project "$PROJECT" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
    --workload-identity-pool "$POOL" --location global --project "$PROJECT" \
    --issuer-uri https://token.actions.githubusercontent.com \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition "assertion.repository == '$REPO'"

gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT" \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository/$REPO" >/dev/null

WIF_PROVIDER="projects/$NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
gh variable set GCP_PROJECT_ID --repo "$REPO" --body "$PROJECT"
gh variable set GCP_SERVICE_ACCOUNT --repo "$REPO" --body "$SA"
gh variable set GCP_WIF_PROVIDER --repo "$REPO" --body "$WIF_PROVIDER"

echo
echo "Done. First run:  gh workflow run rebuild-warehouse --repo $REPO"
echo "Then watch it:    gh run watch --repo $REPO"
