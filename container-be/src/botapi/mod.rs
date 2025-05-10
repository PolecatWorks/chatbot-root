pub mod config;
pub mod directline;
pub mod handlers;

use std::{collections::HashMap, sync::Arc, time::Duration};

use base64::{prelude::BASE64_STANDARD, Engine};
use config::BotApiConfig;
use directline::{BotActivity, ConversationToken};
use log::{error, info};
use reqwest::Client;
use tokio::sync::{Mutex, RwLock};

use crate::{error::MyError, MyState};

/// Client to interact with the DirectLine API
/// This client is used to create and manage conversations with the DirectLine API.
/// It uses the reqwest library to make HTTP requests and the serde library to serialize and deserialize JSON data.
#[derive(Default, Debug, Clone)]
pub struct BotApi {
    pub config: BotApiConfig,
    client: Client,
    pub access_token: Arc<Mutex<Option<String>>>,
    pub webchat_access_token: Arc<Mutex<Option<String>>>,
    pub directline_access_token: Arc<Mutex<Option<String>>>,
    conversations: Arc<RwLock<HashMap<String, ConversationToken>>>,
}

impl BotApi {
    pub fn new(config: BotApiConfig, client: Client) -> Self {
        Self {
            config,
            client,
            access_token: Arc::new(Mutex::new(None)),
            webchat_access_token: Arc::new(Mutex::new(None)),
            directline_access_token: Arc::new(Mutex::new(None)),
            conversations: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new conversation
    ///
    /// This function will create a new conversation and return the conversation ID.
    ///
    ///    curl -X POST "https://europe.directline.botframework.com/v3/directline/conversations" \
    ///     -H "Authorization: Bearer $TOKEN"
    ///
    async fn create_conversation(&self) -> Result<ConversationToken, MyError> {
        let conv_url = self
            .config
            .directline
            .base_url
            .join("v3/directline/conversations")?;

        let conv_response = self
            .client
            .post(conv_url)
            .bearer_auth(&self.config.directline.secret)
            .send()
            .await?
            .error_for_status()?;

        let conv = conv_response.json::<ConversationToken>().await?;

        self.conversations
            .write()
            .await
            .insert(conv.conversation_id.clone(), conv.clone());

        Ok(conv)
    }

    /// Create a new conversation token
    ///
    /// This function will create a new conversation token for the DirectLine API.
    ///
    ///    curl -X POST "https://europe.directline.botframework.com/v3/directline/tokens/generate" \
    ///     -H "Authorization: Bearer $SECRET"
    async fn create_directline_token(&self) -> Result<ConversationToken, MyError> {
        let generate_url = self
            .config
            .directline
            .base_url
            .join("v3/directline/tokens/generate")?;

        let response = self
            .client
            .post(generate_url)
            .bearer_auth(&self.config.directline.secret)
            .send()
            .await?
            .error_for_status()?;

        let conv = response.json::<ConversationToken>().await?;

        self.conversations
            .write()
            .await
            .insert(conv.conversation_id.clone(), conv.clone());

        Ok(conv)
    }

    /// Refresh the token for an existing conversation
    ///
    /// This function will refresh the token for a given conversation ID.
    ///
    ///    curl -X POST "https://europe.directline.botframework.com/v3/directline/tokens/refresh" \
    ///     -H "Authorization: Bearer $TOKEN"
    pub async fn refresh_directline_token(
        &self,
        conversation: &str,
    ) -> Result<ConversationToken, MyError> {
        let conversations = self.conversations.read().await;
        let token = &conversations
            .get(conversation)
            .ok_or(MyError::Message("Conversation not found"))?
            .token;

        let refresh_url = self
            .config
            .directline
            .base_url
            .join("v3/directline/tokens/refresh")?;

        let response = self
            .client
            .post(refresh_url)
            .bearer_auth(token)
            .send()
            .await?
            .error_for_status()?;

        let conv = response.json::<ConversationToken>().await?;

        self.conversations
            .write()
            .await
            .insert(conversation.to_owned(), conv.clone());

        Ok(conv)
    }

    /// Get the token for an existing conversation
    ///
    /// This function will get a conversation token for a given conversation ID.
    ///
    ///     curl -X GET "https://europe.directline.botframework.com/v3/directline/conversations/$CONV_ID" \
    ///     -H "Authorization: Bearer $SECRET"
    pub async fn reconnect_conversation(
        &self,
        conversation: &str,
    ) -> Result<ConversationToken, MyError> {
        let conv_url = self
            .config
            .directline
            .base_url
            .join(&format!("v3/directline/conversations/{}", conversation))?;

        let response = self
            .client
            .get(conv_url)
            .bearer_auth(&self.config.directline.secret)
            .send()
            .await?
            .error_for_status()?;

        let conv = response.json::<ConversationToken>().await?;

        self.conversations
            .write()
            .await
            .insert(conversation.to_owned(), conv.clone());

        Ok(conv)
    }

    /// Send activity to a conversation
    ///
    /// This function will send an activity to a given conversation ID.
    ///
    ///    curl -X POST "https://europe.directline.botframework.com/v3/directline/conversations/$CONV_ID/activities"
    ///     -H "Authorization: Bearer $SECRET"
    pub async fn send_activity(&self, activity: &BotActivity) -> Result<BotActivity, MyError> {
        let conversation = activity.conversation_id();

        let conv_url = self.config.directline.base_url.join(&format!(
            "v3/directline/conversations/{}/activities",
            conversation
        ))?;

        let response = self
            .client
            .post(conv_url)
            .bearer_auth(
                &self
                    .conversations
                    .read()
                    .await
                    .get(conversation)
                    .ok_or(MyError::Message("Conversation not found"))?
                    .token,
            )
            .body(serde_json::to_string(activity)?)
            .send()
            .await?
            .error_for_status()?;

        Ok(response.json().await?)
    }

    /// Receive activity from a conversation
    ///
    /// This function will receive an activity from a given conversation ID.
    ///
    ///   curl -X GET "https://europe.directline.botframework.com/v3/directline/conversations/$CONV_ID/activities"
    ///    -H "Authorization: Bearer $TOKEN"
    pub async fn receive_activity(&self, conversation_id: &str) -> Result<BotActivity, MyError> {
        let token = self
            .conversations
            .read()
            .await
            .get(conversation_id)
            .ok_or(MyError::Message("Conversation not found"))?
            .token
            .clone();

        let conv_url = self.config.directline.base_url.join(&format!(
            "v3/directline/conversations/{}/activities",
            conversation_id
        ))?;

        let response = self
            .client
            .get(conv_url)
            .bearer_auth(&token)
            .send()
            .await?
            .error_for_status()?;

        Ok(response.json().await?)
    }
}

async fn maintain_webchat_token(state: &MyState, config: &BotApiConfig, client: &Client) {
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

async fn update_webchat_token(
    state: &MyState,
    config: &BotApiConfig,
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

            *state.bot_api.webchat_access_token.lock().await = Some(webchat_token);
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

pub async fn test_connection(config: &BotApiConfig) -> Result<(), MyError> {
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
