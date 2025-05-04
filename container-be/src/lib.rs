//! A Simple tutorial for Rust
//!
//! The tutorial covers how to setup a simple CLI program.
//! The program will allow the generation or a JSON schema generating data to match the schema.
//! Additionally the program can validate JSON loaded to the application or can run an http server to allow uploading of json file to the application.

use std::{
    ffi::c_void,
    sync::{Arc, Mutex},
    time::Duration,
};

use botapi::{maintain_access_token, Teams};
use config::MyConfig;
use error::MyError;
use hamsrs::Hams;
use reqwest::Client;

use log::info;
use metrics::{prometheus_response, prometheus_response_free};
use persistence::PersistenceState;
use prometheus::{IntGauge, Registry};

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
    pub teams: Teams,
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
            client,
            count_good: Arc::new(Mutex::new(0)),
            count_fail: Arc::new(Mutex::new(0)),
            registry,
            hello_counter,
            teams: Teams::default(),
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
