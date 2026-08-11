import torch
from sentence_transformers import SentenceTransformer

class VectorEncoder:
    """
    Encodes abstracted AST strings into dense vector representations
    for the router to query.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Automatically select GPU if available, otherwise CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=self.device)

    def encode_logic(self, ast_string: str) -> list[float]:
        """
        Converts an AST logic string into a dense vector embedding list.
        """
        embedding = self.model.encode(ast_string, convert_to_numpy=True)
        return embedding.tolist()

if __name__ == "__main__":
    # Test vector generation with sample AST representation
    sample_ast = "Module([FunctionDef('FUNC', arguments([], [arg('VAR')]), [Return(Name('VAR', Load()))])])"
    
    print("Loading model and encoding AST...")
    encoder = VectorEncoder()
    vector = encoder.encode_logic(sample_ast)
    
    print(f"\nExecution Device: {encoder.device}")
    print(f"Embedding Dimensions: {len(vector)}")
    print(f"First 5 Vector Values: {vector[:5]}")