import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.pipeline import NL2SQLPipeline


class TestNL2SQLPipeline:
    """Test cases for NL2SQLPipeline"""
    
    def setup_method(self):
        """Setup test fixtures"""
        with patch('backend.pipeline.PlannerAgent'), \
             patch('backend.pipeline.RetrieverAgent'), \
             patch('backend.pipeline.SQLGeneratorAgent'), \
             patch('backend.pipeline.ValidatorAgent'), \
             patch('backend.pipeline.ExecutorAgent'), \
             patch('backend.pipeline.SummarizerAgent'):
            
            self.pipeline = NL2SQLPipeline()
    
    def test_init(self):
        """Test NL2SQLPipeline initialization"""
        assert hasattr(self.pipeline, 'planner')
        assert hasattr(self.pipeline, 'retriever')
        assert hasattr(self.pipeline, 'sql_generator')
        assert hasattr(self.pipeline, 'validator')
        assert hasattr(self.pipeline, 'executor')
        assert hasattr(self.pipeline, 'summarizer')
    
    def test_process_query_basic(self):
        """Test basic query processing"""
        query = "Show me all customers"
        
        # Mock all agent responses
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers"],
            "capabilities": ["basic_query"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers..."],
            "value_hints": {"customers": {"state": ["TX", "CA"]}},
            "exemplars": ["SELECT * FROM customers"],
            "metadata": [{"table": "customers"}],
            "tables_found": ["customers"]
        }
        
        self.pipeline.sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM customers",
            "confidence": 0.9,
            "reasoning": "Simple query to get all customers"
        }
        
        self.pipeline.validator.validate.return_value = {
            "is_valid": True,
            "tables_used": ["customers"]
        }
        
        self.pipeline.executor.run_query.return_value = {
            "success": True,
            "data": [{"id": 1, "name": "John"}],
            "columns": ["id", "name"],
            "row_count": 1
        }
        
        self.pipeline.summarizer.summarize.return_value = {
            "summary": "Found 1 customer",
            "suggestions": ["Try filtering by state"]
        }
        
        result = self.pipeline.process_query(query)
        
        assert "planner_output" in result
        assert "retriever_output" in result
        assert "sql_generator_output" in result
        assert "validator_output" in result
        assert "executor_output" in result
        assert "summarizer_output" in result
        assert result["final_sql"] == "SELECT * FROM customers"
        assert result["success"] is True
    
    def test_process_query_with_error(self):
        """Test query processing with error"""
        query = "Invalid query"
        
        # Mock planner to raise an error
        self.pipeline.planner.analyze_query.side_effect = Exception("Planning failed")
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is False
        assert "error" in result
        assert "Planning failed" in result["error"]
    
    def test_process_query_sql_generation_failure(self):
        """Test query processing when SQL generation fails"""
        query = "Show me all customers"
        
        # Mock successful planning and retrieval
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers"],
            "capabilities": ["basic_query"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers..."],
            "value_hints": {},
            "exemplars": [],
            "metadata": [],
            "tables_found": ["customers"]
        }
        
        # Mock SQL generation failure
        self.pipeline.sql_generator.generate_sql.side_effect = Exception("SQL generation failed")
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is False
        assert "error" in result
        assert "SQL generation failed" in result["error"]
    
    def test_process_query_validation_failure(self):
        """Test query processing when validation fails"""
        query = "Show me all customers"
        
        # Mock successful planning, retrieval, and SQL generation
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers"],
            "capabilities": ["basic_query"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers..."],
            "value_hints": {},
            "exemplars": [],
            "metadata": [],
            "tables_found": ["customers"]
        }
        
        self.pipeline.sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM customers",
            "confidence": 0.9,
            "reasoning": "Simple query"
        }
        
        # Mock validation failure
        self.pipeline.validator.validate.return_value = {
            "is_valid": False,
            "error": "Invalid SQL syntax"
        }
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is False
        assert "error" in result
        assert "Invalid SQL syntax" in result["error"]
    
    def test_process_query_execution_failure(self):
        """Test query processing when execution fails"""
        query = "Show me all customers"
        
        # Mock successful planning, retrieval, SQL generation, and validation
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers"],
            "capabilities": ["basic_query"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers..."],
            "value_hints": {},
            "exemplars": [],
            "metadata": [],
            "tables_found": ["customers"]
        }
        
        self.pipeline.sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM customers",
            "confidence": 0.9,
            "reasoning": "Simple query"
        }
        
        self.pipeline.validator.validate.return_value = {
            "is_valid": True,
            "tables_used": ["customers"]
        }
        
        # Mock execution failure
        self.pipeline.executor.run_query.side_effect = Exception("Database error")
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is False
        assert "error" in result
        assert "Database error" in result["error"]
    
    def test_process_query_complex(self):
        """Test complex query processing with joins"""
        query = "Show me customers and their accounts with balance over 1000"
        
        # Mock complex analysis
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers", "accounts"],
            "capabilities": ["joins", "filtering"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers...", "CREATE TABLE accounts..."],
            "value_hints": {"accounts": {"balance": [1000, 2000, 3000]}},
            "exemplars": ["SELECT c.*, a.* FROM customers c JOIN accounts a ON c.id = a.customer_id"],
            "metadata": [{"table": "customers"}, {"table": "accounts"}],
            "tables_found": ["customers", "accounts"]
        }
        
        self.pipeline.sql_generator.generate_sql.return_value = {
            "sql": "SELECT c.*, a.* FROM customers c JOIN accounts a ON c.id = a.customer_id WHERE a.balance > 1000",
            "confidence": 0.8,
            "reasoning": "Join customers and accounts, filter by balance"
        }
        
        self.pipeline.validator.validate.return_value = {
            "is_valid": True,
            "tables_used": ["customers", "accounts"]
        }
        
        self.pipeline.executor.run_query.return_value = {
            "success": True,
            "data": [
                {"id": 1, "name": "John", "account_id": 1, "balance": 2000},
                {"id": 2, "name": "Jane", "account_id": 2, "balance": 3000}
            ],
            "columns": ["id", "name", "account_id", "balance"],
            "row_count": 2
        }
        
        self.pipeline.summarizer.summarize.return_value = {
            "summary": "Found 2 customers with accounts over $1000",
            "suggestions": ["Consider filtering by date range"]
        }
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is True
        assert "JOIN" in result["final_sql"]
        assert "WHERE" in result["final_sql"]
        assert result["executor_output"]["row_count"] == 2
    
    def test_process_query_aggregation(self):
        """Test query processing with aggregation"""
        query = "What is the total balance of all accounts?"
        
        # Mock aggregation analysis
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["accounts"],
            "capabilities": ["aggregation"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE accounts..."],
            "value_hints": {"accounts": {"balance": [1000, 2000, 3000]}},
            "exemplars": ["SELECT SUM(balance) FROM accounts"],
            "metadata": [{"table": "accounts"}],
            "tables_found": ["accounts"]
        }
        
        self.pipeline.sql_generator.generate_sql.return_value = {
            "sql": "SELECT SUM(balance) as total_balance FROM accounts",
            "confidence": 0.9,
            "reasoning": "Sum all account balances"
        }
        
        self.pipeline.validator.validate.return_value = {
            "is_valid": True,
            "tables_used": ["accounts"]
        }
        
        self.pipeline.executor.run_query.return_value = {
            "success": True,
            "data": [{"total_balance": 6000}],
            "columns": ["total_balance"],
            "row_count": 1
        }
        
        self.pipeline.summarizer.summarize.return_value = {
            "summary": "Total balance across all accounts is $6,000",
            "suggestions": ["Break down by account type"]
        }
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is True
        assert "SUM" in result["final_sql"]
        assert result["executor_output"]["data"][0]["total_balance"] == 6000
    
    def test_process_query_no_results(self):
        """Test query processing with no results"""
        query = "Show me customers from Mars"
        
        # Mock successful processing but no results
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers"],
            "capabilities": ["filtering"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers..."],
            "value_hints": {},
            "exemplars": [],
            "metadata": [],
            "tables_found": ["customers"]
        }
        
        self.pipeline.sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM customers WHERE planet = 'Mars'",
            "confidence": 0.7,
            "reasoning": "Filter by planet"
        }
        
        self.pipeline.validator.validate.return_value = {
            "is_valid": True,
            "tables_used": ["customers"]
        }
        
        self.pipeline.executor.run_query.return_value = {
            "success": True,
            "data": [],
            "columns": ["id", "name"],
            "row_count": 0
        }
        
        self.pipeline.summarizer.summarize.return_value = {
            "summary": "No customers found from Mars",
            "suggestions": ["Try a different planet or remove the filter"]
        }
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is True
        assert result["executor_output"]["row_count"] == 0
        assert "No customers found" in result["summarizer_output"]["summary"]
    
    def test_get_pipeline_status(self):
        """Test getting pipeline status"""
        status = self.pipeline.get_pipeline_status()
        
        assert "planner" in status
        assert "retriever" in status
        assert "sql_generator" in status
        assert "validator" in status
        assert "executor" in status
        assert "summarizer" in status
        assert all(status.values())  # All agents should be available
    
    def test_reset_pipeline(self):
        """Test resetting pipeline state"""
        # Set some state
        self.pipeline.last_query = "test query"
        self.pipeline.last_result = {"test": "result"}
        
        self.pipeline.reset_pipeline()
        
        assert self.pipeline.last_query is None
        assert self.pipeline.last_result is None
    
    def test_get_last_query(self):
        """Test getting last query"""
        query = "Show me all customers"
        self.pipeline.last_query = query
        
        result = self.pipeline.get_last_query()
        
        assert result == query
    
    def test_get_last_result(self):
        """Test getting last result"""
        result_data = {"success": True, "data": []}
        self.pipeline.last_result = result_data
        
        result = self.pipeline.get_last_result()
        
        assert result == result_data
    
    def test_validate_input(self):
        """Test input validation"""
        # Valid input
        assert self.pipeline.validate_input("Show me customers") is True
        
        # Invalid input
        assert self.pipeline.validate_input("") is False
        assert self.pipeline.validate_input(None) is False
        assert self.pipeline.validate_input(123) is False
    
    def test_process_query_with_retry(self):
        """Test query processing with retry logic"""
        query = "Show me all customers"
        
        # Mock first attempt to fail, second to succeed
        self.pipeline.sql_generator.generate_sql.side_effect = [
            Exception("First attempt failed"),
            {
                "sql": "SELECT * FROM customers",
                "confidence": 0.9,
                "reasoning": "Simple query"
            }
        ]
        
        # Mock other agents
        self.pipeline.planner.analyze_query.return_value = {
            "tables": ["customers"],
            "capabilities": ["basic_query"],
            "steps": ["plan", "retrieve", "generate", "validate", "execute"]
        }
        
        self.pipeline.retriever.fetch_schema_context.return_value = {
            "schema_context": ["CREATE TABLE customers..."],
            "value_hints": {},
            "exemplars": [],
            "metadata": [],
            "tables_found": ["customers"]
        }
        
        self.pipeline.validator.validate.return_value = {
            "is_valid": True,
            "tables_used": ["customers"]
        }
        
        self.pipeline.executor.run_query.return_value = {
            "success": True,
            "data": [{"id": 1, "name": "John"}],
            "columns": ["id", "name"],
            "row_count": 1
        }
        
        self.pipeline.summarizer.summarize.return_value = {
            "summary": "Found 1 customer",
            "suggestions": []
        }
        
        result = self.pipeline.process_query(query)
        
        assert result["success"] is True
        assert result["final_sql"] == "SELECT * FROM customers"
