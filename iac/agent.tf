## Create a deployment for OpenAI's GPT-4o in the AI Foundry resource
resource "azurerm_cognitive_deployment" "this" {
  depends_on = [
    azurerm_cognitive_account.this
  ]

  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.this.id

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
  }
}