## pepeleli

pepeleli is an AI-powered chatbot designed to be able to participate in group conversations amongst multiple humans.

This is an experimental project and a very early work in progress.  Current functionality is very limited, but will continue to be extended.

## Acknowledgements

This project makes use of [vLLM](https://github.com/vllm-project/vllm) to provide an option for self-hosted AI model inference.  I am incredibly grateful to the vLLM team for generously offering this excellent project under the Apache 2.0 license.  Thank you.

Within this repository vLLM exists as a submodule at `/src/vllm`, which points to my [fork](https://github.com/peterhayglass/vllm) of vLLM.  The vast majority of this code was written by the vLLM team.  I wrote a very small amount of additional code building on top of their work, as you can see in the commit history of my fork.

## Current limitations

- This project is designed to offer a choice of AI model providers.  Currently the OpenAI Instruct and vLLM providers are my focus and are equivalent in feature set.  The non-instruct OpenAI provider has fallen behind the others, and will probably be updated eventually but isn't a short term priority.

- The only supported user interface is Discord.  I plan to add support for other chat interfaces in the future, but this is not top priority.

- Conversation history is truncated when it becomes too long for the context window size.

- The bot only responds when tagged, but the context used in generating a response includes all recent messages in the channel (not just messages where the bot was tagged.)


## Current priorities / objectives

- Explore ways to save (and make use of) much more conversation history than what fits in the context window size.  I plan to try storing conversation history as embeddings in a vector database. Then using a retrieval-augmented generation approach where we use semantic text search to retrieve relevant history to include in the prompt when it's time to generate a new response.

- Explore ways to make the bot independently decide when it "wants" to respond to the ongoing conversation, as opposed to the bot only responding when tagged by a user.  I expect this to be a pretty deep rabbit hole.