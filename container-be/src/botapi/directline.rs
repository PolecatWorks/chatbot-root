use derive_builder::Builder;
use serde::{Deserialize, Serialize};
use url::Url;

#[derive(Debug, Deserialize, Clone)]
pub struct ConversationToken {
    #[serde(alias = "conversationId")]
    pub conversation_id: String,
    pub token: String,
    pub expires_in: i64,
    #[serde(alias = "streamUrl")]
    pub stream_url: String,
    #[serde(alias = "referenceGrammarId")]
    pub reference_grammar_id: String,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(tag = "type")]
pub enum BotActivity {
    // #[serde(alias = "message")]
    // // #[serde(rename="invoke")]
    // Activity(Activity),
    #[serde(alias = "conversationUpdate")]
    ConversationUpdate(ConversationUpdate),
    #[serde(rename = "message")]
    Message(Message),
}

impl BotActivity {
    pub fn conversation_id(&self) -> &str {
        match self {
            BotActivity::ConversationUpdate(activity) => &activity.conversation.id,
            BotActivity::Message(activity) => &activity.conversation.id,
        }
    }
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
    #[serde(skip_serializing_if = "Option::is_none")]
    pub locale: Option<String>,
    pub text: String,
    pub text_format: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input_hint: Option<String>,
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub local_timestamp: Option<String>,
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
    #[serde(skip_serializing_if = "Option::is_none")]
    pub client_timestamp: Option<String>,
}
