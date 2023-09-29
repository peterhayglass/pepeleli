## pepeleli

pepeleli is an AI-powered chatbot designed to be able to participate in group conversations amongst multiple humans.

This is an experimental project and a very early work in progress.  Current functionality is very limited, but will continue to be extended.

## Current limitations

- This project is designed to offer a choice of AI model providers.  However the Ooba AI model provider has fallen behind the OpenAI provider in feature set and should be considered deprecated.  I will likely drop support for Ooba entirely in the near-ish future, replacing it with an implementation based on vLLM or perhaps another similar project (see https://github.com/vllm-project/vllm)

- The only supported user interface is Discord.  I plan to add support for other chat interfaces in the future, but this is not top priority.

- Conversation history is truncated when it becomes too long for the context window size, and all conversation history is lost when the bot restarts.

- The bot only responds when tagged, but the context used in generating a response includes all recent messages in the channel (not just messages where the bot was tagged.)


## Current priorities / objectives

- Explore ways to save (and make use of) much more conversation history than what fits in the context window size.  I plan to try storing conversation history as embeddings in a vector database. Then using a retrieval-augmented generation approach where we use semantic text search to retrieve relevant history to include in the prompt when it's time to generate a new response.

- Explore ways to make the bot independently decide when it "wants" to respond to the ongoing conversation, as opposed to the bot only responding when tagged by a user.  I expect this to be a pretty deep rabbit hole.