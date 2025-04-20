use serde::Deserialize;

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
