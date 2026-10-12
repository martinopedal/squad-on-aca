targetScope = 'resourceGroup'

@description('Exact existing owned job bindings. Qualification must verify both jobs exist; this template is not a new-environment deployment.')
param jobs {
  runnerName: string
  agentName: string
  location: string
  runnerTags: object
  agentTags: object
}

@description('Existing environment and identity names in this resource group. No network, identity or RBAC resources are created.')
param hosting {
  environmentName: string
  identityName: string
  registryServer: string
}

@description('Immutable digest references, qualified before deployment. Neither image may use latest or another mutable tag.')
param images {
  runner: string
  agent: string
}

@description('Public startup metadata only. All protected values remain in the existing Key Vault and are read by Managed Identity inside the container.')
param routing {
  targetRepo: string
  appId: string
  appSlug: string
  installationId: string
  vaultName: string
  appSecretName: string
  copilotSecretName: string
  storageAccount: string
  queueName: string
  runnerLabels: string
}

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: hosting.environmentName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: hosting.identityName
}

var commonEnv = [
  { name: 'GITHUB_APP_ID', value: routing.appId }
  { name: 'GITHUB_APP_SLUG', value: routing.appSlug }
  { name: 'GITHUB_APP_INSTALLATION_ID', value: routing.installationId }
  { name: 'KEY_VAULT_NAME', value: routing.vaultName }
  { name: 'KEY_VAULT_SECRET_NAME', value: routing.appSecretName }
  { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
]

resource runner 'Microsoft.App/jobs@2025-01-01' = {
  name: jobs.runnerName
  location: jobs.location
  tags: jobs.runnerTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
      secrets: []
      registries: [{ server: hosting.registryServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'runner'
        image: images.runner
        resources: { cpu: 1, memory: '2Gi' }
        env: concat(commonEnv, [
          { name: 'GITHUB_REPO', value: routing.targetRepo }
          { name: 'LABELS', value: routing.runnerLabels }
        ])
      }]
    }
  }
}

resource agent 'Microsoft.App/jobs@2025-01-01' = {
  name: jobs.agentName
  location: jobs.location
  tags: jobs.agentTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Event'
      replicaTimeout: 600
      replicaRetryLimit: 0
      secrets: []
      registries: [{ server: hosting.registryServer, identity: identity.id }]
      eventTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
        scale: {
          minExecutions: 0
          maxExecutions: 1
          pollingInterval: 30
          rules: [{
            name: 'queue-scaling'
            type: 'azure-queue'
            identity: identity.id
            metadata: {
              accountName: routing.storageAccount
              queueName: routing.queueName
              queueLength: '1'
            }
          }]
        }
      }
    }
    template: {
      containers: [{
        name: 'squad-agent'
        image: images.agent
        resources: { cpu: 1, memory: '2Gi' }
        env: concat(commonEnv, [
          { name: 'AZURE_STORAGE_ACCOUNT', value: routing.storageAccount }
          { name: 'QUEUE_NAME', value: routing.queueName }
          { name: 'COPILOT_TOKEN_SECRET_NAME', value: routing.copilotSecretName }
          { name: 'SQUAD_TARGET_REPO', value: routing.targetRepo }
          { name: 'SQUAD_README_ONLY', value: 'true' }
          { name: 'SQUAD_TIMEOUT_SECONDS', value: '480' }
        ])
      }]
    }
  }
}

@description('Exact existing owned runner job ID; not an execution receipt.')
output runnerJobId string = runner.id

@description('Exact existing owned agent job ID; not an execution receipt.')
output agentJobId string = agent.id
