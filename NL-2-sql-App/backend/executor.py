import sqlite3
from typing import Dict, Any
from .logger_config import log_agent_flow

class ExecutorAgent:
    def __init__(self, db_path="banking.db"):
        self.db_path = db_path

    @log_agent_flow("ExecutorAgent")
    def run_query(self, sql: str, limit: int = 100, validation_context: Dict[str, Any] = None):
        """Execute SQL query with optional validation context"""
        try:
            # Use validation context for better error handling
            if validation_context and not validation_context.get("is_valid"):
                return {"success": False, "error": "Query failed validation"}
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # results as dict-like
            cursor = conn.cursor()

            cursor.execute(sql)
            rows = cursor.fetchmany(limit)  # avoid huge dumps

            # Convert to list of dicts
            results = [dict(row) for row in rows]

            conn.close()

            if not results:
                return {"success": True, "results": [], "message": "No results found"}

            return {"success": True, "results": results}

        except sqlite3.Error as e:
            return {"success": False, "error": str(e)}
