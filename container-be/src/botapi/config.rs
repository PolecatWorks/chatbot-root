use std::{collections::HashMap, sync::Arc, time::Duration};

use serde::Deserialize;
use tokio::sync::{Mutex, RwLock};
use url::Url;

#[derive(Deserialize, Debug, Clone)]
pub struct BotApiConfig {
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

impl Default for BotApiConfig {
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
                base_url: Url::parse("https://localhost").unwrap(),
            },
            auth_fail_sleep: Duration::from_secs(60),
            auth_margin: Duration::from_secs(60),
        }
    }
}

#[derive(Deserialize, Debug, Clone)]
pub struct WebChatConfig {
    pub secret: String, // Secret for WebChat integration
    pub token_url: Url, // URL to fetch WebChat token
}

#[derive(Deserialize, Debug, Clone)]
pub struct DirectLineConfig {
    pub secret: String, // Secret for DirectLine integration
    pub base_url: Url,  // URL to fetch DirectLine token
}
