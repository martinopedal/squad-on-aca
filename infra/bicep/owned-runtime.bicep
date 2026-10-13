targetScope = 'resourceGroup'

@description('Exact existing owned job bindings. Qualification must verify both jobs exist; this template is not a new-environment deployment.')
param jobs {
  pollerName: string
  agentName: string
  location: string
  pollerTags: object
  agentTags: object
  workloadProfileName: string
}

@description('Existing environment and identity names in this resource group. No network, identity or RBAC resources are created.')
param hosting {
  environmentName: string
  identityName: string
  registryServer: string
}

@description('Immutable digest references, qualified before deployment. Neither image may use latest or another mutable tag.')
param images {
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
  pollIssueNumber: string
  pollAgent: string
  pollStopAfterUtc: string
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

resource poller 'Microsoft.App/jobs@2025-01-01' = {
  name: jobs.pollerName
  location: jobs.location
  tags: jobs.pollerTags
  // Enqueue must not begin while the old fallback-capable worker is deployed.
  dependsOn: [agent]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    environmentId: environment.id
    workloadProfileName: jobs.workloadProfileName
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 60
      replicaRetryLimit: 0
      scheduleTriggerConfig: {
        cronExpression: '*/5 * * * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: []
      registries: [{ server: hosting.registryServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'poller'
        image: images.agent
        command: ['/usr/bin/timeout']
        args: ['--signal=TERM', '--kill-after=5s', '50s', '/poller-entrypoint.sh']
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: concat(commonEnv, [
          { name: 'SQUAD_TARGET_REPO', value: routing.targetRepo }
          { name: 'SQUAD_POLL_ISSUE_NUMBER', value: routing.pollIssueNumber }
          { name: 'SQUAD_POLL_AGENT', value: routing.pollAgent }
          { name: 'SQUAD_POLL_STOP_AFTER_UTC', value: routing.pollStopAfterUtc }
          { name: 'AZURE_STORAGE_ACCOUNT', value: routing.storageAccount }
          { name: 'QUEUE_NAME', value: routing.queueName }
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
    workloadProfileName: jobs.workloadProfileName
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
          { name: 'SQUAD_POLL_ISSUE_NUMBER', value: routing.pollIssueNumber }
          { name: 'SQUAD_POLL_AGENT', value: routing.pollAgent }
          { name: 'SQUAD_README_ONLY', value: 'true' }
          { name: 'SQUAD_TIMEOUT_SECONDS', value: '480' }
        ])
      }]
    }
  }
}

@description('Exact existing owned runner job repurposed as a poller; not an execution receipt.')
output pollerJobId string = poller.id

@description('Exact existing owned agent job ID; not an execution receipt.')
output agentJobId string = agent.id
