import chromadb

client = chromadb.PersistentClient(path="../chromadb_data")
client.heartbeat()