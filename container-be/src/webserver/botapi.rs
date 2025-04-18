use warp::Filter;

use crate::MyState;

pub fn api(
    state: &MyState,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    messages(state)
}

pub fn messages(
    state: &MyState,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::path("messages")
        .and(warp::get())
        .and_then(handlers::message_get)
}


mod handlers {
    use log::info;
    use warp::reply::Reply;

    pub async fn message_get() -> Result<impl Reply, warp::Rejection> {
        info!("Messages");
        Ok(warp::reply::json(&"Hello teams!"))
    }

}
