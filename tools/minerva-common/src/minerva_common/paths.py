from pathlib import Path

HOME_DIR = Path.home()
MINERVA_DIR = HOME_DIR / ".minerva"
CHROMADB_DIR = MINERVA_DIR / "chromadb"
SERVER_CONFIG_PATH = MINERVA_DIR / "server.json"
APPS_DIR = MINERVA_DIR / "apps"
