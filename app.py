import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.router_engine import RouterEngine
from src.compressor import CodebaseCompressor
from src.executor import LogicExecutor

# Initialize FastAPI Application
app = FastAPI(
    title="AI Router Pipeline Microservice",
    description="3-Tier Codebase Compression, Vector Routing, and AST Logic Execution Engine",
    version="1.0.0"
)

# Global Pipeline Instances (Shared State)
router = RouterEngine(code_threshold=0.20, text_threshold=0.75)
compressor = CodebaseCompressor(router_engine=router)
executor = LogicExecutor()


# --- Pydantic Data Models ---

class CompressRequest(BaseModel):
    repo_path: str = Field(
        ..., 
        json_schema_extra={"example": "./"}, 
        description="Local path to repository folder to crawl and index."
    )
    clear_existing: bool = Field(
        default=True, 
        description="Wipe existing ChromaDB collection before indexing."
    )

class RouteRequest(BaseModel):
    query: str = Field(
        ..., 
        json_schema_extra={"example": "read file lines using context manager"}, 
        description="Code snippet or natural language prompt."
    )
    top_k: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="Number of top candidates to return."
    )
    mode: str = Field(
        default="text", 
        pattern="^(text|code)$", 
        description="Search mode: 'text' for natural language, 'code' for code snippets."
    )

class ExecuteRequest(BaseModel):
    match_payload: Dict[str, Any] = Field(
        ..., 
        description="Matched snippet dict returned from /route endpoint."
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional parameters to inject into the execution scope."
    )


# --- API Endpoints ---

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Service health and database state check."""
    return {
        "status": "online",
        "pipeline_version": "1.0.0",
        "chroma_db_path": router.db.collection_name
    }


@app.post("/compress", status_code=status.HTTP_200_OK)
def compress_codebase(req: CompressRequest):
    """
    Model 1 Endpoint: Crawls local repository, extracts AST code fragments, 
    and persists vectorized logic rules into ChromaDB.
    """
    abs_path = os.path.abspath(req.repo_path)
    if not os.path.exists(abs_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Target path '{req.repo_path}' does not exist on disk."
        )

    if req.clear_existing:
        router.db.clear_database()

    try:
        stats = compressor.compress_directory(abs_path)
        return {
            "status": "SUCCESS",
            "target_path": abs_path,
            "metrics": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compression failed: {str(e)}"
        )


@app.post("/route", status_code=status.HTTP_200_OK)
def route_intent(req: RouteRequest):
    """
    Model 2 Endpoint: Evaluates code or text intent against stored AST logic 
    and returns top-K structural matches.
    """
    if req.mode == "code":
        results = router.route_code_query(req.query, top_k=req.top_k)
    else:
        results = router.route_text_query(req.query, top_k=req.top_k)

    if not results.get("matched", False):
        return {
            "status": results.get("status", "NO_MATCH"),
            "query_mode": req.mode,
            "count": 0,
            "matches": [],
            "raw_distances": results.get("raw_distances", [])
        }

    return {
        "status": "MATCHES_FOUND",
        "query_mode": req.mode,
        "count": results["count"],
        "matches": results["matches"]
    }


@app.post("/execute", status_code=status.HTTP_200_OK)
def execute_logic(req: ExecuteRequest):
    """
    Model 3 Endpoint: Inspects AST function signatures, validates code syntax,
    binds parameters, and executes snippet in a sandboxed scope.
    """
    payload = executor.prepare_execution_payload(
        match_result=req.match_payload,
        params=req.params
    )

    if not payload["syntax_valid"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"AST Syntax Validation Failed: {payload['syntax_status']}"
        )

    exec_result = executor.execute_snippet(payload)
    
    return {
        "rule_id": payload["rule_id"],
        "syntax_status": payload["syntax_status"],
        "required_params": payload["required_params"],
        "execution_result": exec_result
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)