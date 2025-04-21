use log::info;
use openidconnect::{
    core::{CoreClient, CoreProviderMetadata},
    ClientId, ClientSecret, IssuerUrl, Scope,
};
use reqwest::Client;
use serde::Deserialize;
use url::Url;

use crate::{config::MyConfig, error::MyError};

#[derive(Debug, Deserialize)]
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

#[derive(Debug, Deserialize)]
pub struct User {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Deserialize)]
pub struct Conversation {
    pub id: String,
}

#[derive(Debug, Deserialize)]
pub struct Attachment {}

#[derive(Debug, Deserialize)]
pub struct Entity {
    pub r#type: String,
    pub requires_bot_state: Option<bool>,
    pub supports_listening: Option<bool>,
    pub supports_tts: Option<bool>,
}

#[derive(Debug, Deserialize)]
pub struct ChannelData {
    #[serde(rename = "clientActivityID")]
    pub client_activity_id: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct TeamsConfig {
    auth: Url,
    openid: Url,
    id: String,
    secret: String,
}

impl Default for TeamsConfig {
    fn default() -> Self {
        Self {
            auth: Url::parse("https://localhost").unwrap(),
            openid: Url::parse("https://localhost").unwrap(),
            id: Default::default(),
            secret: Default::default(),
        }
    }
}

pub async fn test_connection(config: &TeamsConfig) -> Result<(), MyError> {
    info!("I should test the App connection + auth here");

    info!("Connection info is: {:?}", config);

    let client = Client::new();

    let issuer_url = IssuerUrl::new(config.openid.as_str().to_owned())?;
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

    info!("Metadata = {:?}", provider_metadata);

    let client_id = ClientId::new(config.id.clone());
    let client_secret = ClientSecret::new(config.secret.clone());

    // let client_request = CoreClient::from_provider_metadata(
    //     provider_metadata, // Metadata fetched earlier
    //     client_id,
    //     Some(client_secret), // Needed later for code exchange
    // );

    // let ben = client_request
    //     .exchange_client_credentials().unwrap()
    //     .add_scope(Scope::new("read".to_string()))
    //     .request_async(&client).await.unwrap();

    let tenant_id = "1fd80b61-a805-4a57-879b-45ddb39a660d";

    let url = format!(
        "https://login.microsoftonline.com/{}/oauth2/v2.0/token",
        tenant_id
    );
    // let url = "https://informally-large-terrier.ngrok-free.app/api/messages".to_owned();
    let params = [
        ("client_id", config.id.clone()),
        ("client_secret", config.secret.clone()),
        ("grant_type", "client_credentials".to_owned()),
        ("scope", "https://api.botframework.com/.default".to_owned()),
    ];

    let resp = client.post(&url).form(&params).send().await.unwrap();

    println!("Got results : {:?}", resp);

    Ok(())
}
