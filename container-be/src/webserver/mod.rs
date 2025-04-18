mod botapi;
mod hello;

use botapi::api;
use log::info;

use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::json;
use sqlx::{types::Decimal, Pool, Postgres};
use std::{convert::Infallible, net::SocketAddr, path::PathBuf};
use tokio_util::sync::CancellationToken;
use warp::{
    reject::Rejection,
    reply::{self, Reply},
    Filter,
};

use crate::{
    config::MyConfig, error::MyError, service_cancellable, tokio_tools::run_in_tokio, MyState, NAME,
};

use warp::hyper::StatusCode;

#[derive(Deserialize, Debug, Clone)]
pub struct WebServiceConfig {
    /// Prefix of the served API
    pub prefix: String,
    /// Hostname to start the webservice on
    /// This allows chainging to localhost for dev and 0.0.0.0 or specific address for deployment
    pub address: SocketAddr,
    pub forwarding_headers: Vec<String>,
}

impl Default for WebServiceConfig {
    fn default() -> Self {
        Self {
            prefix: "api".to_string(),
            address: "127.0.0.1:1234".parse().unwrap(),
            forwarding_headers: vec![],
        }
    }
}

pub async fn start_app_api(state: MyState, pool_pg: Pool<Postgres>, ct: CancellationToken) {
    let prefix = state.config.webservice.prefix.clone();

    // Setup http server
    let prefix_path = warp::path(prefix.clone());

    let weblog = warp::log(NAME);

    let service = warp::path("hello").and(hello::list(&state));

    let router = prefix_path
        .and(service)
        .or(warp::path("api").and(api(&state)))
        .recover(handle_rejection)
        .with(weblog);

    let (addr, server) = warp::serve(router)
        .bind_with_graceful_shutdown(state.config.webservice.address, async move {
            ct.cancelled().await
        });
    info!("Server started on port {}", addr);
    server.await;
}

fn with_db_pool_pg(
    state: Pool<Postgres>,
) -> impl Filter<Extract = (Pool<Postgres>,), Error = std::convert::Infallible> + Clone {
    warp::any().map(move || state.clone())
}

fn with_state(
    state: MyState,
) -> impl Filter<Extract = (MyState,), Error = std::convert::Infallible> + Clone {
    warp::any().map(move || state.clone())
}

fn with_pathbuf(
    pathbuf: PathBuf,
) -> impl Filter<Extract = (PathBuf,), Error = std::convert::Infallible> + Clone {
    warp::any().map(move || pathbuf.clone())
}

pub fn service_start(config: &MyConfig) -> Result<(), MyError> {
    let ct = CancellationToken::new();

    run_in_tokio("service", &config.runtime, service_cancellable(ct, config))
}

async fn handle_rejection(err: Rejection) -> std::result::Result<impl Reply, Infallible> {
    let (code, json_message) = if err.is_not_found() {
        (StatusCode::NOT_FOUND, reply::json(&"Not Found".to_string()))
    } else if err.find::<warp::reject::PayloadTooLarge>().is_some() {
        (
            StatusCode::BAD_REQUEST,
            reply::json(&"Payload too large".to_string()),
        )
    } else if let Some(e) = err.find::<MyError>() {
        match e {
            MyError::Message(detail) => {
                let error_message = json!({
                    "errorType": "Message",
                    "detail": detail,
                });

                (StatusCode::IM_A_TEAPOT, reply::json(&error_message))
            }
            MyError::Cancelled => todo!(),
            MyError::Serde(err) => todo!("Serde error: {}", err),
            MyError::Io(err) => todo!("IO error: {}", err),
            MyError::JsonValidation(errors) => {
                let myval = serde_json::json!( { "status:": "validation failed","errors": errors});

                (StatusCode::BAD_REQUEST, reply::json(&myval))
            }
            MyError::ValidationError() => todo!(),
            MyError::FigmentError(err) => todo!("Figment error: {}", err),
            MyError::SqlxError(err) => {
                println!("error is {}", err);
                match err {
                    sqlx::Error::RowNotFound => (
                        StatusCode::NOT_FOUND,
                        reply::json(&"Row not found".to_string()),
                    ),
                    _ => (
                        StatusCode::IM_A_TEAPOT,
                        reply::json(&"DB error".to_string()),
                    ),
                }
            }
            MyError::PreflightCheck => todo!(),
            MyError::ShutdownCheck => todo!(),
            MyError::SqlxMigrateError(er) => todo!("SQLX Migrate error: {}", er),
            MyError::PrometheusError(err) => todo!("Prometheus error: {}", err),
            MyError::HamsError(err) => todo!("HaMs error: {}", err),
            MyError::ParquetError(err) => todo!("Parquet error: {}", err),
        }
    } else {
        eprintln!("unhandled error: {:?}", err);
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            reply::json(&"Internal Server Error".to_string()),
        )
    };

    Ok(warp::reply::with_status(json_message, code))
}

#[cfg(test)]
mod tests {
    use sqlx::{PgPool, Row};

    #[sqlx::test(migrations = false)]
    async fn db_connectivity(pool: PgPool) -> sqlx::Result<()> {
        let foo = sqlx::query("SELECT 1").fetch_one(&pool).await?;

        assert_eq!(foo.get::<i32, _>(0), 1);

        Ok(())
    }
}

#[cfg(test)]
mod test {
    use super::*;
}
