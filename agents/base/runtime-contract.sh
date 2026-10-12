#!/usr/bin/env bash

require_native_squad() {
  [[ -s .github/agents/squad.agent.md && -s .squad/team.md ]] \
    || die "Native Squad profile/team missing from checked-out target; no fallback PR."
  grep -Eq '^name: ["'\'']?Squad["'\'']?[[:space:]]*$' .github/agents/squad.agent.md \
    || die "Target custom agent must declare name: Squad."
  # A genuine profile can be case-sensitive even on a case-insensitive host.
  git ls-files --error-unmatch .github/agents/squad.agent.md .squad/team.md >/dev/null 2>&1 \
    || die "Native Squad profile/team must be tracked."
  if [[ -f scripts/check-hosted-squad-setup.mjs ]]; then
    node scripts/check-hosted-squad-setup.mjs >/dev/null 2>&1 \
      || die "Target native Squad setup validation failed."
  fi
}

run_squad() {
  local prompt="$1" result=0
  require_native_squad
  # Never stream or publish raw model/tool output: it can contain credentials or
  # hostile issue data. The parent process keeps the App token out of Copilot.
  env -u GH_TOKEN -u GITHUB_TOKEN COPILOT_GITHUB_TOKEN="${COPILOT_TOKEN}" \
    timeout --signal=TERM --kill-after=10s "${SQUAD_TIMEOUT_SECONDS:-480}s" \
    copilot --yolo --agent Squad --no-auto-update --no-remote-export \
      --log-level none --secret-env-vars=COPILOT_GITHUB_TOKEN,IDENTITY_HEADER,MSI_SECRET \
      --deny-tool='shell(az:*)' --deny-tool='shell(gh:*)' \
      --deny-tool='shell(curl:*)' --deny-tool='shell(wget:*)' \
      --deny-tool='shell(git push:*)' -p "${prompt}" >/dev/null 2>&1 || result=$?
  log "Native Squad result: exit=${result}"
  (( result == 0 )) || die "Native Squad failed (exit=${result}); no push or PR."
}

require_genuine_changes() {
  local base="$1" changes diff secret
  git diff --no-ext-diff --no-textconv --quiet "${base}" HEAD \
    && die "Native Squad produced no changed files; no fallback PR."
  changes=$(git diff --no-ext-diff --no-textconv --name-only "${base}" HEAD)
  diff=$(git diff --no-ext-diff --no-textconv --no-color "${base}" HEAD)
  for secret in "${GITHUB_TOKEN:-}" "${GH_TOKEN:-}" "${COPILOT_TOKEN:-}"; do
    if [[ -n "${secret}" && "${diff}" == *"${secret}"* ]]; then
      die "Credential content detected in agent diff; no push or PR."
    fi
  done
  if printf '%s' "${diff}" | grep -Eq -- '-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'; then
    die "Credential pattern detected in agent diff; no push or PR."
  fi
  if [[ "${SQUAD_README_ONLY:-false}" == "true" ]]; then
    [[ "${changes}" == "README.md" ]] \
      || die "README-only scope violated; no push or PR."
    [[ -f README.md && ! -L README.md ]] || die "README must remain a regular file."
    [[ "$(git diff --no-ext-diff --no-textconv --numstat "${base}" HEAD -- README.md)" != $'-\t-'* ]] \
      || die "README must remain text, not a binary artifact."
    git diff --no-ext-diff --no-textconv --quiet "${base}" HEAD -- README.md \
      && die "README unchanged; no push or PR."
  else
    printf '%s\n' "${changes}" | grep -qvE '^(\.squad/|\.squad-work/)' \
      || die "Only agent state/artifacts changed; no genuine work PR."
  fi
  return 0
}
