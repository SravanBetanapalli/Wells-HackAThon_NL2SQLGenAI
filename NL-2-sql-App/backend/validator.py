"""SQL Validator Agent"""
import sqlparse
from typing import Dict, Any
from .logger_config import log_agent_flow

class ValidatorAgent:
    def __init__(self, schema_tables: dict):
        """
        schema_tables = {
          "customers": ["id", "first_name", "last_name", "gender", ...],
          "accounts": ["id", "customer_id", "type", "balance", ...],
          ...
        }
        """
        self.schema_tables = schema_tables

    @log_agent_flow("ValidatorAgent")
    def validate(self, sql: str) -> Dict[str, Any]:
        """Validate SQL query for safety and correctness"""
        # Normalize SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return {
                "is_valid": False,
                "error": "Invalid SQL syntax"
            }

        stmt = parsed[0]
        tokens = [t.value.upper() for t in stmt.tokens if not t.is_whitespace]

        # 1. Only allow SELECT
        if "SELECT" not in tokens[0]:
            return {
                "is_valid": False,
                "error": "Only SELECT statements are allowed"
            }

        # 2. Block dangerous keywords
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]
        for word in forbidden:
            if word in tokens:
                return {
                    "is_valid": False,
                    "error": f"Forbidden operation detected: {word}"
                }

        # 3. Basic table validation
        sql_str = sql.upper()
        
        # Check if any known table is mentioned
        tables_found = []
        for table in self.schema_tables:
            if table.upper() in sql_str:
                tables_found.append(table)
        
        if not tables_found:
            return {
                "is_valid": True,  # Allow general queries like "SELECT 1"
                "warning": "No known tables referenced",
                "tables_used": []
            }
        
        return {
            "is_valid": True,
            "tables_used": tables_found
        }