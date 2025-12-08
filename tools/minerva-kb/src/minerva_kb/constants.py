from pathlib import Path

HOME_DIR = Path.home()
MINERVA_DIR = HOME_DIR / ".minerva"
APPS_DIR = MINERVA_DIR / "apps"
MINERVA_KB_APP_DIR = APPS_DIR / "minerva-kb"
CHROMADB_DIR = MINERVA_DIR / "chromadb"

OPENAI_API_KEY_NAME = "OPENAI_API_KEY"
GEMINI_API_KEY_NAME = "GEMINI_API_KEY"

PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "ollama": "Ollama",
    "lmstudio": "LM Studio",
}

DEFAULT_PROVIDER_MODELS = {
    "openai": {
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "api_key_name": OPENAI_API_KEY_NAME,
    },
    "gemini": {
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
        "api_key_name": GEMINI_API_KEY_NAME,
    },
    "ollama": {
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "api_key_name": None,
    },
    "lmstudio": {
        "embedding_model": None,
        "llm_model": None,
        "api_key_name": None,
    },
}
