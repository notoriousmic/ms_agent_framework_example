## Create a resource group for the resources to be stored in
resource "azurerm_resource_group" "this" {
  name     = "rg-aifoundry-${var.project_name}"
  location = var.location
}

## Create an AI Foundry resource
resource "azurerm_cognitive_account" "this" {
  name                = "aifoundry-${var.project_name}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  kind                = "AIServices"

  identity {
    type = "SystemAssigned"
  }
  sku_name = var.azure_ai_services_sku_name

}

