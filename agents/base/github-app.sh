#!/usr/bin/env bash

# Source only in a non-tracing entrypoint. Credential-bearing HTTP headers travel
# on curl's stdin, not in process arguments, files, ARM properties or logs.
github_request() {
  local method="$1" url="$2" credential="$3" body="${4:-}"
  {
    printf 'header = "Authorization: Bearer %s"\n' "${credential}"
    printf 'header = "Accept: application/vnd.github+json"\n'
    printf 'header = "X-GitHub-Api-Version: 2022-11-28"\n'
  } | curl --silent --fail --connect-timeout 15 --max-time 45 \
      --config - --request "${method}" --url "${url}" \
      --data "${body}" 2>/dev/null
}

github_app_token() {
  local repo="$1" permission="${2:-}" pem now header payload signature jwt response request
  [[ "${repo}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || return 1
  [[ "${GITHUB_APP_ID:-}" =~ ^[0-9]+$ && "${GITHUB_APP_INSTALLATION_ID:-}" =~ ^[0-9]+$ ]] || return 1
  pem=$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" \
    --name "${KEY_VAULT_SECRET_NAME}" --query value -o tsv 2>/dev/null) || return 1
  [[ -n "${pem}" ]] || return 1
  now=$(date +%s)
  header=$(printf '%s' '{"alg":"RS256","typ":"JWT"}' | openssl base64 -e -A | tr '+/' '-_' | tr -d '=')
  payload=$(jq -cn --arg iss "${GITHUB_APP_ID}" --argjson now "${now}" \
    '{iat: ($now - 60), exp: ($now + 540), iss: $iss}' \
    | openssl base64 -e -A | tr '+/' '-_' | tr -d '=')
  signature=$(printf '%s' "${header}.${payload}" | openssl dgst -sha256 -sign <(printf '%s\n' "${pem}") \
    | openssl base64 -e -A | tr '+/' '-_' | tr -d '=') || return 1
  jwt="${header}.${payload}.${signature}"
  request=$(jq -cn --arg repo "${repo#*/}" --arg permission "${permission}" \
    '{repositories: [$repo]} + (if $permission == "runner" then {permissions: {administration: "write"}} else {} end)')
  response=$(github_request POST \
    "https://api.github.com/app/installations/${GITHUB_APP_INSTALLATION_ID}/access_tokens" \
    "${jwt}" "${request}") || return 1
  unset pem jwt signature
  printf '%s' "${response}" | jq -er '.token | select(type == "string" and length > 0)' 2>/dev/null
}

github_registration_token() {
  local repo="$1" installation_token="$2" response token expires
  response=$(github_request POST "https://api.github.com/repos/${repo}/actions/runners/registration-token" \
    "${installation_token}") || return 1
  token=$(printf '%s' "${response}" | jq -er '.token | select(type == "string" and length > 0)' 2>/dev/null) || return 1
  expires=$(printf '%s' "${response}" | jq -er '.expires_at' 2>/dev/null) || return 1
  expires=$(date -d "${expires}" +%s 2>/dev/null) || return 1
  (( expires > $(date +%s) + 60 )) || return 1
  printf '%s' "${token}"
}
