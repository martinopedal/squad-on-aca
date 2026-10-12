# Owned hosted Squad-on-ACA scheduled-poller preparation

## Status

Ready for Validation (source/local readiness; real deployment BLOCKED).
The delegated overnight decision approves source preparation that replaces
the broken owned self-hosted enqueue-runner dependency with private scheduled
issue polling. It does not approve an apply, new IAM/network resources or image
publication. The existing workspace plan remains the validation source of truth.

## Source and ownership

- Owned fork: `martinopedal/squad-on-aca`; focused PR1, existing repair branch.
- Upstream: `haflidif/squad-on-aca`; original MIT copyright retained unchanged.
- Initial checkpoint: `b82c285298592909d4b5f7fb9c196ccafc3c2850`.
- Mode MODIFY; preserve upstream Bash/container, Terraform/Bicep recipes and
  Jobs API `2025-01-01`. No azd initialization or provider migration.
- Only the owned fork and accepted owned target/runtime are in scope.
- Original source/runtime, working AKS, shared networks, VM and attached disk
  stay untouched. Upstream push is disabled in this independent clone.

## Approved architecture and required outcome

```text
sole approved owned squad:ripley issue
 -> private scheduled ACA poller (existing broken runner Job ID candidate)
 -> existing MI-authenticated Storage Queue
 -> existing KEDA event worker (min0/max1)
 -> genuine target Squad1.0.1 using pinned Copilot CLI1.0.96
 -> numeric success, actual README-only diff and configured App bot PR
```

- Poller: existing MI -> existing Key Vault App PEM in process memory -> short
  App JWT -> target-scoped installation token requesting only Issues:write,
  Contents:read and Pull requests:read. No App Administration permission,
  runner/JIT credential, Copilot credential read or new IAM.
- Configure exactly one target/issue/agent and an accepted UTC cutoff.
  Closed/wrong label, processing/attempted/queued, branch/PR and busy-queue
  dedup all precede enqueue. Read denials fail closed.
- Queue contains only bound metadata, TTL600 and visibility delay10.
  Processing label is written only after accepted queue put.
- The worker handles the accepted-message/label race for only that configured
  poller issue, records `squad:attempted`, and cannot silently rerun duplicate
  sequential messages after native failure. No fallback PR.
- The genuine target setup PR8 was normally merged after independent review;
  its real Squad profile/team/Ripley/checker are preserved.
- Existing target enqueue workflow must be normally retired after source
  acceptance. The owned old queued zero-step run is canceled only by exact ID
  after requalification; no issue close, queue purge or duplicate smoke.
- Both jobs use one accepted immutable image. Poller has 0.25vCPU/0.5Gi,
  50s process deadline, 60s replica timeout, retries0 and five-minute UTC cron.
  Worker has 1vCPU/2Gi, timeout600, retries0 and max1/min0.
- Explicit IaC ordering updates the worker before enabling the poller.
  Supplied tags and workload profile are preserved. No new estate resources.

## Read-only qualification and unresolved ownership

- Existing UAMI metadata has Message Sender (queue add), Data Reader (peek),
  Message Processor (get/delete), Key Vault Secrets User and AcrPull/AcrPush at
  their existing resource scopes. No new role is requested.
- Actual role-definition dataActions confirm queue add and read.
- Existing poller candidate is the broken manual owned runner Job, user-created
  and untagged; worker is event-driven with its existing ownership tags.
  Both use the same existing private environment/UAMI and Consumption profile.
- These metadata facts do not prove no Terraform owner. State/baseline ownership
  remains BLOCKED; no state is read, imported, rewritten or bypassed.
- Group deployment metadata contains only historical failed policy deployments;
  absence of a successful ARM deployment is not proof of no Terraform ownership.
- Private exact bindings/evidence are in the operator receipt, not public inputs.

## Build and publisher choice

- Installed Windows Docker daemon is absent; no host service/features changed.
- Approved source CI builds the actual shared worker/poller image on Ubuntu,
  credential-free, using explicit public versions of the recipe's Go/Debian
  base images. It checks real tooling and both installed entrypoints; no push.
- The owned ACR is Premium/private, public network disabled, admin disabled and
  trusted Azure services bypass configured. Public GitHub runner connectivity
  is not qualified by AcrPush alone.
- Read-only ACR task/agent-pool lists are both empty. No new standing pool,
  network access, registry admin key or IAM grant is allowed.
- Current publisher choice is therefore **credential-free CI build; private
  publication unqualified**. Existing private runner or owner-authenticated
  transient trusted ACR build authority/reachability must be accepted before
  publication. An optional private publisher workflow is not proof of a route.
- Images remain immutable digest references; publishing never updates jobs.

## Cost, lifecycle and scope

- Reuse environment, queue, Key Vault, identity, registry and exact two Jobs.
- No new Azure workload or image push occurs in preparation.
- Parent's tenant cap is USD2,500 through October15; conservative estimate2226
  leaves approximately USD273, not an accepted deployment reservation.
- One admitted 60s poller plus 600s worker conservatively totals615 vCPU-seconds
  and1,230 GiB-seconds. Count image build/storage/logs and every cron tick too.
- Cutoff prevents GitHub/queue activity, not all scheduled billing. A reviewed
  IaC retirement of the schedule is mandatory at the accepted window's end.
- Live supervision maximum600s; stop only exact newly recorded executions,
  not all jobs. No standing builder or duplicate poller is permitted.
- If state ownership forbids repurposing, separately qualify a minimal
  alternative graph and cost before proposing any resource creation.

## Preparation checklist

- [x] Existing plan, scope and upstream/license preservation.
- [x] Poller implementation with narrow existing App permissions.
- [x] Handoff/dedup/negative tests; existing fail-closed worker tests retained.
- [x] Focused existing-job Schedule/Event Bicep and source graph.
- [x] Credential-free Linux container build and entry smoke configured in CI.
- [x] Queue role metadata and publisher/ownership read-only checks.
- [x] Owned target workflow retirement template; no target mutation yet.
- [ ] Parent independently accept exact PR1 source and normally promote.
- [ ] Accept private publication route and immutable image digest.
- [ ] Accept exact state/baseline, cost, policy and deployment qualification.
- [ ] Normally retire target workflow and cancel only its old queued run.
- [ ] Complete azure-validate before accepted azure-deploy.
- [ ] Capture genuine hosted issue -> poller -> worker -> README PR receipt.

## Functional verification and Section7: Validation Proof

- Executable synthetic App/queue/native fixtures use real local Git; protected
  values and full issue payloads cannot appear in logs or queue messages.
- Positive poller metadata/queue-before-label and worker label-race recovery
  contracts are tested, alongside expiry, permission failures, existing work,
  uncertain queue acceptance, invalid scope and duplicate-attempt rejection.
- All previous genuine-work/native failure/README/secret/revision contracts stay.
- Bicep compilation and compiled payload assertions verify Schedule60/Event600,
  zero retries, identity scaler, min0/max1 and preserved workload-profile input.
- Source CI container job builds actual image/tooling and both entrypoints
  without a credential or private input. Exact results are in private receipt.
- UI not applicable. Local mocked/CI builds do not prove live MI secret access,
  Copilot entitlement, private ACR publishing or Azure deployment acceptance.

## All validation checks pass

- [x] Local source syntax/tests/compiled Bicep contract.
- [ ] Accepted container build and immutable private publication receipt.
- [ ] Core CLI/auth/service validate/what-if for exact private scope.
- [ ] Azure policy validation and actual budget reservation.
- [ ] Existing-state ownership and complete baseline preservation.
- [ ] Live MI App/queue and Copilot entitlement qualification inside accepted Jobs.
- [ ] Actual genuine hosted execution/PR proof and exact cleanup.

No App permission approval is a prerequisite for this architecture. No plan is
marked Validated while any real gate is missing; no deploy skill/apply occurs.
