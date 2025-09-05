import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.sql_validator import SQLValidator


class TestSQLValidator:
    """Test cases for SQLValidator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = SQLValidator()
    
    def test_init(self):
        """Test SQLValidator initialization"""
        assert hasattr(self.validator, 'validate_sql')
        assert hasattr(self.validator, 'is_safe_query')
        assert hasattr(self.validator, 'extract_tables')
    
    def test_validate_sql_safe_query(self):
        """Test validating a safe SQL query"""
        sql = "SELECT * FROM customers WHERE id = 1"
        result = self.validator.validate_sql(sql)
        
        assert result["is_valid"] is True
        assert result["error"] is None
        assert "customers" in result["tables_used"]
    
    def test_validate_sql_ddl_operation(self):
        """Test validating DDL operations (should be unsafe)"""
        sql = "CREATE TABLE test (id INTEGER)"
        result = self.validator.validate_sql(sql)
        
        assert result["is_valid"] is False
        assert "CREATE" in result["error"]
    
    def test_validate_sql_dml_operation(self):
        """Test validating DML operations (should be unsafe)"""
        sql = "INSERT INTO customers (name) VALUES ('John')"
        result = self.validator.validate_sql(sql)
        
        assert result["is_valid"] is False
        assert "INSERT" in result["error"]
    
    def test_validate_sql_with_joins(self):
        """Test validating SQL with JOINs"""
        sql = "SELECT c.name, a.balance FROM customers c JOIN accounts a ON c.id = a.customer_id"
        result = self.validator.validate_sql(sql)
        
        assert result["is_valid"] is True
        assert result["error"] is None
        assert "customers" in result["tables_used"]
        assert "accounts" in result["tables_used"]
    
    def test_validate_sql_with_subqueries(self):
        """Test validating SQL with subqueries"""
        sql = "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM accounts WHERE balance > 1000)"
        result = self.validator.validate_sql(sql)
        
        assert result["is_valid"] is True
        assert result["error"] is None
        assert "customers" in result["tables_used"]
        assert "accounts" in result["tables_used"]
    
    def test_validate_sql_with_comments(self):
        """Test validating SQL with comments"""
        sql = """
        -- This is a comment
        SELECT * FROM customers 
        WHERE id = 1; -- Another comment
        """
        result = self.validator.validate_sql(sql)
        
        assert result["is_valid"] is True
        assert result["error"] is None
        assert "customers" in result["tables_used"]
    
    def test_validate_sql_with_empty_string(self):
        """Test validating SQL with empty string"""
        result = self.validator.validate_sql("")
        
        assert result["is_valid"] is False
        assert result["error"] is not None
    
    def test_is_safe_query_select(self):
        """Test is_safe_query with SELECT"""
        assert self.validator.is_safe_query("SELECT * FROM customers") is True
    
    def test_is_safe_query_create(self):
        """Test is_safe_query with CREATE"""
        assert self.validator.is_safe_query("CREATE TABLE test (id INTEGER)") is False
    
    def test_extract_tables_simple(self):
        """Test extract_tables with simple query"""
        sql = "SELECT * FROM customers"
        tables = self.validator.extract_tables(sql)
        assert "customers" in tables
    
    def test_extract_tables_with_joins(self):
        """Test extract_tables with JOINs"""
        sql = "SELECT * FROM customers c JOIN accounts a ON c.id = a.customer_id"
        tables = self.validator.extract_tables(sql)
        assert "customers" in tables
        assert "accounts" in tables
