output "azure_ai_foundry_project_id" {
    value = azurerm_cognitive_account.this.id
    description = "The ID of the Azure AI Foundry Project."
}

output "azure_ai_foundry_project_name" {
    value = azurerm_cognitive_account.this.name
    description = "The name of the Azure AI Foundry Project."
}

# Managed Identity outputs for evaluation setup
output "user_managed_identity_id" {
    value = azurerm_user_assigned_identity.this.id
    description = "The ID of the user-assigned managed identity for evaluations."
}

output "user_managed_identity_client_id" {
    value = azurerm_user_assigned_identity.this.client_id
    description = "The client ID of the user-assigned managed identity for GitHub Actions and evaluation scripts."
}

output "user_managed_identity_principal_id" {
    value = azurerm_user_assigned_identity.this.principal_id
    description = "The principal ID of the user-assigned managed identity."
}

# Resource Group and Cognitive Account outputs for evaluation configuration
output "resource_group_name" {
    value = azurerm_resource_group.this.name
    description = "The name of the resource group containing AI Foundry resources."
}

output "cognitive_account_endpoint" {
    value = azurerm_cognitive_account.this.endpoint
    description = "The endpoint URL for the cognitive services account."
}

output "gpt4o_deployment_name" {
    value = azurerm_cognitive_deployment.this.name
    description = "The name of the GPT-4o model deployment for evaluations."
}