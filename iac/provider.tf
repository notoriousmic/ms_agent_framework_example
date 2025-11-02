terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
      version = "4.51.0"
    }
  }
}

## Configure the Microsoft Azure Provider
# Add your subscription ID below
provider "azurerm" {
  features {}
  subscription_id = ""
}