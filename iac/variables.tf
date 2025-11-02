variable "location" {
    description = "The Azure region to deploy resources in."
    type        = string
    default     = "westeurope"
}

variable "project_name" {
    description = "The name of the project."
    type        = string
    default     = "ms_agent_framework_example" 
}

variable "azure_ai_services_sku_name" {
    description = "The SKU for the azure ai services"
    type = string
    default = "S0"
}