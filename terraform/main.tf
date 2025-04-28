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



resource "azurerm_resource_group" "bot_rg" {
  name     = "bot-resource-group"
  location = "West Europe"

  tags = {
    environment = "dev"
    project     = "RustTeamsBot"
  }
}

# resource "azurerm_log_analytics_workspace" "bot_rg" {
#   name                = "example"
#   location            = azurerm_resource_group.bot_rg.location
#   resource_group_name = azurerm_resource_group.bot_rg.name
#   sku                 = "PerGB2018"
#   retention_in_days   = 30

#   tags = {
#     environment = "dev"
#     project     = "RustTeamsBot"
#   }
# }

# resource "azurerm_application_insights" "bot_rg" {
#   name                = "example-appinsights"
#   location            = azurerm_resource_group.bot_rg.location
#   resource_group_name = azurerm_resource_group.bot_rg.name
#   application_type    = "web"

#   workspace_id = azurerm_log_analytics_workspace.bot_rg.id

#   tags = {
#     environment = "dev"
#     project     = "RustTeamsBot"
#   }
# }

# resource "azurerm_application_insights_api_key" "bot_rg" {
#   name                    = "example-appinsightsapikey"
#   application_insights_id = azurerm_application_insights.bot_rg.id
#   read_permissions        = ["aggregate", "api", "draft", "extendqueries", "search"]

# }




resource "azurerm_service_plan" "bot_service_plan" {
  name                = "bot-service-plan"
  location            = azurerm_resource_group.bot_rg.location
  resource_group_name = azurerm_resource_group.bot_rg.name
  os_type             = "Linux"
  sku_name            = "F1"

   tags = {
    environment = "dev"
    project     = "RustTeamsBot"
  }
}


# 1. Create the Azure AD Application for the Bot
resource "azuread_application" "bot_app" {
  display_name = "app-teams-bot-rust-prod" # Choose a display name
  # For multi-tenant bots, set sign_in_audience = "AzureADMultipleOrgs"
  # For single-tenant (default), it's "AzureADMyOrg"
  identifier_uris = [
    # "api://87de8678-74cc-4a80-8987-ce00baf25087"
   ]
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000"

           resource_access { # https://graph.microsoft.com/email
               id   = "64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0"
               type = "Scope"
            }
           resource_access { # https://graph.microsoft.com/openid
               id   = "37f7f235-527c-4136-accd-4a02d197296e"
               type = "Scope"
            }
           resource_access { # https://graph.microsoft.com/profile
               id   = "14dad69e-099b-42c9-810b-d002981feec1"
               type = "Scope"
            }
  }
}


# 2. Create a Client Secret (Password) for the Azure AD Application
resource "azuread_application_password" "bot_app_password" {
  application_id =  azuread_application.bot_app.id
  display_name          = "BOT password managed by Terraform" # Optional description for the secret
  # Set an expiry date if desired, e.g.:
  # end_date_relative = "8760h" # 1 year
}


# resource "azurerm_application_insights" "example" {
#   name                = "example-appinsights"
#   location            = azurerm_resource_group.bot_rg.location
#   resource_group_name = azurerm_resource_group.bot_rg.name
#   application_type    = "web"
# }

# resource "azurerm_application_insights_api_key" "example" {
#   name                    = "example-appinsightsapikey"
#   application_insights_id = azurerm_application_insights.example.id
#   read_permissions        = ["aggregate", "api", "draft", "extendqueries", "search"]
# }



resource "azurerm_bot_service_azure_bot" "example" {
  name                = "polecatworks"
  location            = azurerm_resource_group.bot_rg.location
  resource_group_name = azurerm_resource_group.bot_rg.name
  sku                 = "F0"
  microsoft_app_id = azuread_application.bot_app.object_id

  endpoint = "https://informally-large-terrier.ngrok-free.app/api/messages"

  display_name = "Rust Teams Bot"

  # developer_app_insights_api_key        = azurerm_application_insights_api_key.example.api_key
  # developer_app_insights_application_id = azurerm_application_insights.example.app_id


  tags = {
    environment = "dev"
    project     = "RustTeamsBot"
  }
}


# resource "azurerm_bot_web_app" "example" {
#   name                = "polecatworks-app"
#   location            = "global"
#   resource_group_name = azurerm_resource_group.bot_rg.name
#   sku                 = "F0"
#   microsoft_app_id    = azuread_application.bot_app.object_id

#   endpoint = "https://informally-large-terrier.ngrok-free.app/api/messages"

#    tags = {
#     environment = "dev"
#     project     = "RustTeamsBot"
#   }
# }



# (Optional but Recommended) Enable the Teams Channel
# Check the latest provider docs for direct channel management.
# If `azurerm_bot_channel_teams` exists and is stable:
# resource "azurerm_bot_channel_teams" "teams_channel" {
#   bot_name            = azurerm_bot_service_azurebot.bot_service.name
#   location            = azurerm_bot_service_azurebot.bot_service.location
#   resource_group_name = azurerm_resource_group.rg.name
#   # Add specific Teams channel settings if needed
# }
# If not, you might need to enable it manually or via Azure CLI post-deployment.



# output "insight_key" {
#   value = azurerm_application_insights.bot_rg.instrumentation_key
#   sensitive = true
# }

# output "insight_id" {
#   value = azurerm_application_insights.bot_rg.app_id
# }


output "bot_messaging_endpoint" {
  value = azurerm_bot_service_azure_bot.example.endpoint
}

# Bot's Microsoft Application ID (Client ID)
output "bot_microsoft_app_id" {
  description = "The Client ID of the Azure AD Application for the Bot."
  value       = azuread_application.bot_app.client_id
}

# Bot's Microsoft Application Password (Client Secret)
output "bot_microsoft_app_password" {
  description = "The Client Secret for the Bot's Azure AD Application. Store securely!"
  value       = azuread_application_password.bot_app_password.value
  sensitive   = true # Mark as sensitive to hide from stdout by default
}
