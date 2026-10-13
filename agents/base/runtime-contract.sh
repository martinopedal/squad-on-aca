#!/usr/bin/env bash

require_native_squad() {
  [[ -s .github/agents/squad.agent.md && -s .squad/team.md ]] \
    || die "Native Squad profile/team missing from checked-out target; no fallback PR."
  grep -Eq '^name: ["'\'']?Squad["'\'']?[[:space:]]*$' .github/agents/squad.agent.md \
    || die "Target custom agent must declare name: Squad."
  # A genuine profile can be case-sensitive even on a case-insensitive host.
  git ls-files --error-unmatch .github/agents/squad.agent.md .squad/team.md >/dev/null 2>&1 \
    || die "Native Squad profile/team must be tracked."
}

run_squad() {
  local prompt="$1" result=0
  # No credential in argv or inherited controller environment. The protected
  # launcher constructs the CLI-only environment and drops UID/groups/caps.
  printf '%s\n%s' "${COPILOT_TOKEN}" "${prompt}" \
    | env -i PATH="${PATH}" python3 -I "${MODEL_HELPER}" run \
      "${WORKSPACE}/repo" "${MODEL_HOME}" "${SQUAD_TIMEOUT_SECONDS:-480}" \
      >/dev/null 2>&1 || result=$?
  log "Native Squad result: exit=${result}"
  (( result == 0 )) || die "Native Squad failed (exit=${result}); no push or PR."
}

trusted_git() {
  env -i PATH="${PATH}" HOME="${TRUSTED_HOME}" GH_CONFIG_DIR="${TRUSTED_HOME}/gh" \
    GH_TOKEN="${GITHUB_TOKEN}" GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 LC_ALL=C \
    git -c core.hooksPath=/dev/null -c core.autocrlf=false \
      -c commit.gpgsign=false -c tag.gpgsign=false -c credential.helper= \
      -c 'credential.helper=!gh auth git-credential' "$@"
}

require_issue_approval() {
  ISSUE_STATUS=$(gh issue view "${ISSUE_NUMBER}" --repo "${GITHUB_REPO}" --json state,labels) \
    || die "Current issue approval read failed."
  printf '%s' "${ISSUE_STATUS}" | jq -e --arg approved_label "squad:${AGENT_TYPE}" \
    '.state == "OPEN" and any(.labels[]; .name == $approved_label)' >/dev/null \
    || die "Issue closed or approved agent label withdrawn; no execution/publication."
  LABELS=$(printf '%s' "${ISSUE_STATUS}" | jq -r '.labels[].name')
}

require_revision_binding() {
  local binding
  binding=$(gh pr view "${PR_NUMBER}" --repo "${GITHUB_REPO}" \
    --json state,headRefName,headRefOid,baseRefName,isCrossRepository,author) \
    || die "Revision PR binding read failed."
  printf '%s' "${binding}" | jq -e --arg branch "${BRANCH}" --arg head "${HEAD_SHA}" \
    --arg bot "${BOT_LOGIN}" --arg base "${BASE_BRANCH:-}" \
    '.state == "OPEN" and .isCrossRepository == false and .headRefName == $branch
     and .headRefOid == $head and .author.login == $bot
     and ($base == "" or .baseRefName == $base)' >/dev/null \
    || die "Revision head moved or PR is not the known trusted task context."
}

publication_python() {
  (cd "${TRUSTED_HOME}" && env -i PATH="${PATH}" HOME="${TRUSTED_HOME}" \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 \
    GIT_TERMINAL_PROMPT=0 LC_ALL=C GITHUB_TOKEN="${GITHUB_TOKEN}" COPILOT_TOKEN="${COPILOT_TOKEN}" \
    python3 -I "${PUBLICATION_HELPER}" "$@")
}

prepare_readme_publication() {
  # Never inspect or push the model's Git directory. Fetch only the qualified
  # target ancestry into a fresh repository, then import validated file bytes.
  PUBLISHER="${WORKSPACE}/publisher-${RANDOM}-${RANDOM}"
  (umask 077; mkdir "${PUBLISHER}") || die "Controlled publisher directory unavailable."
  trusted_git -C "${PUBLISHER}" init --quiet --template= \
    || die "Controlled publisher initialization failed."
  trusted_git -C "${PUBLISHER}" fetch --quiet --no-tags "${PUBLISH_REMOTE}" \
    "refs/heads/${BASE_BRANCH}:refs/remotes/trusted/main" \
    || die "Qualified main fetch failed."
  [[ "$(trusted_git -C "${PUBLISHER}" rev-parse refs/remotes/trusted/main)" == "${EXPECTED_BASE}" ]] \
    || die "Qualified main moved; require a fresh execution."
  if [[ "${MSG_TYPE}" == "revise" ]]; then
    trusted_git -C "${PUBLISHER}" fetch --quiet --no-tags "${PUBLISH_REMOTE}" \
      "refs/heads/${BRANCH}:refs/remotes/trusted/previous" \
      || die "Previous wrapper publication fetch failed."
    [[ "$(trusted_git -C "${PUBLISHER}" rev-parse refs/remotes/trusted/previous)" == "${BEFORE}" ]] \
      || die "Revision head moved; no publication."
  fi
  PUBLISHED_HEAD=$(publication_python build "${PUBLISHER}" "${WORKSPACE}/repo" \
      "${EXPECTED_BASE}" "${BEFORE}" "${BOT_LOGIN}" \
      "${BOT_USER_ID}+${BOT_LOGIN}@users.noreply.github.com") \
    || die "Trusted README publication validation failed; no push or PR."
  [[ "${PUBLISHED_HEAD}" =~ ^[0-9a-f]{40}$ ]] || die "Invalid trusted publication receipt."
}
