import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.llm_prompt_builder import PromptingAgent


class TestPromptingAgent:
    """Test cases for PromptingAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.schema_context = {
            "tables": {
                "customers": {
                    "description": "Customer information",
                    "columns": {
                        "id": {"type": "INTEGER", "primary_key": True},
                        "first_name": {"type": "TEXT", "required": True},
                        "last_name": {"type": "TEXT", "required": True},
                        "email": {"type": "TEXT", "unique": True},
                        "balance": {"type": "REAL", "default": 0.0}
                    }
                },
                "accounts": {
                    "description": "Account information",
                    "columns": {
                        "id": {"type": "INTEGER", "primary_key": True},
                        "customer_id": {"type": "INTEGER", "foreign_key": "customers.id"},
                        "account_number": {"type": "TEXT", "unique": True},
                        "balance": {"type": "REAL", "default": 0.0}
                    }
                }
            }
        }
        
        self.value_hints = {
            "customers": {
                "first_name": ["John", "Jane", "Bob"],
                "state": ["TX", "CA", "NY"]
            },
            "accounts": {
                "type": ["checking", "savings", "credit"]
            }
        }
        
        self.exemplars = [
            "SELECT * FROM customers WHERE state = 'TX'",
            "SELECT c.first_name, c.last_name, a.balance FROM customers c JOIN accounts a ON c.id = a.customer_id",
            "SELECT COUNT(*) FROM accounts WHERE type = 'savings'"
        ]
        
        with patch('backend.llm_prompt_builder.LLMProvider'):
            self.prompting_agent = PromptingAgent()
    
    def test_init(self):
        """Test PromptingAgent initialization"""
        assert hasattr(self.prompting_agent, 'build_sql_prompt')
        assert hasattr(self.prompting_agent, 'build_summary_prompt')
    
    def test_build_sql_prompt_basic(self):
        """Test building basic SQL prompt"""
        nl_query = "Show me all customers"
        schema_context = "Table customers: id, first_name, last_name, email, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "SQL" in prompt
        assert "JSON" in prompt
    
    def test_build_sql_prompt_with_value_hints(self):
        """Test building SQL prompt with value hints"""
        nl_query = "Show me customers from Texas"
        schema_context = "Table customers: id, first_name, last_name, state"
        value_hints = {"customers": {"state": ["TX", "CA", "NY"]}}
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context, value_hints=value_hints)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "Texas" in prompt
        assert "TX" in prompt
    
    def test_build_sql_prompt_with_exemplars(self):
        """Test building SQL prompt with exemplars"""
        nl_query = "Show me customers and their accounts"
        schema_context = "Tables: customers, accounts"
        exemplars = ["SELECT c.*, a.* FROM customers c JOIN accounts a ON c.id = a.customer_id"]
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context, exemplars=exemplars)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "JOIN" in prompt
        assert "customers" in prompt
        assert "accounts" in prompt
    
    def test_build_sql_prompt_with_error_context(self):
        """Test building SQL prompt with error context"""
        nl_query = "Show me customers"
        schema_context = "Table customers: id, name"
        error_context = "Column 'name' does not exist. Available columns: id, first_name, last_name"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context, error_context=error_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "error" in prompt.lower()
        assert "first_name" in prompt
        assert "last_name" in prompt
    
    def test_build_sql_prompt_with_previous_attempts(self):
        """Test building SQL prompt with previous attempts"""
        nl_query = "Show me customers"
        schema_context = "Table customers: id, first_name, last_name"
        previous_attempts = [
            {"sql": "SELECT * FROM customers", "error": "No such column: *"},
            {"sql": "SELECT name FROM customers", "error": "No such column: name"}
        ]
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context, previous_attempts=previous_attempts)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "previous attempts" in prompt.lower()
        assert "SELECT * FROM customers" in prompt
        assert "No such column" in prompt
    
    def test_build_sql_prompt_with_aggregation(self):
        """Test building SQL prompt for aggregation queries"""
        nl_query = "What is the total balance of all accounts?"
        schema_context = "Table accounts: id, customer_id, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "total" in prompt.lower()
        assert "balance" in prompt
        assert "SUM" in prompt
    
    def test_build_sql_prompt_with_joins(self):
        """Test building SQL prompt for join queries"""
        nl_query = "Show me customers and their account balances"
        schema_context = "Tables: customers(id, name), accounts(customer_id, balance)"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "JOIN" in prompt
        assert "customer_id" in prompt
    
    def test_build_sql_prompt_with_filtering(self):
        """Test building SQL prompt for filtering queries"""
        nl_query = "Show me customers with balance over 1000"
        schema_context = "Table customers: id, first_name, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "WHERE" in prompt
        assert "balance > 1000" in prompt
    
    def test_build_sql_prompt_with_grouping(self):
        """Test building SQL prompt for grouping queries"""
        nl_query = "Show me customers by state"
        schema_context = "Table customers: id, first_name, state"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "GROUP BY" in prompt
        assert "state" in prompt
    
    def test_build_sql_prompt_with_ordering(self):
        """Test building SQL prompt for ordering queries"""
        nl_query = "Show me customers ordered by balance descending"
        schema_context = "Table customers: id, first_name, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "ORDER BY" in prompt
        assert "DESC" in prompt
    
    def test_build_sql_prompt_with_limit(self):
        """Test building SQL prompt for limited queries"""
        nl_query = "Show me top 10 customers by balance"
        schema_context = "Table customers: id, first_name, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "LIMIT" in prompt
        assert "10" in prompt
    
    def test_build_sql_prompt_with_subqueries(self):
        """Test building SQL prompt for subquery queries"""
        nl_query = "Show me customers who have accounts with balance over 5000"
        schema_context = "Tables: customers(id, name), accounts(customer_id, balance)"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "subquery" in prompt.lower() or "IN" in prompt
    
    def test_build_sql_prompt_with_case_statements(self):
        """Test building SQL prompt for case statement queries"""
        nl_query = "Show me customers with balance categories: High if > 10000, Medium if > 1000, Low otherwise"
        schema_context = "Table customers: id, first_name, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "CASE" in prompt
        assert "WHEN" in prompt
    
    def test_build_sql_prompt_with_window_functions(self):
        """Test building SQL prompt for window function queries"""
        nl_query = "Show me customers with their rank by balance"
        schema_context = "Table customers: id, first_name, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "RANK" in prompt or "window" in prompt.lower()
    
    def test_build_sql_prompt_with_cte(self):
        """Test building SQL prompt for CTE queries"""
        nl_query = "Show me customers with high balance accounts using a CTE"
        schema_context = "Tables: customers(id, name), accounts(customer_id, balance)"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "CTE" in prompt or "WITH" in prompt
    
    def test_build_sql_prompt_with_union(self):
        """Test building SQL prompt for union queries"""
        nl_query = "Show me all customers from Texas and California"
        schema_context = "Table customers: id, first_name, state"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "UNION" in prompt
    
    def test_build_sql_prompt_with_distinct(self):
        """Test building SQL prompt for distinct queries"""
        nl_query = "Show me unique customer states"
        schema_context = "Table customers: id, first_name, state"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "DISTINCT" in prompt
    
    def test_build_sql_prompt_with_functions(self):
        """Test building SQL prompt for function queries"""
        nl_query = "Show me customers with uppercase names"
        schema_context = "Table customers: id, first_name, last_name"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "UPPER" in prompt or "function" in prompt.lower()
    
    def test_build_sql_prompt_with_date_functions(self):
        """Test building SQL prompt for date function queries"""
        nl_query = "Show me customers created in 2024"
        schema_context = "Table customers: id, first_name, created_at"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "2024" in prompt
        assert "date" in prompt.lower()
    
    def test_build_sql_prompt_with_null_checks(self):
        """Test building SQL prompt for null check queries"""
        nl_query = "Show me customers with missing email addresses"
        schema_context = "Table customers: id, first_name, email"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "NULL" in prompt
        assert "IS NULL" in prompt
    
    def test_build_sql_prompt_with_like_patterns(self):
        """Test building SQL prompt for LIKE pattern queries"""
        nl_query = "Show me customers with email addresses ending in @gmail.com"
        schema_context = "Table customers: id, first_name, email"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "LIKE" in prompt
        assert "%@gmail.com" in prompt
    
    def test_build_sql_prompt_with_in_clause(self):
        """Test building SQL prompt for IN clause queries"""
        nl_query = "Show me customers from Texas, California, or New York"
        schema_context = "Table customers: id, first_name, state"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "IN" in prompt
        assert "('TX', 'CA', 'NY')" in prompt
    
    def test_build_sql_prompt_with_between_clause(self):
        """Test building SQL prompt for BETWEEN clause queries"""
        nl_query = "Show me customers with balance between 1000 and 10000"
        schema_context = "Table customers: id, first_name, balance"
        
        prompt = self.prompting_agent.build_sql_prompt(nl_query, schema_context)
        
        assert nl_query in prompt
        assert schema_context in prompt
        assert "BETWEEN" in prompt
        assert "1000" in prompt
        assert "10000" in prompt
    
    def test_build_summary_prompt_basic(self):
        """Test building basic summary prompt"""
        nl_query = "Show me all customers"
        execution_result = {
            "success": True,
            "data": [{"id": 1, "first_name": "John", "last_name": "Doe"}],
            "row_count": 1
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "John" in prompt
        assert "Doe" in prompt
        assert "summary" in prompt.lower()
    
    def test_build_summary_prompt_with_aggregation(self):
        """Test building summary prompt for aggregation results"""
        nl_query = "What is the total balance of all accounts?"
        execution_result = {
            "success": True,
            "data": [{"total_balance": 50000.0}],
            "row_count": 1
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "50000" in prompt
        assert "total" in prompt.lower()
    
    def test_build_summary_prompt_with_group_by(self):
        """Test building summary prompt for group by results"""
        nl_query = "Show me customers by state"
        execution_result = {
            "success": True,
            "data": [
                {"state": "TX", "count": 15},
                {"state": "CA", "count": 12},
                {"state": "NY", "count": 8}
            ],
            "row_count": 3
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "TX" in prompt
        assert "CA" in prompt
        assert "NY" in prompt
        assert "15" in prompt
        assert "12" in prompt
        assert "8" in prompt
    
    def test_build_summary_prompt_with_no_results(self):
        """Test building summary prompt for no results"""
        nl_query = "Show me customers from Mars"
        execution_result = {
            "success": True,
            "data": [],
            "row_count": 0
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "0" in prompt
        assert "no results" in prompt.lower()
    
    def test_build_summary_prompt_with_error(self):
        """Test building summary prompt for error results"""
        nl_query = "Show me invalid data"
        execution_result = {
            "success": False,
            "error": "Table does not exist"
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "error" in prompt.lower()
        assert "Table does not exist" in prompt
    
    def test_build_summary_prompt_with_large_dataset(self):
        """Test building summary prompt for large datasets"""
        nl_query = "Show me all transactions"
        execution_result = {
            "success": True,
            "data": [{"id": i, "amount": 100 + i} for i in range(1000)],
            "row_count": 1000
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "1000" in prompt
        assert "large" in prompt.lower() or "many" in prompt.lower()
    
    def test_build_summary_prompt_with_numeric_data(self):
        """Test building summary prompt for numeric data"""
        nl_query = "Show me account balances"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "balance": 5000.00},
                {"id": 2, "balance": 15000.50},
                {"id": 3, "balance": 2500.75}
            ],
            "row_count": 3
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "5000" in prompt
        assert "15000" in prompt
        assert "2500" in prompt
        assert "balance" in prompt.lower()
    
    def test_build_summary_prompt_with_date_data(self):
        """Test building summary prompt for date data"""
        nl_query = "Show me recent transactions"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "date": "2024-01-15", "amount": 100.00},
                {"id": 2, "date": "2024-01-16", "amount": 250.00}
            ],
            "row_count": 2
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "2024" in prompt
        assert "recent" in prompt.lower()
        assert "100" in prompt
        assert "250" in prompt
    
    def test_build_summary_prompt_with_text_data(self):
        """Test building summary prompt for text data"""
        nl_query = "Show me customer names"
        execution_result = {
            "success": True,
            "data": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Smith"}
            ],
            "row_count": 2
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "John" in prompt
        assert "Jane" in prompt
        assert "Doe" in prompt
        assert "Smith" in prompt
        assert "customer" in prompt.lower()
    
    def test_build_summary_prompt_with_boolean_data(self):
        """Test building summary prompt for boolean data"""
        nl_query = "Show me active accounts"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "active": True, "balance": 5000.00},
                {"id": 2, "active": False, "balance": 0.00}
            ],
            "row_count": 2
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "active" in prompt.lower()
        assert "True" in prompt
        assert "False" in prompt
    
    def test_build_summary_prompt_with_null_data(self):
        """Test building summary prompt for null data"""
        nl_query = "Show me customer phone numbers"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "phone": "555-1234"},
                {"id": 2, "phone": None}
            ],
            "row_count": 2
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "555-1234" in prompt
        assert "null" in prompt.lower() or "missing" in prompt.lower()
    
    def test_build_summary_prompt_with_complex_query(self):
        """Test building summary prompt for complex query results"""
        nl_query = "Show me customers with high balance accounts in Texas"
        execution_result = {
            "success": True,
            "data": [
                {"customer_name": "John Doe", "balance": 25000.00, "state": "TX"},
                {"customer_name": "Jane Smith", "balance": 30000.00, "state": "TX"}
            ],
            "row_count": 2
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "John Doe" in prompt
        assert "Jane Smith" in prompt
        assert "25000" in prompt
        assert "30000" in prompt
        assert "Texas" in prompt or "TX" in prompt
        assert "high balance" in prompt.lower()
    
    def test_build_summary_prompt_with_suggestions(self):
        """Test building summary prompt with suggestions"""
        nl_query = "Show me all customers"
        execution_result = {
            "success": True,
            "data": [{"id": 1, "first_name": "John", "last_name": "Doe"}],
            "row_count": 1
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "suggestion" in prompt.lower() or "insight" in prompt.lower()
    
    def test_build_summary_prompt_with_reasoning(self):
        """Test building summary prompt with reasoning"""
        nl_query = "Show me customers with balance over 10000"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "first_name": "John", "balance": 15000.00},
                {"id": 2, "first_name": "Jane", "balance": 20000.00}
            ],
            "row_count": 2
        }
        
        prompt = self.prompting_agent.build_summary_prompt(nl_query, execution_result)
        
        assert nl_query in prompt
        assert "reasoning" in prompt.lower() or "analysis" in prompt.lower()
        assert "15000" in prompt
        assert "20000" in prompt
        assert "high balance" in prompt.lower()
