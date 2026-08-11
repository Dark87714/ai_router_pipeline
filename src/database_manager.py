import chromadb

class DatabaseManager:
    """
    Handles local ChromaDB vector persistence and metadata indexing.
    """
    def __init__(self, db_path: str = "./db", collection_name: str = "logic_rules"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def clear_database(self):
        """
        Clears all stored rules from the local collection.
        """
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_logic_rule(
        self, 
        rule_id: str, 
        embedding: list[float], 
        raw_code: str, 
        ast_string: str, 
        metrics: dict = None
    ):
        metadata = {
            "raw_code": raw_code,
            "ast_string": ast_string
        }
        if metrics:
            metadata.update(metrics)

        self.collection.add(
            ids=[rule_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[ast_string]
        )

    def query_similar_logic(self, query_embedding: list[float], n_results: int = 1) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )