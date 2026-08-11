from src.ast_parser import parse_code_to_logic
from src.vector_encoder import VectorEncoder
from src.database_manager import DatabaseManager

class RouterEngine:
    """
    Model 2 (The Router): Translates code or natural language prompts into 
    dense logic space with dual-threshold filtering, top-K ranking, 
    and structural metric extraction.
    """
    def __init__(
        self, 
        db_path: str = "./db", 
        code_threshold: float = 0.20, 
        text_threshold: float = 0.75
    ):
        self.encoder = VectorEncoder()
        self.db = DatabaseManager(db_path=db_path)
        self.code_threshold = code_threshold
        self.text_threshold = text_threshold

    def index_code_snippet(self, rule_id: str, raw_code: str):
        """
        Parses raw python code into AST logic, generates structural descriptors 
        and complexity metrics, encodes vectors, and persists to ChromaDB.
        """
        ast_string, semantic_desc, metrics = parse_code_to_logic(raw_code)
        if ast_string.startswith("SYNTAX_ERROR"):
            raise ValueError(f"Failed to index snippet {rule_id}: {ast_string}")
        
        target_text = semantic_desc if semantic_desc else ast_string
        embedding = self.encoder.encode_logic(target_text)
        
        self.db.add_logic_rule(
            rule_id=rule_id,
            embedding=embedding,
            raw_code=raw_code,
            ast_string=ast_string,
            metrics=metrics
        )

    def route_code_query(self, raw_code: str, top_k: int = 3) -> dict:
        """
        Routes code snippet queries using strict code_threshold.
        """
        ast_string, semantic_desc, _ = parse_code_to_logic(raw_code)
        if ast_string.startswith("SYNTAX_ERROR"):
            return {"matched": False, "status": "SYNTAX_ERROR", "details": ast_string}

        target_text = semantic_desc if semantic_desc else ast_string
        query_embedding = self.encoder.encode_logic(target_text)
        return self._evaluate_matches(query_embedding, threshold=self.code_threshold, top_k=top_k)

    def route_text_query(self, user_prompt: str, top_k: int = 3) -> dict:
        """
        Routes natural language intent queries using text_threshold.
        """
        query_embedding = self.encoder.encode_logic(user_prompt)
        return self._evaluate_matches(query_embedding, threshold=self.text_threshold, top_k=top_k)

    def _evaluate_matches(self, query_embedding: list[float], threshold: float, top_k: int) -> dict:
        raw_results = self.db.query_similar_logic(query_embedding, n_results=top_k)

        if not raw_results['ids'] or not raw_results['ids'][0]:
            return {"matched": False, "status": "EMPTY_DATABASE", "matches": []}

        matches = []
        raw_distances = []
        for i in range(len(raw_results['ids'][0])):
            distance = raw_results['distances'][0][i]
            rule_id = raw_results['ids'][0][i]
            meta = raw_results['metadatas'][0][i]
            raw_distances.append((rule_id, round(distance, 4)))

            if distance <= threshold:
                confidence = max(0.0, min(1.0, 1.0 - distance))
                matches.append({
                    "rank": len(matches) + 1,
                    "rule_id": rule_id,
                    "confidence": round(confidence, 4),
                    "distance": round(distance, 4),
                    "metrics": {
                        "node_count": meta.get("node_count", 0),
                        "depth": meta.get("depth", 0),
                        "complexity": meta.get("complexity", 0)
                    },
                    "ast_string": meta.get("ast_string"),
                    "raw_code": meta.get("raw_code")
                })

        if not matches:
            return {
                "matched": False,
                "status": "NO_MATCH",
                "threshold_used": threshold,
                "raw_distances": raw_distances,
                "matches": []
            }

        return {
            "matched": True,
            "status": "MATCHES_FOUND",
            "threshold_used": threshold,
            "count": len(matches),
            "matches": matches
        }