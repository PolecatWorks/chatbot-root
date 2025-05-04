pub mod handlers;

use std::{sync::Arc, time::Duration};

use base64::{prelude::BASE64_STANDARD, Engine};
use derive_builder::Builder;
use log::{debug, error, info, warn};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tokio::sync::Mutex;
use url::Url;

use crate::{error::MyError, MyState};

#[derive(Debug, Deserialize, Serialize)]
#[serde(tag = "type")]
pub enum BotResponses {
    // #[serde(alias = "message")]
    // // #[serde(rename="invoke")]
    // Activity(Activity),
    #[serde(alias = "conversationUpdate")]
    ConversationUpdate(ConversationUpdate),
    #[serde(rename = "message")]
    Message(Message),
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ConversationUpdate {
    pub id: String,
    pub timestamp: String,
    pub service_url: Option<Url>,
    pub channel_id: String,
    pub from: Recipient,
    pub conversation: Conversation,
    pub recipient: Recipient,
    pub members_added: Vec<Recipient>,
}

#[derive(Debug, Deserialize, Serialize, Builder, Default)]
#[serde(rename_all = "camelCase")]
#[builder(default)]
pub struct Message {
    pub service_url: Option<Url>,
    pub channel_id: String,
    pub from: Recipient,
    pub conversation: Conversation,
    pub recipient: Recipient,
    pub locale: String,
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text_format: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input_hint: Option<String>,
    pub id: String,
    pub local_timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub local_timezone: Option<String>,
    pub timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub channel_data: Option<ChannelData>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub entities: Option<Vec<Entity>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reply_to_id: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone, Default)]
pub struct Recipient {
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub role: Option<String>,
}

/// Activity message
///
/// https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-api-reference?view=azure-bot-service-4.0#activity-object
#[derive(Debug, Deserialize, Serialize, Builder, Clone, Default)]
#[builder(default)]
#[serde(rename_all = "camelCase")]
pub struct Activity {
    // pub r#type: String,
    pub text: String,
    pub from: Recipient,
    pub recipient: Recipient,
    pub conversation: Conversation,
    pub service_url: Option<Url>,
    pub channel_id: Option<String>,

    pub timestamp: Option<String>,

    pub id: Option<String>,
    pub local_timestamp: Option<String>,
    pub local_timezone: Option<String>,
    pub text_format: Option<String>,
    pub locale: Option<String>,
    pub attachments: Option<Vec<Attachment>>,
    pub entities: Option<Vec<Entity>>,
    pub channel_data: Option<ChannelData>,
    pub reply_to_id: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct User {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Deserialize, Serialize, Clone, Default)]
pub struct Conversation {
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Attachment {}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Entity {
    pub r#type: String,
    pub requires_bot_state: Option<bool>,
    pub supports_listening: Option<bool>,
    pub supports_tts: Option<bool>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ChannelData {
    #[serde(rename = "clientActivityID")]
    pub client_activity_id: String,
    pub client_timestamp: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct WebChatConfig {
    pub secret: String, // Secret for WebChat integration
    pub token_url: Url, // URL to fetch WebChat token
}

#[derive(Deserialize, Debug, Clone)]
pub struct DirectLineConfig {
    pub secret: String, // Secret for DirectLine integration
    pub token_url: Url, // URL to fetch DirectLine token
}

#[derive(Deserialize, Debug, Clone)]
pub struct TeamsConfig {
    pub auth_endpoint: Url,
    pub bot_endpoint: Url,
    pub tenant_id: String,
    pub scope: String,
    pub id: String,
    pub secret: String,
    pub webchat: WebChatConfig,       // WebChat configuration
    pub directline: DirectLineConfig, // DirectLine configuration
    #[serde(with = "humantime_serde")]
    pub auth_fail_sleep: Duration,
    #[serde(with = "humantime_serde")]
    pub auth_margin: Duration,
}

impl Default for TeamsConfig {
    fn default() -> Self {
        Self {
            auth_endpoint: Url::parse("https://localhost").unwrap(),
            bot_endpoint: Url::parse("https://localhost").unwrap(),
            tenant_id: Default::default(),
            scope: Default::default(),
            id: Default::default(),
            secret: Default::default(),
            webchat: WebChatConfig {
                secret: Default::default(),
                token_url: Url::parse("https://localhost").unwrap(),
            },
            directline: DirectLineConfig {
                secret: Default::default(),
                token_url: Url::parse("https://localhost").unwrap(),
            },
            auth_fail_sleep: Duration::from_secs(60),
            auth_margin: Duration::from_secs(60),
        }
    }
}

#[derive(Default, Debug, Clone)]
pub struct Teams {
    pub access_token: Arc<Mutex<Option<String>>>,
    pub webchat_access_token: Arc<Mutex<Option<String>>>,
    pub directline_access_token: Arc<Mutex<Option<String>>>,
}
pub async fn maintain_access_token(state: MyState) -> Result<(), MyError> {
    // maintain_app_token(state.clone()).await

    tokio::select! {
        _ = state.ct.cancelled() => {
            info!("Cancelled maintain_access_token");
        }
        _ = maintain_app_token(state.clone()) => {
            info!("Cancelled maintain_app_token");
        }
        _ = maintain_direcline_token(&state, &state.config.teams, &state.client) => {
            info!("Cancelled maintain_direcline_token");
        }
        _ = maintain_webchat_token(&state, &state.config.teams, &state.client) => {
            info!("Cancelled maintain_webchat_token");
        }
    }

    state.ct.cancel();
    Ok(())
}

pub async fn maintain_app_token(state: MyState) -> Result<(), MyError> {
    let config = state.config.teams.clone();

    // TODO: Setup liveness starting here

    let client = state.client.clone();

    // Fetch and parse the well-known endpoints to get issuer and token endpoint
    let well_known_url = config
        .auth_endpoint
        .join(".well-known/openid-configuration")?;
    debug!("Fetching well-known endpoints from: {}", well_known_url);
    let well_known_response = client.get(well_known_url).send().await?;

    debug!("Well-known response: {:?}", well_known_response);
    if !well_known_response.status().is_success() {
        error!(
            "Failed to fetch well-known endpoints: {}",
            well_known_response.status()
        );
        return Err(MyError::RequestTokenError(format!(
            "Failed to fetch well-known endpoints: {}",
            well_known_response.status()
        )));
    }

    let well_known_data: serde_json::Value = well_known_response.json().await?;
    let issuer = well_known_data["issuer"].as_str().ok_or_else(|| {
        MyError::RequestTokenError("Missing issuer in well-known endpoints".to_string())
    })?;
    let token_endpoint = well_known_data["token_endpoint"].as_str().ok_or_else(|| {
        MyError::RequestTokenError("Missing token endpoint in well-known endpoints".to_string())
    })?;

    info!("Discovered issuer: {}", issuer);
    info!("Discovered token endpoint: {}", token_endpoint);

    while !state.ct.is_cancelled() {
        // If we are cancelled, break out of the loop
        // Try to get the token. If we fail we will sleep for a bit and try again
        // If we get it then we will update the token object in the state AND update the liveness check AND we set the token to None

        // Replace the exchange_client_credentials logic with reqwest
        let token_response = client
            .post(token_endpoint)
            .form(&[
                ("client_id", config.id.clone()),
                ("client_secret", config.secret.clone()),
                ("grant_type", "client_credentials".to_string()),
                ("scope", config.scope.clone()),
            ])
            .send()
            .await;

        println!("Token response: {:?}", token_response);

        match token_response {
            Ok(response) if response.status().is_success() => {
                let token: serde_json::Value = response.json().await?;
                let access_token = token["access_token"]
                    .as_str()
                    .map(str::to_string)
                    .ok_or_else(|| {
                        MyError::RequestTokenError("Missing token in app token".to_string())
                    })?;

                *state.teams.access_token.lock().await = Some(access_token);
                info!("Access token updated successfully");

                let expires_in = token["expires_in"]
                    .as_str()
                    .map(str::parse::<u64>)
                    .ok_or_else(|| {
                        MyError::RequestTokenError("Missing expires in app token".to_string())
                    })??;
                let refresh_wait = Duration::from_secs(expires_in) - config.auth_margin;

                info!("Access token expires in: {} seconds", expires_in);

                tokio::time::sleep(refresh_wait).await;
            }
            Ok(response) => {
                info!("Failed to fetch token: {}", response.status());
                tokio::time::sleep(config.auth_fail_sleep).await;
            }
            Err(error) => {
                info!("Error fetching token: {}", error);
                tokio::time::sleep(config.auth_fail_sleep).await;
            }
        }

        // update_webchat_token(&state, &config, &client).await;
        // update_direcline_token(&state, &config, &client).await;
        tokio::time::sleep(config.auth_fail_sleep).await;
    }

    Ok(())
}

async fn maintain_direcline_token(state: &MyState, config: &TeamsConfig, client: &Client) {
    while !state.ct.is_cancelled() {
        // If we are cancelled, break out of the loop
        // Try to get the token. If we fail we will sleep for a bit and try again
        // If we get it then we will update the token object in the state AND update the liveness check AND we set the token to None

        match update_direcline_token(state, config, client).await {
            Ok(duration) => {
                let sleep_duration = duration - config.auth_margin;
                info!(
                    "DirectLine token expires in: {} seconds",
                    duration.as_secs()
                );
                tokio::time::sleep(sleep_duration).await;
            }
            Err(error) => {
                info!("Error fetching DirectLine token: {}", error);
                tokio::time::sleep(config.auth_fail_sleep).await;
            }
        }
    }
}

async fn maintain_webchat_token(state: &MyState, config: &TeamsConfig, client: &Client) {
    while !state.ct.is_cancelled() {
        // If we are cancelled, break out of the loop
        // Try to get the token. If we fail we will sleep for a bit and try again
        // If we get it then we will update the token object in the state AND update the liveness check AND we set the token to None

        match update_webchat_token(state, config, client).await {
            Ok(duration) => {
                let sleep_duration = duration - config.auth_margin;
                info!("WebChat token expires in: {} seconds", duration.as_secs());
                tokio::time::sleep(sleep_duration).await;
            }
            Err(error) => {
                info!("Error fetching WebChat token: {}", error);
                tokio::time::sleep(config.auth_fail_sleep).await;
            }
        }
    }
}

fn jwt_expire_time(token: &str) -> Result<Duration, MyError> {
    // Decode the JWT token to get the expiration time
    println!("Decoding JWT token: {}", token);
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 3 {
        return Err(MyError::Message("JWT does not have 3 parts"));
    }

    println!("Decoding parts: {:?}", parts[1]);
    let payload = BASE64_STANDARD.decode(parts[1])?;

    let payload_str = String::from_utf8(payload)?;
    let payload_json: serde_json::Value = serde_json::from_str(&payload_str)?;

    let exp = payload_json["exp"]
        .as_u64()
        .ok_or(MyError::Message("Missing exp field in JWT payload"))?;
    let now = chrono::Utc::now().timestamp() as u64;

    Ok(Duration::from_secs(exp - now))
}

async fn update_direcline_token(
    state: &MyState,
    config: &TeamsConfig,
    client: &Client,
) -> Result<Duration, MyError> {
    // Maintain DirectLine token

    let directline_token_response = client
        .post(config.directline.token_url.clone())
        .header(
            "Authorization",
            format!("Bearer {}", config.directline.secret),
        )
        .send()
        .await?;

    match directline_token_response {
        response if response.status().is_success() => {
            let token: serde_json::Value = response.json().await?;
            let directline_token =
                token["token"].as_str().map(str::to_string).ok_or_else(|| {
                    MyError::RequestTokenError("Missing token in directline".to_string())
                })?;

            *state.teams.directline_access_token.lock().await = Some(directline_token.clone());
            info!("DirectLine token updated successfully");

            // jwt_expire_time(&directline_token)
            Ok(Duration::from_secs(3000))
        }
        response => {
            error!(
                "Failed to fetch DirectLine token: {:?} and {}",
                response, config.directline.token_url
            );
            Err(MyError::RequestTokenError(format!(
                "Failed to fetch DirectLine token: {:?} and {}",
                response, config.directline.token_url
            )))
        }
    }
}

async fn update_webchat_token(
    state: &MyState,
    config: &TeamsConfig,
    client: &Client,
) -> Result<Duration, MyError> {
    let webchat_token_response = client
        .get(config.webchat.token_url.clone())
        .header(
            "Authorization",
            format!("BotConnector {}", config.webchat.secret),
        )
        .send()
        .await;

    // println!("WebChat token response: {:?}", webchat_token_response);

    match webchat_token_response {
        Ok(response) if response.status().is_success() => {
            let token: serde_json::Value = response.json().await?;
            let webchat_token = token.as_str().map(str::to_string).ok_or_else(|| {
                MyError::RequestTokenError("Missing token in webchat".to_string())
            })?;

            *state.teams.webchat_access_token.lock().await = Some(webchat_token);
            info!("WebChat token updated successfully");

            let refresh_wait = Duration::from_secs(3000);
            Ok(refresh_wait)
        }
        Ok(response) => {
            error!(
                "Failed to fetch WebChat token: {:?} from {}",
                response, config.webchat.token_url
            );
            Err(MyError::RequestTokenError(format!(
                "Failed to fetch WebChat token: {:?} from {}",
                response, config.webchat.token_url
            )))
        }
        Err(error) => {
            error!("Error fetching WebChat token: {}", error);
            Err(MyError::RequestTokenError(format!(
                "Error fetching WebChat token: {}",
                error
            )))
        }
    }
}

pub async fn test_connection(config: &TeamsConfig) -> Result<(), MyError> {
    info!("I should test the App connection + auth here");

    info!("Connection info is: {:?}", config);

    let client = Client::new();

    let well_known_url = config
        .auth_endpoint
        .join(".well-known/openid-configuration")?;
    info!("Fetching well-known endpoints from: {}", well_known_url);
    // let well_known_response = client
    //     .get(well_known_url)
    //     // .build()?
    //     .send()
    //     .await?;
    let well_known_response = reqwest::get(well_known_url).await?;
    info!("Well-known response: {:?}", well_known_response);

    // let issuer_url = IssuerUrl::new(config.auth_endpoint.as_str().to_owned())?;
    // println!("Parsed Issuer URL: {}", issuer_url.as_str());
    // // The crate automatically appends "/.well-known/openid-configuration"
    // // or "/.well-known/oauth-authorization-server" when fetching.

    // // 2. Discover the provider metadata asynchronously
    // //    This function sends an HTTP GET request to the .well-known endpoint.
    // //    It requires an async HTTP client function. We use the one provided
    // //    by the `reqwest-client` feature.
    // let provider_metadata = CoreProviderMetadata::discover_async(
    //     issuer_url, // The base URL of the provider
    //     &client,    // The HTTP client function
    //                 // If using openidconnect v2.x: reqwest::async_http_client
    // )
    // .await;

    // info!("Issuer: {:?}", provider_metadata.clone().issuer());

    // let client_id = ClientId::new(config.id.clone());
    // let client_secret = ClientSecret::new(config.secret.clone());

    // let client_request = CoreClient::from_provider_metadata(
    //     provider_metadata.clone(), // Metadata fetched earlier
    //     client_id,
    //     Some(client_secret), // Needed later for code exchange
    // );

    // let token_response = client_request
    //     .exchange_client_credentials()
    //     .unwrap()
    //     .add_scope(Scope::new(
    //         "api://87de8678-74cc-4a80-8987-ce00baf25087/.default".to_owned(),
    //     ))
    //     .request_async(&client)
    //     .await
    //     .unwrap();
    // info!("Token response: {:?}", token_response);
    // info!("Access token: {:?}", token_response.access_token().secret());

    // // Create a new request to call to the API endpoint with the access token
    // let api_url = config.bot_endpoint.join("api/messages").unwrap();
    // let access_token = token_response.access_token().secret();

    Ok(())
}
