use warp::Filter;

use crate::{botapi::handlers::message_post, MyState};

use super::with_state;

pub fn api(
    state: &MyState,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::path("messages").and(messages(state))
}

pub fn messages(
    state: &MyState,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    messages_get(state).or(message_post_structured(state))
    // .or(messages_post(state))
}

pub fn messages_get(
    state: &MyState,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::get().and_then(handlers::messages_get)
}

pub fn message_post_structured(
    state: &MyState,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::post()
        .and(warp::header::optional::<String>("authorization")) // Get Authorization header
        .and(warp::body::json()) // Expect JSON body, parse into Activity
        .and(with_state(state.clone()))
        .and_then(message_post)
    //     |auth: Option<String>, body: Message, state: MyState| async move {
    //         info!("Structured POST");
    //         info!("Authorization: {:?}", auth);
    //         info!("Body: {:?}", body);

    //         // info!("You sent a message: {}", body.activity.text);
    //         info!("Using teams as : {:?}", state.config.teams);

    //         Ok::<_, warp::Rejection>(warp::reply::json(&"POST messages"))
    //     },
    // )
}

// pub fn messages_post(
//     state: &MyState,
// ) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
//     warp::post()
//         .and(warp::header::optional::<String>("authorization")) // Get Authorization header
//         .and(warp::body::json()) // Expect JSON body, parse into Activity
//         .and_then(|auth: Option<String>, body: serde_json::Value| async move {
//             info!("Authorization: {:?}", auth);
//             info!("Body: {:?}", body);
//             Ok::<_, warp::Rejection>(warp::reply::json(&"POST messages"))
//         })
// }

mod handlers {
    use log::info;
    use warp::reply::Reply;

    pub async fn messages_get() -> Result<impl Reply, warp::Rejection> {
        info!("Messages");
        Ok(warp::reply::json(&"GET messages"))
    }
}
