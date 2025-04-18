


use thiserror::Error;
use std::io;

/// Error type for handling errors on Sample
#[derive(Error, Debug)]
pub enum MyError {
    #[error("General error `{0}`")]
    Message(&'static str),
    #[error("IO Error `{0}`")]
    Io(#[from] io::Error),
    #[error("Service Cancelled")]
    Cancelled,

}
