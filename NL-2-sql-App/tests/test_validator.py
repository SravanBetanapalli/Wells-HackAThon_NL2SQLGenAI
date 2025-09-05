import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.validator import ValidatorAgent


class TestValidatorAgent:
    """Test cases for ValidatorAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.schema_tables = {
            "customers": ["id", "first_name", "last_name", "email", "phone", "address", "date_of_birth", "gender", "national_id", "created_at", "updated_at", "branch_id"],
            "accounts": ["id", "customer_id", "account_number", "type", "balance", "opened_at", "interest_rate", "status", "branch_id", "created_at", "updated_at"],
            "branches": ["id", "name", "address", "city", "state", "zip_code", "manager_id", "created_at", "updated_at"],
            "employees": ["id", "branch_id", "name", "email", "phone", "position", "hire_date", "salary", "created_at", "updated_at"],
            "transactions": ["id", "account_id", "transaction_date", "amount", "type", "description", "status", "created_at", "updated_at", "employee_id"]
        }
        self.validator = ValidatorAgent(self.schema_tables)
    
    def test_init(self):
        """Test ValidatorAgent initialization"""
        assert hasattr(self.validator, 'validate')
        assert self.validator.schema_tables == self.schema_tables
    
    def test_validate_safe_query(self):
        """Test validation of safe SQL query"""
        sql = "SELECT * FROM customers LIMIT 10"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_ddl_operation(self):
        """Test validation of DDL operation"""
        sql = "DROP TABLE customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is False
        assert "DROP" in result["error"]
    
    def test_validate_dml_operation(self):
        """Test validation of DML operation"""
        sql = "DELETE FROM customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is False
        assert "DELETE" in result["error"]
    
    def test_validate_insert_operation(self):
        """Test validation of INSERT operation"""
        sql = "INSERT INTO customers (name, email) VALUES ('John', 'john@example.com')"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is False
        assert "INSERT" in result["error"]
    
    def test_validate_update_operation(self):
        """Test validation of UPDATE operation"""
        sql = "UPDATE customers SET name = 'John' WHERE id = 1"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is False
        assert "UPDATE" in result["error"]
    
    def test_validate_complex_safe_query(self):
        """Test validation of complex but safe query"""
        sql = """
        SELECT 
            c.first_name,
            c.last_name,
            COUNT(a.id) as account_count,
            AVG(a.balance) as avg_balance
        FROM customers c
        LEFT JOIN accounts a ON c.id = a.customer_id
        WHERE c.state = 'TX'
        GROUP BY c.id, c.first_name, c.last_name
        HAVING COUNT(a.id) > 1
        ORDER BY avg_balance DESC
        LIMIT 10
        """
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_comments(self):
        """Test validation of SQL with comments"""
        sql = "-- This is a comment\nSELECT * FROM customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_cte(self):
        """Test validation of SQL with CTE"""
        sql = """
        WITH high_balance AS (
            SELECT * FROM accounts WHERE balance > 10000
        )
        SELECT * FROM high_balance
        """
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_subqueries(self):
        """Test validation of SQL with subqueries"""
        sql = "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM accounts WHERE balance > 1000)"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_unions(self):
        """Test validation of SQL with UNION"""
        sql = "SELECT * FROM customers WHERE state = 'TX' UNION SELECT * FROM customers WHERE state = 'CA'"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_window_functions(self):
        """Test validation of SQL with window functions"""
        sql = "SELECT *, ROW_NUMBER() OVER (ORDER BY balance DESC) FROM accounts"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_case_statements(self):
        """Test validation of SQL with CASE statements"""
        sql = "SELECT CASE WHEN balance > 10000 THEN 'High' WHEN balance > 1000 THEN 'Medium' ELSE 'Low' END FROM accounts"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_aggregations(self):
        """Test validation of SQL with aggregations"""
        sql = "SELECT COUNT(*), SUM(balance), AVG(balance), MAX(balance), MIN(balance) FROM accounts"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_joins(self):
        """Test validation of SQL with various joins"""
        sql = """
        SELECT c.name, a.balance 
        FROM customers c 
        INNER JOIN accounts a ON c.id = a.customer_id
        LEFT JOIN branches b ON c.branch_id = b.id
        """
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
        assert "accounts" in result["tables_used"]
        assert "branches" in result["tables_used"]
    
    def test_validate_with_aliases(self):
        """Test validation of SQL with table and column aliases"""
        sql = "SELECT c.first_name AS name, a.balance AS bal FROM customers c JOIN accounts a ON c.id = a.customer_id"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_functions(self):
        """Test validation of SQL with built-in functions"""
        sql = "SELECT UPPER(first_name), LOWER(email), LENGTH(phone) FROM customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_date_functions(self):
        """Test validation of SQL with date functions"""
        sql = "SELECT DATE(created_at), DATETIME(updated_at) FROM customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_numeric_functions(self):
        """Test validation of SQL with numeric functions"""
        sql = "SELECT ROUND(balance, 2), ABS(amount), CEIL(interest_rate) FROM accounts"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_string_functions(self):
        """Test validation of SQL with string functions"""
        sql = "SELECT SUBSTR(first_name, 1, 3), REPLACE(email, '@', '[at]'), TRIM(phone) FROM customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_conditional_logic(self):
        """Test validation of SQL with conditional logic"""
        sql = "SELECT *, CASE WHEN balance > 10000 THEN 'High' ELSE 'Low' END as balance_category FROM accounts"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_group_by_having(self):
        """Test validation of SQL with GROUP BY and HAVING"""
        sql = "SELECT state, COUNT(*) FROM customers GROUP BY state HAVING COUNT(*) > 10"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_order_by_limit(self):
        """Test validation of SQL with ORDER BY and LIMIT"""
        sql = "SELECT * FROM customers ORDER BY created_at DESC LIMIT 20"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_distinct(self):
        """Test validation of SQL with DISTINCT"""
        sql = "SELECT DISTINCT state FROM customers"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_like_patterns(self):
        """Test validation of SQL with LIKE patterns"""
        sql = "SELECT * FROM customers WHERE email LIKE '%@gmail.com' OR phone LIKE '555-%'"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_in_clause(self):
        """Test validation of SQL with IN clause"""
        sql = "SELECT * FROM customers WHERE state IN ('TX', 'CA', 'NY')"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_between_clause(self):
        """Test validation of SQL with BETWEEN clause"""
        sql = "SELECT * FROM accounts WHERE balance BETWEEN 1000 AND 10000"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_null_checks(self):
        """Test validation of SQL with NULL checks"""
        sql = "SELECT * FROM customers WHERE phone IS NULL OR email IS NOT NULL"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_arithmetic_operations(self):
        """Test validation of SQL with arithmetic operations"""
        sql = "SELECT balance * 1.05 as new_balance, balance + 100 as bonus FROM accounts"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_with_logical_operators(self):
        """Test validation of SQL with logical operators"""
        sql = "SELECT * FROM customers WHERE (state = 'TX' OR state = 'CA') AND created_at > '2020-01-01'"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "customers" in result["tables_used"]
    
    def test_validate_with_comparison_operators(self):
        """Test validation of SQL with comparison operators"""
        sql = "SELECT * FROM accounts WHERE balance > 1000 AND balance <= 10000 AND type != 'savings'"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert "accounts" in result["tables_used"]
    
    def test_validate_invalid_sql(self):
        """Test validation of invalid SQL"""
        sql = "INVALID SQL STATEMENT"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is False
        assert "error" in result
    
    def test_validate_no_tables(self):
        """Test validation of SQL with no table references"""
        sql = "SELECT 1 as test"
        result = self.validator.validate(sql)
        
        assert result["is_valid"] is True
        assert result["tables_used"] == []
