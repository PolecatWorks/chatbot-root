use std::{collections::HashMap, sync::Arc};

use reqwest::Client;
use tokio::sync::RwLock;

use super::{config::DirectLineConfig, directline::ConversationToken, dl_apis::DlService};

#[derive(Debug, Clone)]
pub struct AbcWebChat {
    pub config: DirectLineConfig,
    pub client: reqwest::Client,
    pub conversations: Arc<RwLock<HashMap<String, ConversationToken>>>,
}

impl AbcWebChat {
    pub fn new(config: DirectLineConfig, client: Client) -> Self {
        let conversations = Arc::new(RwLock::new(HashMap::new()));
        AbcWebChat {
            config,
            client,
            conversations,
        }
    }
}

impl DlService for AbcWebChat {
    fn get_secret(&self) -> &str {
        &self.config.secret
    }

    fn get_base_url(&self) -> &url::Url {
        &self.config.base_url
    }

    fn get_client(&self) -> &Client {
        &self.client
    }

    fn get_conversations(&self) -> &RwLock<HashMap<String, ConversationToken>> {
        &self.conversations
    }
}
