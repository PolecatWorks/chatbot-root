pub mod abc;
pub mod config;
pub mod directline;
pub mod dl_apis;
pub mod handlers;

use std::{collections::HashMap, sync::Arc, time::Duration};

use abc::AbcWebChat;
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
#[derive(Debug, Clone)]
pub struct BotApi {
    pub config: BotApiConfig,
    client: Client,
    pub access_token: Arc<Mutex<Option<String>>>,

    directline: AbcWebChat,
    webchat: AbcWebChat,
}

impl BotApi {
    pub fn new(config: BotApiConfig, client: Client) -> Self {
        Self {
            directline: AbcWebChat::new(config.directline.clone(), client.clone()),
            webchat: AbcWebChat::new(config.webchat.clone(), client.clone()),
            config,
            client,
            access_token: Arc::new(Mutex::new(None)),
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
