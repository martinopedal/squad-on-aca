#!/usr/bin/env bash
set +x
set -euo pipefail

log() { printf '%s\n' "$*"; }
die() { log "FATAL: $*"; exit 1; }
source "$(dirname "${BASH_SOURCE[0]}")/github-app.sh"

for name in SQUAD_TARGET_REPO SQUAD_POLL_ISSUE_NUMBER SQUAD_POLL_AGENT SQUAD_POLL_STOP_AFTER_UTC AZURE_STORAGE_ACCOUNT QUEUE_NAME AZURE_CLIENT_ID GITHUB_APP_ID GITHUB_APP_INSTALLATION_ID KEY_VAULT_NAME KEY_VAULT_SECRET_NAME; do
  [[ -n "${!name:-}" ]] || die "Required poller setting ${name} missing."
done
[[ "${SQUAD_TARGET_REPO}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "Invalid poll target."
[[ "${SQUAD_POLL_ISSUE_NUMBER}" =~ ^[1-9][0-9]*$ ]] || die "Invalid approved issue."
[[ "${SQUAD_POLL_AGENT}" =~ ^[A-Za-z0-9_-]+$ ]] || die "Invalid approved agent."
STOP=$(date -d "${SQUAD_POLL_STOP_AFTER_UTC}" +%s 2>/dev/null) || die "Invalid poll cutoff."
if (( $(date +%s) >= STOP )); then
  log "Poll window expired; no authentication or queue activity."
  exit 0
fi
export GITHUB_HTTP_TIMEOUT_SECONDS=8
az login --identity --client-id "${AZURE_CLIENT_ID}" --allow-no-subscriptions -o none >/dev/null 2>&1 \
  || die "Poller Managed Identity login failed."
TOKEN=$(github_app_token "${SQUAD_TARGET_REPO}" poller) \
  || die "Poller App token denied, expired or over-permissioned; no queue write."
API="https://api.github.com/repos/${SQUAD_TARGET_REPO}"
NUMBER="${SQUAD_POLL_ISSUE_NUMBER}"
AGENT="${SQUAD_POLL_AGENT}"
ISSUE=$(github_request GET "${API}/issues/${NUMBER}" "${TOKEN}") || die "Approved issue read failed."
printf '%s' "${ISSUE}" | jq -e --argjson number "${NUMBER}" \
  '.number == $number and .pull_request == null and (.labels | type == "array")' >/dev/null 2>&1 \
  || die "Approved issue binding invalid."
if ! printf '%s' "${ISSUE}" | jq -e --arg label "squad:${AGENT}" \
  '.state == "open" and any(.labels[]; .name == $label)' >/dev/null 2>&1; then
  log "Approved issue is closed or lacks its configured agent label; no work."
  exit 0
fi
if printf '%s' "${ISSUE}" | jq -e \
  'any(.labels[]; .name == "squad:processing" or .name == "squad:queued" or .name == "squad:revising" or .name == "squad:attempted")' >/dev/null; then
  log "Approved issue already claimed; no duplicate."
  exit 0
fi
BRANCH="squad/${AGENT}/issue-${NUMBER}"
REFS=$(github_request GET "${API}/git/matching-refs/heads/${BRANCH}" "${TOKEN}") \
  || die "Issue branch dedup read failed."
printf '%s' "${REFS}" | jq -e 'type == "array"' >/dev/null 2>&1 || die "Branch dedup response invalid."
if printf '%s' "${REFS}" | jq -e --arg ref "refs/heads/${BRANCH}" 'any(.[]; .ref == $ref)' >/dev/null; then
  log "Approved issue branch already exists; no duplicate."
  exit 0
fi
PRS=$(github_request GET "${API}/pulls?state=all&head=${SQUAD_TARGET_REPO%/*}:${BRANCH}&per_page=100" "${TOKEN}") \
  || die "Issue PR dedup read failed."
printf '%s' "${PRS}" | jq -e 'type == "array"' >/dev/null 2>&1 || die "PR dedup response invalid."
if printf '%s' "${PRS}" | jq -e 'length > 0' >/dev/null; then
  log "Approved issue PR already exists; no duplicate."
  exit 0
fi

# One scheduled replica, a 60s job timeout and a five-minute schedule avoid
# normal overlap. A nonempty queue defers this single approved issue; no purge.
PENDING=$(az storage message peek --account-name "${AZURE_STORAGE_ACCOUNT}" --queue-name "${QUEUE_NAME}" \
  --auth-mode login --num-messages 1 --timeout 8 -o json 2>/dev/null) || die "Queue dedup read failed."
printf '%s' "${PENDING}" | jq -e 'type == "array"' >/dev/null 2>&1 || die "Queue dedup response invalid."
if [[ "${PENDING}" != "[]" ]] && printf '%s' "${PENDING}" | jq -e 'length > 0' >/dev/null; then
  log "Queue already has work; this poll is deferred."
  exit 0
fi
MESSAGE=$(jq -cn --arg repo "${SQUAD_TARGET_REPO}" --arg agent "${AGENT}" --argjson number "${NUMBER}" \
  '{type:"new",source:"owned-poller",repo:$repo,agent_type:$agent,issue_number:$number}')
CONTENT=$(printf '%s' "${MESSAGE}" | base64 | tr -d '\n')
MESSAGE_ID=$(az storage message put --account-name "${AZURE_STORAGE_ACCOUNT}" --queue-name "${QUEUE_NAME}" \
  --auth-mode login --content "${CONTENT}" --time-to-live 600 --visibility-timeout 10 --timeout 8 \
  --query id -o tsv 2>/dev/null) || die "Queue acceptance failed or uncertain; no processing label written."
[[ "${MESSAGE_ID}" =~ ^[A-Za-z0-9-]+$ ]] \
  || die "Queue acceptance receipt missing or invalid; no processing label written."
# Labels follow durable queue acceptance. The worker can claim this explicitly
# bound poller message if it wins this cross-service race or this POST fails.
github_request POST "${API}/issues/${NUMBER}/labels" "${TOKEN}" '{"labels":["squad:processing"]}' >/dev/null \
  || die "Message accepted but label acknowledgement failed; worker owns bounded recovery."
unset TOKEN ISSUE
log "Approved issue #${NUMBER} accepted as queue message ${MESSAGE_ID}; processing label recorded."
