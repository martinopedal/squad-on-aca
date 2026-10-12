# Owned hosted Squad-on-ACA fork preparation

## Status

Ready for Validation (source/local readiness only; live deployment BLOCKED).
Scope-approved preparation. The user explicitly requested an owned fork of
Haflidi's original, repairs necessary for a working hosted Apps/Jobs demo, retained
attribution, and autonomous implementation decisions overnight. Exact deployment
source, resource plan, cost and execution qualification are not yet accepted.

## Source and ownership

- Owned fork: `martinopedal/squad-on-aca`.
- Upstream: `haflidif/squad-on-aca`, MIT license retained.
- Initial fork checkpoint: `b82c285298592909d4b5f7fb9c196ccafc3c2850`.
- Modify only the owned fork and explicitly qualified owned target/runtime.
- Leave Haflidi's original implementation, working AKS, shared Corp resources,
  the presenter VM and its currently attached disk untouched. Only the two
  exact broken owned-clone jobs may be updated after separate source/scope gates.

## Required outcome

One actual hosted issue -> enqueue -> ACA Job -> genuine Squad work -> reviewed
README-only bot PR trace, with repository/runtime/identity bindings, numeric
results and cleanup. This is distinct from the accepted native ACA Sandboxes
host-to-microVM flow.

## Constraints

- Preserve existing legitimate App/managed-identity authority; no credential copy,
  plaintext registration tokens in logs/state/ARM metadata, broad permissions or
  fabricated fallback PR success.
- Durable Azure changes use reviewed IaC and exact validation/plan gates.
- Use the approved Online primary placement for eligible components, or preserve
  an existing owned runtime where its required private placement is qualified.
- Total tenant budget remains USD2,500 through October 15; current conservative
  queue estimate has limited headroom and must account for any new deployment.
- Real required human/GitHub gates remain. No impersonation or admin bypass.
- Morning reporting is requested; routine overnight Teams messages are paused.

## Preparation checklist

- [x] Verify owned fork, upstream parent, license and initial checkpoint.
- [x] Inspect existing application, infrastructure and authentication contracts.
- [x] Identify owned-source fixes for agent discovery, result semantics and registration.
- [x] Implement protected fresh startup minting with offline denial/expiry tests.
- [x] Define bounded existing two-job scope without duplicate infrastructure.
- [x] Implement source/tests, attribution and explicit owned image publishing gates.
- [ ] Independently accept source and promote through normal GitHub gates.
- [x] Complete local mocked functional verification and mark Ready for Validation.
- [ ] Invoke azure-validate, then azure-deploy only after accepted qualifications.
- [ ] Capture actual hosted end-to-end results; preserve original upstream.

## Architecture decisions

- Mode: MODIFY, preserving upstream Terraform/Bicep recipes and Jobs API
  `2025-01-01`; no azd init, provider migration or changes to upstream resources.
- Existing queue receives target workflow output; the manual private enqueue
  runner and event-driven Squad agent are distinct ACA Jobs.
- Registration is minted inside every runner startup via existing MI -> existing
  Key Vault PEM -> short App JWT -> target-scoped App installation token ->
  fresh repo registration token. No protected value is an ARM/IaC parameter.
- Existing demo App public metadata lacks Administration:write. Owner-approved
  App and installation permission update is a hard gate, not a code workaround.
- Target native setup PR8 was independently reviewed and normally merged. The
  target's current main contains the real Squad profile and setup checker.
- CLI 1.0.96 is pinned; noninteractive `--agent Squad -p` runs inside the clone,
  with secret environment protection, no raw logs/export and direct auth/push
  tool denials. Failed/empty/state-only/out-of-scope work cannot open a PR.
- Smoke publication requires actual README-only changed-file work and rejects
  runtime credentials/token/PEM patterns. No fallback artifact is generated.
- `infra/bicep/owned-runtime.bicep` is a proposed two-existing-job repair envelope,
  not a new platform deployment. Its baseline/state ownership and exact what-if
  must be independently accepted; any additional baseline properties block use.
- Terraform source, addresses and provider constraints are unchanged. This
  focused Bicep envelope must not become an unaccepted second Terraform writer.
- Owned publisher workflow is manual, main-only and fails closed without owned
  OIDC/ACR variables. It builds immutable digests but never updates runtime jobs.
  Original-author ACR/OIDC defaults are removed from fork build automation.

## Placement, scope and cost

- Candidate: reuse existing owned private Corp environment, ACR, queue, MI,
  Key Vault and exact existing runner/agent jobs. No new Azure resources,
  network changes, IAM grants, secrets or subscription transfers.
- Exact private bindings remain in private operator evidence. Parent must
  accept placement and resource/state ownership; this public plan is not GO.
- One admitted smoke: at most one runner execution and one agent execution,
  600-second overall supervision, zero retries, agent max=1/min=0.
- Conservative workload ceiling: 1,200 vCPU-seconds and 2,400 GiB-seconds at
  1 vCPU/2Gi each, plus separately counted ACR build/storage/log costs.
- No new workload incurred during preparation. No price/cost reservation is
  claimed. Parent must reserve incremental cost under the USD2,500 tenant cap.
- Stop only exact newly recorded execution IDs in finally, never all executions.

## Functional verification

- Backend: executable offline Azure/GitHub/Copilot mocks exercise the production
  entrypoint and fresh runner bootstrap, including real local Git README diffs.
- Negative contracts: expired/static token, missing App admin, registration
  denial, absent profile, missing native agent, nonzero-with-diff, empty work,
  out-of-scope file changes, secret content, stale revision and deadline.
- UI: not applicable.
- Bicep: local compiler 0.47.16 compiles the focused envelope without diagnostics.
- Docker: installed client cannot connect to an existing Linux daemon; no daemon
  installed/started, no image built, no immutable runtime image qualified yet.
- Tests prove source contracts only; they do not prove MI secret access,
  GitHub permissions, Copilot entitlement or a real hosted execution.

## Deployment holds and next gate

1. Parent independent owned-fork source review and normal source promotion.
2. Owner-approved App Administration permission/installation update.
3. Exact existing-job baseline/state ownership and accepted cost reservation.
4. Qualified owned publisher authority, accepted immutable images and regional
   service validation/what-if.
5. azure-validate and parent deployment acceptance before azure-deploy.
6. Reuse sole target issue7/queued workflow, capture genuine bot README PR;
   preserve original source and all unrelated runtime resources.

## All validation checks pass

- [x] Local source compilation and offline contract verification.
- [ ] Core validation (CLI, auth, build, service validate, what-if) using the
  azure-validate helper with the focused Bicep template and exact private
  parameters; BLOCKED by unaccepted images/state ownership/source/scope.
- [ ] Optional lint: compiler diagnostics checked locally; configured broader
  estate linting is not changed or represented as validated.
- [ ] Azure Policy Validation for the exact accepted subscription/resource group.
- [ ] Container image build, startup and immutable digest qualification.
- [ ] Static/live role verification, App permission and installation acceptance.

## Section 7: Validation Proof

- `python -m unittest discover -s tests -p "test_*.py" -v`: executable synthetic
  issue/runner/revision/negative contracts pass locally. Final counts are in the
  private implementation receipt and source CI; no real external effects.
- Bash 5.3.15 syntax checks: all four production shell scripts pass.
- `bicep build infra\bicep\owned-runtime.bicep --stdout`: exit 0, Bicep 0.47.16,
  no compiler diagnostics. Static payload tests verify bounded job properties.
- `git diff --check`: exit 0.
- Docker client: daemon unavailable, image build BLOCKED; no daemon changes.
- Service validate, what-if, policy checks and live authority checks: NOT RUN;
  no exact deployment approval or immutable images. Plan is NOT Validated.
