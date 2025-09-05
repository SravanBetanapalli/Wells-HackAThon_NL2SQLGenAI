"""Test cases for SQL Generator"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.sql_generator import SQLGeneratorAgent
from backend.llm_prompt_builder import PromptingAgent
from backend.llm_provider import OpenAIProvider


class TestSQLGeneratorAgent:
    """Test cases for SQLGeneratorAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        with patch('backend.sql_generator.PromptingAgent'), \
             patch('backend.sql_generator.OpenAIProvider'):
            self.sql_generator = SQLGeneratorAgent()
    
    def test_init(self):
        """Test SQLGeneratorAgent initialization"""
        assert hasattr(self.sql_generator, 'prompting_agent')
        assert hasattr(self.sql_generator, 'llm_provider')
    
    @patch('backend.sql_generator.PromptingAgent')
    @patch('backend.sql_generator.OpenAIProvider')
    def test_generate_sql_basic(self, mock_llm_provider, mock_prompting_agent):
        """Test basic SQL generation"""
        # Mock LLM response
        mock_llm_provider.return_value.generate_text.return_value = {
            "SQLQuery": "SELECT * FROM customers LIMIT 10",
            "Suggestion": "This query retrieves all customers"
        }
        
        # Mock prompt building
        mock_prompting_agent.return_value.build_prompt.return_value = "Test prompt"
        
        query = "Show me all customers"
        context = {"tables": ["customers"], "schema_context": []}
        
        result = self.sql_generator.generate_sql(query, context)
        
        assert "sql" in result
        assert "suggestion" in result
        assert result["sql"] == "SELECT * FROM customers LIMIT 10"
    
    @patch('backend.sql_generator.PromptingAgent')
    @patch('backend.sql_generator.OpenAIProvider')
    def test_generate_sql_with_error_correction(self, mock_llm_provider, mock_prompting_agent):
        """Test SQL generation with error correction"""
        # Mock first attempt - error
        mock_llm_provider.return_value.generate_text.side_effect = [
            {"SQLQuery": "SELECT * FROM nonexistent_table", "Suggestion": "Wrong query"},
            {"SQLQuery": "SELECT * FROM customers", "Suggestion": "Corrected query"}
        ]
        
        mock_prompting_agent.return_value.build_prompt.return_value = "Test prompt"
        
        query = "Show me all customers"
        context = {"tables": ["customers"], "schema_context": []}
        
        result = self.sql_generator.generate_sql(query, context)
        
        assert "sql" in result
        assert result["sql"] == "SELECT * FROM customers"
    
    def test_extract_problematic_columns(self):
        """Test problematic column extraction"""
        error_message = "no such column: invalid_column"
        columns = self.sql_generator._extract_problematic_columns(error_message)
        
        assert "invalid_column" in columns
    
    def test_extract_problematic_columns_no_match(self):
        """Test problematic column extraction with no match"""
        error_message = "syntax error"
        columns = self.sql_generator._extract_problematic_columns(error_message)
        
        assert columns == []
    
    def test_create_simplified_query(self):
        """Test simplified query creation"""
        original_sql = "SELECT id, name, email, phone FROM customers WHERE balance > 1000"
        problematic_columns = ["phone", "balance"]
        
        simplified_sql = self.sql_generator._create_simplified_query(original_sql, problematic_columns)
        
        assert "phone" not in simplified_sql
        assert "balance" not in simplified_sql
        assert "id" in simplified_sql
        assert "name" in simplified_sql
    
    @patch('backend.sql_generator.sqlite3')
    def test_test_sql_execution(self, mock_sqlite3):
        """Test SQL execution testing"""
        # Mock successful execution
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT * FROM customers LIMIT 1"
        result = self.sql_generator._test_sql_execution(sql)
        
        assert result is True
    
    @patch('backend.sql_generator.sqlite3')
    def test_test_sql_execution_error(self, mock_sqlite3):
        """Test SQL execution testing with error"""
        # Mock execution error
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("SQL error")
        mock_connection.cursor.return_value = mock_cursor
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT * FROM nonexistent_table"
        result = self.sql_generator._test_sql_execution(sql)
        
        assert result is False
    
    def test_validate_sql_safety(self):
        """Test SQL safety validation"""
        safe_sql = "SELECT * FROM customers"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_ddl(self):
        """Test SQL safety validation with DDL"""
        unsafe_sql = "DROP TABLE customers"
        result = self.sql_generator._validate_sql_safety(unsafe_sql)
        
        assert result is False
    
    def test_validate_sql_safety_dml(self):
        """Test SQL safety validation with DML"""
        unsafe_sql = "DELETE FROM customers"
        result = self.sql_generator._validate_sql_safety(unsafe_sql)
        
        assert result is False
    
    def test_validate_sql_safety_insert(self):
        """Test SQL safety validation with INSERT"""
        unsafe_sql = "INSERT INTO customers VALUES (1, 'John')"
        result = self.sql_generator._validate_sql_safety(unsafe_sql)
        
        assert result is False
    
    def test_validate_sql_safety_update(self):
        """Test SQL safety validation with UPDATE"""
        unsafe_sql = "UPDATE customers SET name = 'John'"
        result = self.sql_generator._validate_sql_safety(unsafe_sql)
        
        assert result is False
    
    def test_validate_sql_safety_union(self):
        """Test SQL safety validation with UNION"""
        safe_sql = "SELECT * FROM customers UNION SELECT * FROM accounts"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_subquery(self):
        """Test SQL safety validation with subquery"""
        safe_sql = "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM accounts)"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_case(self):
        """Test SQL safety validation with CASE"""
        safe_sql = "SELECT CASE WHEN balance > 1000 THEN 'High' ELSE 'Low' END FROM accounts"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_aggregation(self):
        """Test SQL safety validation with aggregation"""
        safe_sql = "SELECT COUNT(*), AVG(balance) FROM accounts"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_joins(self):
        """Test SQL safety validation with joins"""
        safe_sql = "SELECT c.name, a.balance FROM customers c JOIN accounts a ON c.id = a.customer_id"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_window(self):
        """Test SQL safety validation with window functions"""
        safe_sql = "SELECT *, ROW_NUMBER() OVER (ORDER BY balance) FROM accounts"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_cte(self):
        """Test SQL safety validation with CTE"""
        safe_sql = "WITH high_balance AS (SELECT * FROM accounts WHERE balance > 1000) SELECT * FROM high_balance"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_comments(self):
        """Test SQL safety validation with comments"""
        safe_sql = "-- This is a comment\nSELECT * FROM customers"
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
    
    def test_validate_sql_safety_multiline(self):
        """Test SQL safety validation with multiline"""
        safe_sql = """
        SELECT 
            c.name,
            a.balance
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        WHERE a.balance > 1000
        """
        result = self.sql_generator._validate_sql_safety(safe_sql)
        
        assert result is True
