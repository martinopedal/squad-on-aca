# Owned hosted runtime repair

This MIT fork credits [@haflidif](https://github.com/haflidif) and retains the
upstream copyright and license. The original service is not a deployment target.
These changes concern an independently owned Apps/Jobs demo, not native ACA
Sandboxes. Source tests are not an end-to-end hosted success receipt.

## One pipeline, two jobs

The existing target issue workflow waits for a private-network self-hosted
enqueue runner. That manual ACA Job must register before the workflow can put
the issue on the queue. KEDA then starts the separate Squad agent Job.

The runner image extends a qualified agent image. On each startup it uses its
existing UAMI to read the existing App PEM inside the container, signs a short
JWT, requests an installation token scoped to the target repository and
`administration:write`, and immediately obtains a fresh repository registration
token. A stored `RUNNER_TOKEN` is explicitly rejected. Secrets never enter IaC,
ARM environment values, public build arguments or curl process arguments.
The standard runner reads the token via `ACTIONS_RUNNER_INPUT_TOKEN`, which is
unset immediately after configuration; its standard ephemeral runtime
credentials are confined to the execution filesystem.

**GitHub gate:** repo runner registration requires the installed App's
Administration: write permission. Contents/Issues/Pull requests permissions do
not imply it. The owned demo App's public metadata currently lacks this
permission. The App owner must approve the permission and installation update
through GitHub's normal settings/approval flow. The code cannot grant it and
fails closed on denial. No presenter PAT or host OAuth is substituted.
An alternative queue transport would need a separately accepted private-network
design; changing the target to a public runner does not solve private reachability.

The agent uses the same protected startup pattern but does not request runner
Administration permission. Copilot gets only its existing licensed credential
through `COPILOT_GITHUB_TOKEN`; App tokens are removed from its environment.
The verified CLI 1.0.96 is pinned and automatic updates are disabled. Its native
secret-environment control strips the Copilot credential and MI header secrets
from shell/MCP child environments and redacts their output. CLI logging and
remote session export are disabled; direct Azure/GitHub/curl/wget/push tool
calls are denied. The publication guard also rejects known runtime credentials
and common token/PEM patterns in the complete diff. Repository Git hooks and
external diff drivers are disabled in the trusted wrapper.
The clone is the current target default branch, and native `Squad` runs from
that working directory with `-p`, not interactive piped input. The real tracked
`.github/agents/squad.agent.md` and `.squad/team.md` must exist; if the target's
native setup checker exists, it must pass. The wrapper never synthesizes profiles.

Every native call has a numeric exit receipt and a deadline. Nonzero exits
(including missing-agent errors), empty diffs and state/artifact-only diffs
cannot push or create a PR. README smoke mode additionally requires the whole
PR diff to contain exactly changed `README.md`. Issue/review JSON is task data,
not permission to read secrets, publish, merge or deploy. Raw model/tool output
is discarded rather than copied into PRs, logs or fallback artifacts.
The wrapper still uses powerful CLI tools; these boundaries are not an OS-level
sandbox and do not replace trusted repository instructions and private egress policy.

Queue acknowledgement retains upstream's one-attempt semantics. Failed work
requires an explicit operator retry after repair; it is not automatic success.
New and revision flows retain dedup, current-head checks and lifecycle labels.

## Build and source verification

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests use synthetic local fixtures and mocked Azure/GitHub/Copilot commands;
they do not read secrets or create resources. CI runs the same tests on Linux.

Build the existing base context, then the runner context with an immutable
`SQUAD_AGENT_IMAGE` digest. Supply the exact runner release version and verified
Linux x64 SHA256 from
[the official runner release](https://github.com/actions/runner/releases).
The defaults pin 2.338.0 and its official SHA256; requalify any version override.
An explicitly empty checksum fails the build; do not use an unverified checksum.
The existing base-image cache host is a build argument; never use the original
author's registry as a fallback for this fork. Pass the owned existing registry
host explicitly. Build labels credit upstream while identifying this fork.
No host Docker daemon is installed or started by this change.

## Focused existing-runtime IaC

`infra/bicep/owned-runtime.bicep` is a focused **existing-job repair** envelope
using the upstream Jobs API version. It reuses environment, registry, identity,
queue and Key Vault by public metadata, without creating network/IAM/storage
resources. It changes only the two accepted owned job definitions. It is not a
replacement for the upstream Terraform or azd deployment recipe, and must not
be used to take over a Terraform-managed resource without an accepted state
ownership decision. Existing Terraform addresses/providers are unchanged.

Before using it, independent review must accept **all** of these gates:

1. Both exact jobs already exist in the accepted owned resource group; names,
   location, tags, environment, container resources, workload profile, identity,
   registry and scaler metadata match the reviewed baseline. If the baseline has
   secret references, sidecars or additional properties absent from this envelope,
   stop and extend it through review; do not erase them.
2. State/IaC ownership is accepted. The envelope is not permission for a second
   writer or a generic deployment into a new resource group.
3. Target native setup source is independently approved and normally merged.
   Preserve the existing issue and queued workflow; do not create another smoke.
4. App installation scope, owner-approved Administration permission, existing
   MI secret reads, Copilot entitlement and private egress are qualified.
   Caller Key Vault denial does not establish failure of the job's MI.
5. Both images are accepted immutable `@sha256:` references in the existing
   owned ACR. Source CI/image publishing needs its own approved identity, trust
   and AcrPush authorization; inherited original OIDC settings cannot be used.
6. The plan permits only the two exact job updates: runner timeout 600s and no
   retries; agent max=1/min=0/timeout=600s/no retries. No new environment/network,
   secrets, roles, subscriptions or broad access changes.
7. `azure-validate` completes; parent accepts source and exact deployment
   qualification before `azure-deploy`. No imperative image/template/secret edits.

Bicep resources can create a missing resource; the explicit existence/what-if
gate is mandatory. This source envelope alone does not prove Azure acceptance
or authorize an apply. The tracked preparation plan contains only public scope;
actual existing bindings belong in private operator evidence.

## Bounded live receipt, after all gates

Use the sole existing README smoke issue and queued workflow. Record:
issue URL → original workflow/run and runner registration → enqueue step →
queue receipt → exact new agent execution → numeric native result → bot PR
with an actual README diff and commit. Verify bot identity and issue linkage.
No empty/state-only/fallback PR is acceptable.

At most one runner execution and one agent execution are admitted for one smoke.
At 1 vCPU/2Gi for at most 600s each, the workload ceiling is 1,200 vCPU-seconds
and 2,400 GiB-seconds, excluding image build/storage/log ingestion. Obtain the
accepted regional rate/cost reservation before launching; this is not a price
quote. Shared ACR and Key Vault are reused, not free or duplicated.
Stop only the exact newly recorded execution IDs in `finally` at the 600-second
supervision deadline, even if GitHub is still queued. Do not stop all jobs.

**Current status:** source readiness only. Target native setup PR8 was normally
merged after independent review; the target's real Squad profile is now on main.
Owned runtime source approval, App permission approval, immutable image build, existing-resource/state ownership review,
Azure deployment acceptance and a genuine hosted PR receipt remain required.
