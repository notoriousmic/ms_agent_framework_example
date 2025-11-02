resource "azurerm_user_assigned_identity" "this" {
  location            = var.location
  name                = "${var.project_name}-github-actions-identity"
  resource_group_name = azurerm_resource_group.this.name
}

# Cognitive Services User role - Required for basic AI model access
resource "azurerm_role_assignment" "cognitive_services_user" {
  scope                = azurerm_cognitive_account.this.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# Cognitive Services OpenAI User role - Required for OpenAI model access during evaluations
resource "azurerm_role_assignment" "cognitive_services_openai_user" {
  scope                = azurerm_cognitive_account.this.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# Azure AI Developer role - Required for AI Foundry evaluation operations
resource "azurerm_role_assignment" "ai_developer" {
  scope                = azurerm_cognitive_account.this.id
  role_definition_name = "Azure AI Developer"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# Contributor role on resource group - Required for creating evaluation resources
resource "azurerm_role_assignment" "contributor_rg" {
  scope                = azurerm_resource_group.this.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# Storage Blob Data Contributor - Required for accessing evaluation datasets and results
data "azurerm_subscription" "current" {}

resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  scope                = "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/${azurerm_resource_group.this.name}"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# Monitoring Metrics Publisher - Required for publishing evaluation metrics
resource "azurerm_role_assignment" "monitoring_metrics_publisher" {
  scope                = azurerm_resource_group.this.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}