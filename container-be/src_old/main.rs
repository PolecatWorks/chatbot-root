use clap::Parser;
use polecatbot::{bot::get_conversations, CARGO_PKG_NAME, CARGO_PKG_VERSION};
use tokio::runtime::Runtime;



#[derive(Parser)]
#[command(name = "polecatbot")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(clap::Subcommand)]
enum Commands {
    Start,
    Version,
    ListConversations {
        #[arg(short, long)]
        bot_token: String,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Start => {
            println!("Start command executed");
        }
        Commands::Version => {
            println!("{} v{}", CARGO_PKG_NAME, CARGO_PKG_VERSION);
        }
        Commands::ListConversations { bot_token } => {
            let rt = Runtime::new().unwrap();
            rt.block_on(async {
                match get_conversations(&bot_token).await {
                    Ok(conversations) => {
                        for conversation in conversations {
                            println!("Conversation: {:?}", conversation);
                        }
                    }
                    Err(e) => {
                        eprintln!("Error fetching conversations: {}", e);
                    }
                }
            });
        }
    }
}
