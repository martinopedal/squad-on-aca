# Optional owned private ACR publisher

**Prepared source, not a deployed or qualified publisher.** This standalone
entrypoint does not change the upstream Terraform/Bicep recipe, build an image,
authenticate to Azure, create a subnet or update a job.

## Why a dedicated ACR task agent pool?

The default cloud builder is not inside your registry's private network.
`AcrPush` does not establish network connectivity. A Linux ACR agent pool can
join a qualified VNet subnet, resolve the registry's private DNS and use its
private endpoint. Premium ACR and a supported region are required; this focused
recipe allows Sweden Central only.

`infra/bicep/owned-publisher.bicep` deploys just one pool child under an existing
registry, using the provider's current agent-pool API `2025-03-01-preview`:

| Input | Meaning |
| --- | --- |
| `registryName` | Existing, independently accepted owned Premium registry |
| `agentPoolName` | New, separately owned pool; no existing pool takeover |
| `buildSubnetResourceId` | Separately accepted private build subnet |
| `location` | Sweden Central, matching the qualified target |
| `capacity` | Default `0`; only `0` or `1`, hardcoded Linux S1 |

There is no automatic idle shutdown. S1 is two vCPUs and 3 GB RAM; **allocation**
is billed even when no task runs. Capacity one activation and capacity zero
retirement require bounded, separately reviewed IaC execution. The default
standard quota of 16 cores is documentation, not a live quota admission result.

## Mandatory private preflight

- Independently accept the exact publisher and application source commits.
- Establish single-writer ownership for the existing registry/network. If a
  subnet is missing, its existing AVNM/IPAM source owner must declare it.
  This public fork must not redeploy the Terraform-owned network.
- Prove private registry login **and data** DNS resolution from the build
  subnet, private routing, sufficient unallocated addresses, no conflicting
  service delegation, subnet join authority and actual quota admission.
- Explicitly allow documented task dependencies: Azure Key Vault, Storage,
  Event Hub, Entra and Monitor on TCP443, plus Monitor TCP12000. Qualify task
  source/base/package egress too. DNS/service endpoints alone are not firewall
  rules; do not weaken registry public access or alter existing routes to fit.
- Accept a current S1 allocation quote and a supervised cost/cleanup envelope.
  A generic task-duration retail meter is not proof of pool allocation pricing.
- Invoke Azure Validate, native validate and exact what-if with private
  parameters. Require one new pool child and no existing-asset change, followed
  by independent immutable-plan review and the human apply gate.
- Provision only through the reviewed IaC. Then prove a scratch build/push
  before any application publication. Preserve actual run/digest receipts.

Local, Azure-free source verification (Bicep CLI and Python installed):

```text
python -m unittest discover -s tests -p test_owned_publisher.py -v
```

Do not treat green compile/CI as live network, permission, quota or price proof.
The PR workflow deliberately has no Azure login, secrets, push or dispatch.

## Publication after all gates

Use the already authorized operator, not copied host tokens or registry admin
credentials. The official quick-task interface supports this shape:

```text
az acr build --subscription <approved-subscription> --resource-group <approved-rg> --registry <approved-registry> --agent-pool <approved-active-pool> --image squad-agent:<accepted-full-commit> --file <accepted-dockerfile-path> --platform linux/amd64 --timeout 1200 https://github.com/martinopedal/squad-on-aca.git#<accepted-full-commit>
```

This is **not** an executable approval. Recheck the actual accepted revision's
Dockerfile path, context and all build arguments. Match its proven CI recipe;
never build a rejected revision, moving branch, dirty checkout or new proposal.
No credentials are embedded in the public owned-fork source URL. Successful
publication yields an actual image digest; digest-pinned ACA job updates require
their own deployment gates.

In success **or failure**, cancel only the recorded active build if necessary,
wait for it to finish, retire pool capacity through the reviewed zero-capacity
IaC and verify the actual readback. A process timeout does not retire a pool.

Trusted-service bypass documents ACR **image import**, not arbitrary Tasks
build/push. An existing private runner is an option only after actual
authorization and network qualification; this change does not create one.

## Official references

- [Pool regions, sizing, VNet dependencies and scale to zero](https://learn.microsoft.com/azure/container-registry/tasks-agent-pools)
- [Exact pool ARM/Bicep schema](https://learn.microsoft.com/azure/templates/microsoft.containerregistry/2025-03-01-preview/registries/agentpools)
- [Private endpoint and DNS requirements](https://learn.microsoft.com/azure/container-registry/container-registry-private-endpoints)
- [Trusted-service limitations](https://learn.microsoft.com/azure/container-registry/allow-access-trusted-services)
- [Allocation pricing](https://azure.microsoft.com/pricing/details/container-registry/)
