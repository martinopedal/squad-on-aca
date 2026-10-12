#!/usr/bin/env bash
set +x
set -euo pipefail

log() { printf '%s\n' "$*"; }
die() { log "FATAL: $*"; exit 1; }
source "$(dirname "${BASH_SOURCE[0]}")/github-app.sh"

[[ -z "${RUNNER_TOKEN:-}" ]] || die "Persisted RUNNER_TOKEN is unsupported; remove it from the job template."
for name in GITHUB_REPO GITHUB_APP_ID GITHUB_APP_INSTALLATION_ID KEY_VAULT_NAME KEY_VAULT_SECRET_NAME AZURE_CLIENT_ID; do
  [[ -n "${!name:-}" ]] || die "Required public setting ${name} missing."
done
[[ "${GITHUB_REPO}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "Invalid target repository."
[[ "${RUNNER_NAME:-squad-aca}-${HOSTNAME:-job}" =~ ^[A-Za-z0-9_.-]+$ ]] || die "Invalid runner name."

az login --identity --client-id "${AZURE_CLIENT_ID}" --allow-no-subscriptions -o none >/dev/null 2>&1 \
  || die "Managed Identity login failed."
APP_TOKEN=$(github_app_token "${GITHUB_REPO}" runner) \
  || die "App startup mint failed; verify target installation and Administration:write approval. No runner registered."
ACTIONS_RUNNER_INPUT_TOKEN=$(github_registration_token "${GITHUB_REPO}" "${APP_TOKEN}") \
  || die "Fresh repo registration denied or expired; no runner registered."
unset APP_TOKEN
export ACTIONS_RUNNER_INPUT_TOKEN

cd "${SQUAD_RUNNER_DIRECTORY:-/runner}"
./config.sh --unattended --ephemeral --disableupdate \
  --url "https://github.com/${GITHUB_REPO}" \
  --name "${RUNNER_NAME:-squad-aca}-${HOSTNAME:-job}" \
  --labels "${LABELS:-squad-on-aca-demo}" --work _work >/dev/null 2>&1 \
  || die "Runner registration failed."
unset ACTIONS_RUNNER_INPUT_TOKEN
log "Fresh ephemeral target runner registered."
# The owning ACA execution also has a 600-second replica timeout and zero retries.
exec timeout --signal=TERM --kill-after=10s 570s ./run.sh
