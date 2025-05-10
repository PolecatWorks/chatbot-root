//! A Simple tutorial for Rust
//!
//! The tutorial covers how to setup a simple CLI program.
//! The program will allow the generation or a JSON schema generating data to match the schema.
//! Additionally the program can validate JSON loaded to the application or can run an http server to allow uploading of json file to the application.

use std::{
    collections::HashMap,
    ffi::c_void,
    sync::{Arc, Mutex},
    time::Duration,
};

use botapi::{config::BotApiConfig, BotApi};
use config::MyConfig;
use error::MyError;
use hamsrs::Hams;
use log::{debug, error, info};
use reqwest::Client;

use metrics::{prometheus_response, prometheus_response_free};
use persistence::PersistenceState;
use prometheus::{IntGauge, Registry};

use tokio::sync::RwLock;
use tokio_util::sync::CancellationToken;
use warp::reject::Reject;
use webserver::start_app_api;

pub mod botapi;
pub mod config;
pub mod error;
pub mod hams;
mod metrics;
pub mod persistence;
pub mod tokio_tools;
pub mod webserver;

/// Name of the Crate
pub const NAME: &str = env!("CARGO_PKG_NAME");
/// Version of the Crate
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

// Marker trait to indicate MyError is a planned rejection type
impl Reject for MyError {}

#[derive(Debug, Clone)]
pub struct MyState {
    config: MyConfig,
    db_state: PersistenceState,
    ct: CancellationToken,
    client: Client,
    pub count_good: Arc<Mutex<usize>>,
    pub count_fail: Arc<Mutex<usize>>,
    registry: Registry,
    hello_counter: IntGauge,
    pub bot_api: BotApi,
    pub conv_tokens: Arc<RwLock<HashMap<String, String>>>,
}

impl MyState {
    pub async fn new(config: &MyConfig, ct: CancellationToken) -> Result<MyState, MyError> {
        let db_state = PersistenceState::new(&config.persistence).await?;

        let client = Client::builder().timeout(Duration::from_secs(5)).build()?;

        let registry = Registry::new();

        let hello_counter = IntGauge::new("my_counter", "A counter for my application")?;

        registry.register(Box::new(hello_counter.clone()))?;

        Ok(MyState {
            config: config.clone(),
            db_state,
            ct,
            client: client.clone(),
            count_good: Arc::new(Mutex::new(0)),
            count_fail: Arc::new(Mutex::new(0)),
            registry,
            hello_counter,
            bot_api: BotApi::new(config.teams.clone(), client.clone()),
            conv_tokens: Arc::new(RwLock::new(HashMap::new())),
        })
    }
}

pub async fn service_cancellable(ct: CancellationToken, config: &MyConfig) -> Result<(), MyError> {
    let state = MyState::new(config, ct.clone()).await?;

    let pool_pg = state.db_state.pool_pg.clone();

    // Initialise liveness here

    let mut config = state.config.hams.clone();

    config.name = NAME.to_owned();
    config.version = VERSION.to_owned();

    let hams = Hams::new(ct.clone(), &config).unwrap();

    hams.register_prometheus(
        prometheus_response,
        prometheus_response_free,
        &state.registry as *const _ as *const c_void,
    )?;

    hams.start().unwrap();

    let state0 = state.clone();
    let access_auth_handler = tokio::spawn(async move { maintain_access_token(state0).await });

    let server = start_app_api(state.clone(), pool_pg, ct.clone());

    server.await;

    hams.stop().unwrap();
    hams.deregister_prometheus()?;

    ct.cancel();
    let _ = access_auth_handler.await?;

    Ok(())
}

pub async fn maintain_access_token(state: MyState) -> Result<(), MyError> {
    // maintain_app_token(state.clone()).await

    tokio::select! {
        _ = state.ct.cancelled() => {
            info!("Cancelled maintain_access_token");
        }
        _ = maintain_app_token(state.clone()) => {
            info!("Cancelled maintain_app_token");
        }
        // _ = maintain_direcline_token(&state, &state.config.teams, &state.client) => {
        //     info!("Cancelled maintain_direcline_token");
        // }
        // _ = maintain_webchat_token(&state, &state.config.teams, &state.client) => {
        //     info!("Cancelled maintain_webchat_token");
        // }
    }

    state.ct.cancel();
    Ok(())
}

pub async fn maintain_app_token(state: MyState) -> Result<(), MyError> {
    let config = state.config.teams.clone();

    // TODO: Setup liveness starting here

    let client = state.client.clone();

    // Fetch and parse the well-known endpoints to get issuer and token endpoint
    let well_known_url = config
        .auth_endpoint
        .join(".well-known/openid-configuration")?;
    debug!("Fetching well-known endpoints from: {}", well_known_url);
    let well_known_response = client.get(well_known_url).send().await?;

    debug!("Well-known response: {:?}", well_known_response);
    if !well_known_response.status().is_success() {
        error!(
            "Failed to fetch well-known endpoints: {}",
            well_known_response.status()
        );
        return Err(MyError::RequestTokenError(format!(
            "Failed to fetch well-known endpoints: {}",
            well_known_response.status()
        )));
    }

    let well_known_data: serde_json::Value = well_known_response.json().await?;
    let issuer = well_known_data["issuer"].as_str().ok_or_else(|| {
        MyError::RequestTokenError("Missing issuer in well-known endpoints".to_string())
    })?;
    let token_endpoint = well_known_data["token_endpoint"].as_str().ok_or_else(|| {
        MyError::RequestTokenError("Missing token endpoint in well-known endpoints".to_string())
    })?;

    info!("Discovered issuer: {}", issuer);
    info!("Discovered token endpoint: {}", token_endpoint);

    while !state.ct.is_cancelled() {
        // If we are cancelled, break out of the loop
        // Try to get the token. If we fail we will sleep for a bit and try again
        // If we get it then we will update the token object in the state AND update the liveness check AND we set the token to None

        // Replace the exchange_client_credentials logic with reqwest
        let token_response = client
            .post(token_endpoint)
            .form(&[
                ("grant_type", "client_credentials".to_string()),
                ("client_id", config.id.clone()),
                ("client_secret", config.secret.clone()),
                ("scope", config.scope.clone()),
            ])
            .send()
            .await;

        println!("Token response: {:?}", token_response);

        match token_response {
            Ok(response) if response.status().is_success() => {
                let token: serde_json::Value = response.json().await?;
                let access_token = token["access_token"]
                    .as_str()
                    .map(str::to_string)
                    .ok_or_else(|| {
                        MyError::RequestTokenError("Missing token in app token".to_string())
                    })?;

                info!("Access token updated successfully to be: {}", access_token);
                *state.bot_api.access_token.lock().await = Some(access_token);

                let expires_in = token["expires_in"]
                    .as_str()
                    .map(str::parse::<u64>)
                    .ok_or_else(|| {
                        MyError::RequestTokenError("Missing expires in app token".to_string())
                    })??;
                let refresh_wait = Duration::from_secs(expires_in) - config.auth_margin;

                info!("Access token expires in: {} seconds", expires_in);

                tokio::time::sleep(refresh_wait).await;
            }
            Ok(response) => {
                info!("Failed to fetch token: {}", response.status());
                tokio::time::sleep(config.auth_fail_sleep).await;
            }
            Err(error) => {
                info!("Error fetching token: {}", error);
                tokio::time::sleep(config.auth_fail_sleep).await;
            }
        }

        // update_webchat_token(&state, &config, &client).await;
        // update_direcline_token(&state, &config, &client).await;
        tokio::time::sleep(config.auth_fail_sleep).await;
    }

    Ok(())
}
