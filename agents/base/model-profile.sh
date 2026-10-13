#!/usr/bin/env bash
set -euo pipefail
die() { exit 1; }
source /runtime-contract.sh
require_native_squad
if [[ -f scripts/check-hosted-squad-setup.mjs ]]; then
  node scripts/check-hosted-squad-setup.mjs >/dev/null 2>&1 \
    || die "Target native Squad setup validation failed."
fi
