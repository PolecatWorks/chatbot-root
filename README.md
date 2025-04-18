# Build a MS Teams Bot

Create a bot for MS Teams.
Use Rust to build the app.

## Overview of Bots

Bots are software applications that interact with users through text-based conversations. They can range from simple scripts to advanced AI systems that learn and adapt. In Microsoft Teams, bots can act as virtual assistants to automate tasks, provide customer support, and more.

## Types of Bots

- **Notification Bots**: Send alerts, reminders, or updates to users in Teams channels or chats.
- **Workflow Bots**: Automate and streamline business processes by managing tasks and workflows.
- **Command Bots**: Respond to simple commands using Adaptive Cards for UI.

## Bot Development Basics

- **Activity Handler**: Manages events or activities triggered by user interactions.
- **Bot Logic**: Defines decision-making rules and conditions for bot responses.
- **Bot Scope**: Determines how the bot interacts with users (e.g., personal chat, group chat, or channel).

## Development Tools

- Use the **Bot Framework SDK** or **Teams AI Library** with Teams Toolkit to build bot capabilities.
- AI-powered bots can leverage custom AI models for advanced features like natural language understanding.

## Setting Up Azure Components and Generating API Tokens

To enable the bot to interact with the Microsoft Bot Framework, you need to set up Azure components and generate API tokens. Follow these steps:

### Setup Terraform

Before you start creating the Azure components you need to install terraform

    brew install azure-cli
    az login
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform

Then you can try it out with

    make terraform-init


### 1. Register Your Bot in Azure
1. Log in to the [Azure Portal](https://portal.azure.com/).
2. Navigate to **Azure Bot Services** and create a new bot or select an existing one.
3. During the bot creation process, you will be prompted to provide the following details:
   - **Bot Handle**: A unique name for your bot.
   - **Messaging Endpoint**: The URL where your bot will receive messages (e.g., `https://<your-domain>/api/messages`).
   - **App Service Plan**: Choose a pricing tier.
4. Once the bot is created, navigate to the **Settings** page to find the **App ID** and **App Secret**.

### 2. Generate an API Token
To authenticate your bot with the Microsoft Bot Framework REST API, you need to generate an API token using the App ID and App Secret.

#### Steps to Generate a Token:
1. Use the following OAuth2 endpoint:
   - `https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token`
2. Make a POST request to the endpoint with the following form data:
   ```
   grant_type=client_credentials
   client_id=<Your App ID>
   client_secret=<Your App Secret>
   scope=https://api.botframework.com/.default
   ```
3. The response will include an `access_token`. Use this token in the `Authorization` header for API requests.

#### Example Using `curl`:
```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<Your App ID>" \
  -d "client_secret=<Your App Secret>" \
  -d "scope=https://api.botframework.com/.default" \
  https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token
```

### 3. Update Your Bot Configuration
Once you have the API token, update your bot's configuration to use it for authenticated API calls. You can pass the token as a command-line argument or store it securely in an environment variable.

## References

- [Microsoft Teams Bot Overview](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
- [API reference for the Bot Framework Connector service](https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-api-reference?view=azure-bot-service-4.0)


# Setting up local dev

Prepare a referese proxy for using with MS Teams.

## ngrok

Ngrok seems like it provides the relevant reverse proxy capabaility to project to dev laptop.

    brew install ngrok
