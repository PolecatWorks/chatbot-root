use std::{sync::Arc, time::Duration};

use log::info;
use openidconnect::{
    core::{CoreClient, CoreProviderMetadata},
    ClientId, ClientSecret, IssuerUrl, OAuth2TokenResponse, Scope,
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tokio::sync::Mutex;
use url::Url;

use crate::{config::MyConfig, error::MyError, MyState};

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Activity {
    pub r#type: String,
    pub id: String,
    pub timestamp: String,
    pub local_timestamp: String,
    pub local_timezone: String,
    pub service_url: String,
    pub channel_id: String,
    pub from: User,
    pub conversation: Conversation,
    pub recipient: User,
    pub text_format: String,
    pub locale: String,
    pub text: String,
    pub attachments: Vec<Attachment>,
    pub entities: Option<Vec<Entity>>,
    pub channel_data: ChannelData,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct User {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Conversation {
    pub id: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Attachment {}

#[derive(Debug, Deserialize, Serialize)]
pub struct Entity {
    pub r#type: String,
    pub requires_bot_state: Option<bool>,
    pub supports_listening: Option<bool>,
    pub supports_tts: Option<bool>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ChannelData {
    #[serde(rename = "clientActivityID")]
    pub client_activity_id: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct TeamsConfig {
    auth_endpoint: Url,
    bot_endpoint: Url,
    tenant_id: String,
    scopes: Vec<String>,
    id: String,
    secret: String,
    #[serde(with = "humantime_serde")]
    pub auth_sleep: Duration,
    #[serde(with = "humantime_serde")]
    pub auth_margin: Duration,
}

impl Default for TeamsConfig {
    fn default() -> Self {
        Self {
            auth_endpoint: Url::parse("https://localhost").unwrap(),
            bot_endpoint: Url::parse("https://localhost").unwrap(),
            tenant_id: Default::default(),
            scopes: vec![],
            id: Default::default(),
            secret: Default::default(),
            auth_sleep: Duration::from_secs(60),
            auth_margin: Duration::from_secs(60),
        }
    }
}

#[derive(Default, Debug, Clone)]
pub struct Teams {
    pub access_token: Arc<Mutex<Option<String>>>,
}

pub async fn maintain_access_token(state: MyState) -> Result<(), MyError> {
    let config = state.config.teams.clone();

    let client = Client::new();
    let issuer_url = IssuerUrl::new(state.config.teams.auth_endpoint.as_str().to_owned())?;

    let provider_metadata = CoreProviderMetadata::discover_async(
        issuer_url, // The base URL of the provider
        &client,    // The HTTP client function
                    // If using openidconnect v2.x: reqwest::async_http_client
    )
    .await?;

    info!("Issuer: {}", provider_metadata.clone().issuer().as_str());

    let client_id = ClientId::new(config.id.clone());
    let client_secret = ClientSecret::new(config.secret.clone());

    let client_request = CoreClient::from_provider_metadata(
        provider_metadata.clone(), // Metadata fetched earlier
        client_id,
        Some(client_secret), // Needed later for code exchange
    );

    while !state.ct.is_cancelled() {
        // If we are cancelled, break out of the loop
        // Try to get the token. If we feil we will sleep for a bit and try again
        // If we get it then we will update the token object in the state AND update the liveness check AND we set the token to None

        let token_response = {
            let mut token_query = client_request
                .exchange_client_credentials()?
                .add_scopes(config.scopes.iter().map(|s| Scope::new(s.to_owned())));

            let token_response = token_query.request_async(&client).await.map_err(|error| {
                info!("Error getting token: {:?}", error);
                MyError::RequestTokenError(error.to_string())
            })?;

            Ok::<_, MyError>(token_response)
            // Ok(token_response)
        };

        match token_response {
            Ok(token_response) => {
                info!("Token expires in: {:?}", token_response.expires_in());

                *state.teams.access_token.lock().await =
                    Some(token_response.access_token().secret().to_string());
                // TODO: Add liveness check into this loop
                let refresh_wait = token_response.expires_in().unwrap() - config.auth_margin;
                tokio::time::sleep(refresh_wait).await;
            }
            Err(error) => {
                info!(
                    "Error getting token,{} trying again in {:?}",
                    error, config.auth_sleep
                );
                tokio::time::sleep(config.auth_sleep).await;
            }
        }
    }

    Ok(())
}

pub async fn test_connection(config: &TeamsConfig) -> Result<(), MyError> {
    info!("I should test the App connection + auth here");

    info!("Connection info is: {:?}", config);

    let client = Client::new();
    let issuer_url = IssuerUrl::new(config.auth_endpoint.as_str().to_owned())?;
    println!("Parsed Issuer URL: {}", issuer_url.as_str());
    // The crate automatically appends "/.well-known/openid-configuration"
    // or "/.well-known/oauth-authorization-server" when fetching.

    // 2. Discover the provider metadata asynchronously
    //    This function sends an HTTP GET request to the .well-known endpoint.
    //    It requires an async HTTP client function. We use the one provided
    //    by the `reqwest-client` feature.
    let provider_metadata = CoreProviderMetadata::discover_async(
        issuer_url, // The base URL of the provider
        &client,    // The HTTP client function
                    // If using openidconnect v2.x: reqwest::async_http_client
    )
    .await?;

    info!("Issuer: {:?}", provider_metadata.clone().issuer());

    let client_id = ClientId::new(config.id.clone());
    let client_secret = ClientSecret::new(config.secret.clone());

    let client_request = CoreClient::from_provider_metadata(
        provider_metadata.clone(), // Metadata fetched earlier
        client_id,
        Some(client_secret), // Needed later for code exchange
    );

    let token_response = client_request
        .exchange_client_credentials()
        .unwrap()
        .add_scope(Scope::new(
            "api://87de8678-74cc-4a80-8987-ce00baf25087/.default".to_owned(),
        ))
        .request_async(&client)
        .await
        .unwrap();
    info!("Token response: {:?}", token_response);
    info!("Access token: {:?}", token_response.access_token().secret());

    // Create a new request to call to the API endpoint with the access token
    let api_url = config.bot_endpoint.join("api/messages").unwrap();
    let access_token = token_response.access_token().secret();

    let response = client
        .post(api_url)
        .bearer_auth(access_token)
        .json(&Activity {
            r#type: "message".to_string(),
            id: "1".to_string(),
            timestamp: "2023-10-01T00:00:00Z".to_string(),
            local_timestamp: "2023-10-01T00:00:00Z".to_string(),
            local_timezone: "UTC".to_string(),
            service_url: config.bot_endpoint.to_string(),
            channel_id: "msteams".to_string(),
            from: User {
                id: "1".to_string(),
                name: "Bot".to_string(),
            },
            conversation: Conversation {
                id: "1".to_string(),
            },
            recipient: User {
                id: "2".to_string(),
                name: "User".to_string(),
            },
            text_format: "plain".to_string(),
            locale: "en-US".to_string(),
            text: "Hello, world!".to_string(),
            attachments: vec![],
            entities: None,
            channel_data: ChannelData {
                client_activity_id: "1".to_string(),
            },
        })
        .send()
        .await?;
    info!("API response: {:?}", response.status());
    if response.status().is_success() {
        info!("API call succeeded");
    } else {
        info!("API call failed: {:?}", response.text().await?);
    }

    //    let auth_url = provider_metadata.clone().token_endpoint().unwrap();

    //     let tenant_id = "1fd80b61-a805-4a57-879b-45ddb39a660d";

    //     let url = format!(
    //         "https://login.microsoftonline.com/{}/oauth2/v2.0/token",
    //         tenant_id
    //     );
    //     // let url = "https://informally-large-terrier.ngrok-free.app/api/messages".to_owned();
    //     let params = [
    //         ("client_id", config.id.clone()),
    //         ("client_secret", config.secret.clone()),
    //         ("grant_type", "client_credentials".to_owned()),
    //         ("scope", "api://87de8678-74cc-4a80-8987-ce00baf25087/.default".to_owned()),
    //     ];

    //     let resp = client.post(&url).form(&params).send().await.unwrap();

    //     println!("Got results : {:?}", resp.text().await);

    Ok(())
}
