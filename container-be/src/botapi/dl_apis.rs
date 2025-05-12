use std::collections::HashMap;

use reqwest::Client;
use tokio::sync::RwLock;
use url::Url;

use crate::error::MyError;

use super::directline::ConversationToken;

pub trait DlService {
    fn get_secret(&self) -> &str;
    fn get_base_url(&self) -> &Url;
    fn get_client(&self) -> &Client;
    fn get_conversations(&self) -> &RwLock<HashMap<String, ConversationToken>>;
}

pub(crate) trait DlApis {
    async fn send_activity(
        &self,
        conversation_id: &str,
        activity: serde_json::Value,
    ) -> Result<serde_json::Value, MyError>;
    async fn receive_activity(&self, conversation_id: &str) -> Result<serde_json::Value, MyError>;
    async fn reconnect_conversation(
        &self,
        conversation_id: &str,
    ) -> Result<ConversationToken, MyError>;
    async fn refresh_token(&self) -> Result<ConversationToken, MyError>;
    async fn create_token(&self) -> Result<ConversationToken, MyError>;
    async fn create_conversation(&self) -> Result<ConversationToken, MyError>;
}

pub struct DlApisImpl;

impl<T> DlApis for T
where
    T: DlService,
{
    /// Asynchronously creates a new conversation and returns a `ConversationToken`.
    ///
    /// This function performs the following steps:
    /// 1. Constructs the URL for creating a new conversation by appending
    ///    `"v3/directline/conversations"` to the base URL.
    /// 2. Sends a POST request to the constructed URL with a bearer token for authentication.
    /// 3. Checks the response for errors and deserializes the response body into a `ConversationToken`.
    /// 4. Stores the conversation token in the internal conversations map, keyed by the conversation ID.
    ///
    /// # Returns
    /// - `Ok(ConversationToken)` if the conversation is successfully created and stored.
    /// - `Err(MyError)` if any step in the process fails, such as URL construction, HTTP request,
    ///   or response deserialization.
    ///
    /// # Errors
    /// This function will return an error in the following cases:
    /// - If the base URL cannot be joined with the conversation path.
    /// - If the HTTP request fails or returns a non-success status code.
    /// - If the response body cannot be deserialized into a `ConversationToken`.
    ///
    /// # Examples
    /// ```rust
    /// let conversation_token = bot_api.create_conversation().await?;
    /// println!("Conversation ID: {}", conversation_token.conversation_id);
    /// ```
    async fn create_conversation(&self) -> Result<ConversationToken, MyError> {
        let conv_url = self.get_base_url().join("v3/directline/conversations")?;

        let conv_response = self
            .get_client()
            .post(conv_url)
            .bearer_auth(self.get_secret())
            .send()
            .await?
            .error_for_status()?;

        let conv = conv_response.json::<ConversationToken>().await?;

        self.get_conversations()
            .write()
            .await
            .insert(conv.conversation_id.clone(), conv.clone());

        Ok(conv)
    }

    /// Asynchronously creates a new Direct Line token and returns a `ConversationToken`.
    ///
    /// This function performs the following steps:
    /// 1. Constructs the URL for generating a new Direct Line token by appending
    ///    `"v3/directline/tokens/generate"` to the base URL.
    /// 2. Sends a POST request to the constructed URL with a bearer token for authentication.
    /// 3. Checks the response for errors and deserializes the response body into a `ConversationToken`.
    /// 4. Stores the token in the internal conversations map, keyed by the conversation ID.
    ///
    /// # Returns
    /// - `Ok(ConversationToken)` if the token is successfully created and stored.
    /// - `Err(MyError)` if any step in the process fails, such as URL construction, HTTP request,
    ///   or response deserialization.
    ///
    /// # Errors
    /// This function will return an error in the following cases:
    /// - If the base URL cannot be joined with the token generation path.
    /// - If the HTTP request fails or returns a non-success status code.
    /// - If the response body cannot be deserialized into a `ConversationToken`.
    ///
    /// # Examples
    /// ```rust
    /// let directline_token = bot_api.create_directline_token().await?;
    /// println!("Token: {}", directline_token.token);
    /// ```
    async fn create_token(&self) -> Result<ConversationToken, MyError> {
        let token_url = self.get_base_url().join("v3/directline/tokens/generate")?;

        let token_response = self
            .get_client()
            .post(token_url)
            .bearer_auth(self.get_secret())
            .send()
            .await?
            .error_for_status()?;

        let token = token_response.json::<ConversationToken>().await?;

        self.get_conversations()
            .write()
            .await
            .insert(token.conversation_id.clone(), token.clone());

        Ok(token)
    }

    /// Asynchronously refreshes an existing Direct Line token and returns an updated `ConversationToken`.
    ///
    /// This function performs the following steps:
    /// 1. Constructs the URL for refreshing the Direct Line token by appending
    ///    `"v3/directline/tokens/refresh"` to the base URL.
    /// 2. Sends a POST request to the constructed URL with a bearer token for authentication.
    /// 3. Checks the response for errors and deserializes the response body into a `ConversationToken`.
    /// 4. Updates the token in the internal conversations map, keyed by the conversation ID.
    ///
    /// # Returns
    /// - `Ok(ConversationToken)` if the token is successfully refreshed and updated.
    /// - `Err(MyError)` if any step in the process fails, such as URL construction, HTTP request,
    ///   or response deserialization.
    ///
    /// # Errors
    /// This function will return an error in the following cases:
    /// - If the base URL cannot be joined with the token refresh path.
    /// - If the HTTP request fails or returns a non-success status code.
    /// - If the response body cannot be deserialized into a `ConversationToken`.
    ///
    /// # Examples
    /// ```rust
    /// let refreshed_token = bot_api.refresh_directline_token().await?;
    /// println!("Refreshed Token: {}", refreshed_token.token);
    /// ```
    async fn refresh_token(&self) -> Result<ConversationToken, MyError> {
        let refresh_url = self.get_base_url().join("v3/directline/tokens/refresh")?;

        let refresh_response = self
            .get_client()
            .post(refresh_url)
            .bearer_auth(self.get_secret())
            .send()
            .await?
            .error_for_status()?;

        let refreshed_token = refresh_response.json::<ConversationToken>().await?;

        self.get_conversations().write().await.insert(
            refreshed_token.conversation_id.clone(),
            refreshed_token.clone(),
        );

        Ok(refreshed_token)
    }

    /// Asynchronously reconnects to an existing conversation using a conversation ID.
    ///
    /// This function performs the following steps:
    /// 1. Looks up the conversation token in the internal conversations map using the provided conversation ID.
    /// 2. If the conversation token exists, it returns the token.
    /// 3. If the conversation token does not exist, it returns an error.
    ///
    /// # Arguments
    /// - `conversation_id`: The ID of the conversation to reconnect to.
    ///
    /// # Returns
    /// - `Ok(ConversationToken)` if the conversation token is found.
    /// - `Err(MyError)` if the conversation token is not found.
    ///
    /// # Errors
    /// This function will return an error if the conversation ID is not found in the internal map.
    ///
    /// # Examples
    /// ```rust
    /// let conversation_token = bot_api.reconnect_conversation("conversation_id").await?;
    /// println!("Reconnected to Conversation ID: {}", conversation_token.conversation_id);
    /// ```
    async fn reconnect_conversation(
        &self,
        conversation_id: &str,
    ) -> Result<ConversationToken, MyError> {
        let conv_url = self
            .get_base_url()
            .join(&format!("v3/directline/conversations/{}", conversation_id))?;

        let response = self
            .get_client()
            .get(conv_url)
            .bearer_auth(&self.get_secret())
            .send()
            .await?
            .error_for_status()?;

        let conv = response.json::<ConversationToken>().await?;

        self.get_conversations()
            .write()
            .await
            .insert(conversation_id.to_owned(), conv.clone());

        Ok(conv)
    }

    /// Asynchronously receives an activity from a conversation.
    ///
    /// This function performs the following steps:
    /// 1. Constructs the URL for receiving activities by appending
    ///    `"v3/directline/conversations/{conversation_id}/activities"` to the base URL.
    /// 2. Sends a GET request to the constructed URL with a bearer token for authentication.
    /// 3. Checks the response for errors and deserializes the response body into a JSON value.
    ///
    /// # Arguments
    /// - `conversation_id`: The ID of the conversation to receive activities from.
    ///
    /// # Returns
    /// - `Ok(serde_json::Value)` if the activities are successfully received and deserialized.
    /// - `Err(MyError)` if any step in the process fails, such as URL construction, HTTP request,
    ///   or response deserialization.
    ///
    /// # Errors
    /// This function will return an error in the following cases:
    /// - If the base URL cannot be joined with the activities path.
    /// - If the HTTP request fails or returns a non-success status code.
    /// - If the response body cannot be deserialized into a JSON value.
    ///
    /// # Examples
    /// ```rust
    /// let activities = bot_api.receive_activity("conversation_id").await?;
    /// println!("Activities: {:?}", activities);
    /// ```
    async fn receive_activity(&self, conversation_id: &str) -> Result<serde_json::Value, MyError> {
        let activity_url = self.get_base_url().join(&format!(
            "v3/directline/conversations/{}/activities",
            conversation_id
        ))?;

        let response = self
            .get_client()
            .get(activity_url)
            .bearer_auth(self.get_secret())
            .send()
            .await?
            .error_for_status()?;

        let activities = response.json::<serde_json::Value>().await?;
        Ok(activities)
    }

    /// Asynchronously sends an activity to a conversation.
    ///
    /// This function performs the following steps:
    /// 1. Constructs the URL for sending activities by appending
    ///    `"v3/directline/conversations/{conversation_id}/activities"` to the base URL.
    /// 2. Sends a POST request to the constructed URL with a bearer token for authentication
    ///    and the activity payload as the request body.
    /// 3. Checks the response for errors and deserializes the response body into a JSON value.
    ///
    /// # Arguments
    /// - `conversation_id`: The ID of the conversation to send the activity to.
    /// - `activity`: The activity payload to send, represented as a `serde_json::Value`.
    ///
    /// # Returns
    /// - `Ok(serde_json::Value)` if the activity is successfully sent and the response is deserialized.
    /// - `Err(MyError)` if any step in the process fails, such as URL construction, HTTP request,
    ///   or response deserialization.
    ///
    /// # Errors
    /// This function will return an error in the following cases:
    /// - If the base URL cannot be joined with the activities path.
    /// - If the HTTP request fails or returns a non-success status code.
    /// - If the response body cannot be deserialized into a JSON value.
    ///
    /// # Examples
    /// ```rust
    /// let activity_payload = serde_json::json!({
    ///     "type": "message",
    ///     "text": "Hello, world!"
    /// });
    /// let response = bot_api.send_activity("conversation_id", activity_payload).await?;
    /// println!("Response: {:?}", response);
    /// ```
    async fn send_activity(
        &self,
        conversation_id: &str,
        activity: serde_json::Value,
    ) -> Result<serde_json::Value, MyError> {
        let activity_url = self.get_base_url().join(&format!(
            "v3/directline/conversations/{}/activities",
            conversation_id
        ))?;

        let response = self
            .get_client()
            .post(activity_url)
            .bearer_auth(self.get_secret())
            .json(&activity)
            .send()
            .await?
            .error_for_status()?;

        let result = response.json::<serde_json::Value>().await?;
        Ok(result)
    }
}
