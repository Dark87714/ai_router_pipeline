import os
import sys
from src.router_engine import RouterEngine
from src.compressor import CodebaseCompressor
from src.executor import LogicExecutor

def run_end_to_end_pipeline(repo_path: str):
    """
    End-to-End Pipeline Execution:
    1. Model 1 (Compressor) scans and indexes codebase AST logic into ChromaDB.
    2. Model 2 (Router) translates user intent into top-K structural matches.
    3. Model 3 (Executor) validates syntax, inspects parameters, and executes code.
    """
    repo_path = os.path.abspath(repo_path)
    
    if not os.path.exists(repo_path):
        print(f"Error: Path '{repo_path}' does not exist.")
        return

    print("==================================================")
    print("    AI ROUTER PIPELINE: END-TO-END SYSTEM (1-3)   ")
    print("==================================================")
    print(f"Target Repository: {repo_path}\n")

    router = RouterEngine(code_threshold=0.20, text_threshold=0.75)
    router.db.clear_database()
    compressor = CodebaseCompressor(router_engine=router)
    executor = LogicExecutor()

    print("[MODEL 1] Indexing codebase AST logic...")
    stats = compressor.compress_directory(repo_path)
    print(f"Scanned Files: {stats['scanned_files']} | Indexed Snippets: {stats['indexed_snippets']} | Failures: {stats['failed_snippets']}\n")

    if stats['indexed_snippets'] == 0:
        print("No snippets indexed. Exiting pipeline.")
        return

    print("[MODEL 2 & 3] Enter a plain English intent or code query (type 'exit' to quit):")

    while True:
        try:
            user_query = input("\nPipeline Query > ").strip()
            if not user_query:
                continue
            if user_query.lower() in ("exit", "quit"):
                print("Exiting pipeline loop.")
                break

            results = router.route_text_query(user_query, top_k=1)

            if results['matched']:
                top_match = results['matches'][0]
                print(f"\n[MODEL 2 ROUTE] Match Found!")
                print(f"Rule ID    : {top_match['rule_id']}")
                print(f"Confidence : {top_match['confidence']} (Distance: {top_match['distance']})")
                print(f"AST Metrics: {top_match['metrics']}")
                
                payload = executor.prepare_execution_payload(top_match)
                print(f"\n[MODEL 3 EXECUTOR] AST Syntax Status: {payload['syntax_status']}")
                print(f"Detected Parameters : {payload['required_params']}")
                
                print("\nCode Payload Preview:")
                print("-" * 40)
                print(payload['raw_code'])
                print("-" * 40)

                # Prompt user for optional execution test
                run_choice = input("\nExecute payload in sandboxed environment? (y/n): ").strip().lower()
                if run_choice == 'y':
                    exec_result = executor.execute_snippet(payload)
                    print("\n[EXECUTION RESULT]")
                    print(f"Success         : {exec_result['success']}")
                    print(f"Defined Symbols : {exec_result['defined_symbols']}")
                    if exec_result['output']:
                        print(f"Captured STDOUT :\n{exec_result['output']}")
                    if exec_result['error']:
                        print(f"Error           : {exec_result['error']}")

            else:
                print(f"\n[MODEL 2 ROUTE] NO_MATCH (Nearest distance exceeded threshold)")
                print(f"Raw Distances: {results.get('raw_distances')}")

        except KeyboardInterrupt:
            print("\nExiting pipeline loop.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_directory = sys.argv[1]
    else:
        target_directory = input("Enter path to repository folder (e.g. .): ").strip().strip('"').strip("'")

    if target_directory:
        run_end_to_end_pipeline(target_directory)
    else:
        print("No repository path provided.")