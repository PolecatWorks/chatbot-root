use std::error::Error;
use std::collections::HashMap;
use reqwest::Client;
use serde::Deserialize;


#[derive(Deserialize, Debug)]
pub struct Conversation {
    pub id: String,
    pub name: Option<String>,
}

pub async fn get_conversations(bot_token: &str) -> Result<Vec<Conversation>, Box<dyn Error>> {
    let client = Client::new();
    let url = "https://smba.trafficmanager.net/amer/v3/conversations";

    let response = client
        .get(url)
        .bearer_auth(bot_token)
        .send()
        .await?;

    if response.status().is_success() {
        let conversations: Vec<Conversation> = response.json().await?;
        Ok(conversations)
    } else {
        Err(format!("Failed to fetch conversations: {}", response.status()).into())
    }
}

pub async fn generate_bot_token(app_id: &str, app_secret: &str) -> Result<String, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token";

    let mut params = HashMap::new();
    params.insert("grant_type", "client_credentials");
    params.insert("client_id", app_id);
    params.insert("client_secret", app_secret);
    params.insert("scope", "https://api.botframework.com/.default");

    let response = client
        .post(url)
        .form(&params)
        .send()
        .await?;

    if response.status().is_success() {
        let json: serde_json::Value = response.json().await?;
        if let Some(token) = json["access_token"].as_str() {
            return Ok(token.to_string());
        }
    }

    Err("Failed to generate bot token".into())
}
