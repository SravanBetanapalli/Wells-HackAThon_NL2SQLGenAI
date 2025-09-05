"""SQL Validator for testing and validating generated SQL queries"""
import logging
import sqlite3
import re
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class SQLValidator:
    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
        'MODIFY', 'RENAME', 'REPLACE', 'GRANT', 'REVOKE'
    }
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety and executability
        Returns: (is_valid, error_message)
        """
        sql = sql.strip()
        
        # Basic syntax check
        if not sql or not sql.strip():
            return False, "Empty SQL query"
            
        # Check for dangerous keywords
        sql_upper = sql.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in sql_upper:
                return False, f"Dangerous keyword '{keyword}' found in query"
                
        # Must be a SELECT query
        if not sql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
            
        # Check for proper table and column names
        if not self._has_valid_identifiers(sql):
            return False, "Invalid table or column names in query"
            
        # Try executing with LIMIT 1
        return self._test_execution(sql)

    def _has_valid_identifiers(self, sql: str) -> bool:
        """Check if SQL contains valid identifiers"""
        # Basic pattern for SQL identifiers
        identifier_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        
        # Extract all identifiers after FROM, JOIN, and table aliases
        tables = re.findall(r'(?:FROM|JOIN)\s+(' + identifier_pattern + ')', sql, re.IGNORECASE)
        if not tables:
            return False
            
        return True

    def _test_execution(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Test if SQL can be executed with LIMIT 1"""
        try:
            # Add LIMIT 1 if not present
            test_sql = sql.strip(';')  # Remove any trailing semicolon
            if 'LIMIT' not in test_sql.upper():
                test_sql += ' LIMIT 1'
            
            # Try executing
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(test_sql)
                cursor.fetchall()  # Actually execute the query
                return True, None
                
        except sqlite3.OperationalError as e:
            return False, f"SQL execution error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def get_error_context(self, error_msg: str) -> Dict[str, Any]:
        """Generate context about the error for LLM"""
        context = {
            "error_type": "unknown",
            "suggestion": "Please review the query syntax",
            "examples": []
        }
        
        error_lower = error_msg.lower()
        
        if "no such table" in error_lower:
            context.update({
                "error_type": "table_not_found",
                "suggestion": "Check table names and ensure they exist in the schema",
                "examples": [
                    "FROM customers c",
                    "JOIN accounts a ON c.id = a.customer_id"
                ]
            })
        elif "no such column" in error_lower:
            context.update({
                "error_type": "column_not_found",
                "suggestion": "Verify column names and table aliases",
                "examples": [
                    "SELECT c.first_name, c.last_name, a.account_number",
                    "WHERE a.status = 'active'"
                ]
            })
        elif "ambiguous" in error_lower:
            context.update({
                "error_type": "ambiguous_column",
                "suggestion": "Use table aliases to qualify column names",
                "examples": [
                    "SELECT c.id AS customer_id, a.id AS account_id",
                    "ON c.branch_id = b.id"
                ]
            })
        elif "syntax error" in error_lower:
            context.update({
                "error_type": "syntax_error",
                "suggestion": "Check SQL syntax, especially JOINs and conditions",
                "examples": [
                    "LEFT JOIN branches b ON c.branch_id = b.id",
                    "WHERE a.type IN ('checking', 'savings')"
                ]
            })
            
        return context
