output "azure_ai_foundry_project_id" {
    value = azurerm_cognitive_account.this.id
    description = "The ID of the Azure AI Foundry Project."
}

output "azure_ai_foundry_project_name" {
    value = azurerm_cognitive_account.this.name
    description = "The name of the Azure AI Foundry Project."
}

# Outputs for Service Principal used in GitHub Actions
output "service_principal_id" {
  value       = azuread_service_principal.this.id
  description = "The ID of the service principal."
}

output "service_principal_client_id" {
  value       = azuread_service_principal.this.client_id
  description = "The client ID (App ID) for GitHub OIDC authentication."
}

output "service_principal_object_id" {
  value       = azuread_service_principal.this.object_id
  description = "The object ID of the service principal."
}

output "tenant_id" {
  value       = data.azurerm_client_config.current.tenant_id
  description = "Azure AD tenant ID for authentication."
}

output "subscription_id" {
  value       = data.azurerm_client_config.current.subscription_id
  description = "Azure subscription ID for GitHub workflows."
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