# Problem 1

initialize_chat_system
- in the chat command we are accessing the local chromadb!! this is not right, chat is interacting to the data through an MCP, there could be no chromadb installed on the system
- for the same reason, I think chromadb_path in the config file of chat is useless

# Problem 2
class LMStudioClient:
    def __init__(self, base_url: Optional[str], api_key: Optional[str]):
        if not base_url:
            raise AIProviderError("LM Studio base_url must be provided")

- why having an optional args that - if missing - creates an exception? at this point make it mandatory
- why api_key? unused! Unless you are aware of LMStudio asking for an API Key

# Problem 3
chat_completion
        if not messages:
            raise ValueError("Messages list cannot be empty")

- can really happen? messages is non mandatory and declared as a List

# Problem 4

AIProvider.chat_completion
	result = {'role': 'assistant'}

why this assignment when the message already contain these data? take them from it

# Problem 5
dynamic import litellm is useless, litellm is a mandatory dependency, move it at the beginning of the file, at module level

# Problem 6
during minerva index --dry-run
- /Users/michele/my-code/minerva/.venv/lib/python3.13/site-packages/httpx/_models.py:408: DeprecationWarning: Use 'content=<...>' to upload raw bytes/text content.
- /Users/michele/my-code/minerva/.venv/lib/python3.13/site-packages/litellm/llms/custom_httpx/async_client_cleanup.py:66: DeprecationWarning: There is no current event loop
      loop = asyncio.get_event_loop()
