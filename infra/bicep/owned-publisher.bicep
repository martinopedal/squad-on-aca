targetScope = 'resourceGroup'

@description('Existing owned Premium registry name. This template never redeploys the registry.')
@minLength(5)
@maxLength(50)
param registryName string

@description('Name of the separately owned, optional private task agent pool.')
@minLength(3)
@maxLength(20)
param agentPoolName string

@description('Previously qualified build subnet ARM ID; DNS, routing, NSG and explicit egress remain network-owner prerequisites.')
@minLength(1)
param buildSubnetResourceId string

@description('Qualified registry/pool region. This focused entrypoint supports only Sweden Central.')
@allowed([
  'swedencentral'
])
param location string = 'swedencentral'

@description('Zero when inactive. One instance requires a separate accepted activation/cost/cleanup plan; no automatic idle scaling is implied.')
@allowed([
  0
  1
])
param capacity int = 0

// Existing only: parent network access, admin, identities and RBAC stay untouched.
resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: registryName
}

resource pool 'Microsoft.ContainerRegistry/registries/agentPools@2025-03-01-preview' = {
  parent: registry
  name: agentPoolName
  location: location
  properties: {
    count: capacity
    os: 'Linux'
    tier: 'S1'
    virtualNetworkSubnetResourceId: buildSubnetResourceId
  }
}

output agentPoolResourceId string = pool.id
