terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}


provider "azurerm" {
    subscription_id = "9d415cc4-075a-47ac-ba34-4328587f07ba"
  features {}
}


resource "random_password" "bot_password" {
  length           = 32
  special          = true
  override_special = "_%@"
}



resource "azurerm_resource_group" "bot_rg" {
  name     = "bot-resource-group"
  location = "West Europe"
}

resource "azurerm_service_plan" "bot_service_plan" {
  name                = "bot-service-plan"
  location            = azurerm_resource_group.bot_rg.location
  resource_group_name = azurerm_resource_group.bot_rg.name
  os_type             = "Linux"
  sku_name            = "F1"
}





resource "azurerm_bot_service_azure_bot" "bot_registration" {
  name                = "bot-registration"
  location            = azurerm_resource_group.bot_rg.location
  resource_group_name = azurerm_resource_group.bot_rg.name
  microsoft_app_id    = data.azurerm_client_config.current.client_id
  sku                 = "F0"

  # IMPORTANT: This endpoint URL needs to point to your AKS Ingress
  # You'll likely need to update this *after* deploying your app and setting up Ingress
  # For now, use a placeholder. Update later via Azure Portal, CLI, or CI/CD.
  endpoint = "https://bot.polecatworks.com/api/messages"

  display_name = "Rust Teams Bot"


  # developer_app_insights_api_key        = azurerm_application_insights_api_key.example.api_key
  # developer_app_insights_application_id = azurerm_application_insights.example.app_id


  tags = {
    environment = "dev"
    project     = "RustTeamsBot"
  }
}

data "azurerm_client_config" "current" {}

variable "microsoft_app_id" {
    type = string
    default = "abcdef"
}
# variable "microsoft_app_secret" {}

output "bot_messaging_endpoint" {
  value = azurerm_bot_service_azure_bot.bot_registration.endpoint
}

output "bot_messaging_id" {
  value = azurerm_bot_service_azure_bot.bot_registration.id
}
