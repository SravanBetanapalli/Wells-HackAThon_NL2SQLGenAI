import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.executor import ExecutorAgent


class TestExecutorAgent:
    """Test cases for ExecutorAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.executor = ExecutorAgent()
    
    def test_init(self):
        """Test ExecutorAgent initialization"""
        assert hasattr(self.executor, 'run_query')
    
    @patch('backend.executor.sqlite3')
    def test_run_query_success(self, mock_sqlite3):
        """Test successful query execution"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.fetchall.return_value = [
            (1, 'John', 'Doe', 'john@example.com'),
            (2, 'Jane', 'Smith', 'jane@example.com')
        ]
        mock_cursor.description = [
            ('id',), ('first_name',), ('last_name',), ('email',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT id, first_name, last_name, email FROM customers LIMIT 2"
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert "data" in result
        assert "columns" in result
        assert "row_count" in result
        assert result["row_count"] == 2
        assert len(result["data"]) == 2
        assert result["columns"] == ['id', 'first_name', 'last_name', 'email']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_no_results(self, mock_sqlite3):
        """Test query execution with no results"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock empty results
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [
            ('id',), ('first_name',), ('last_name',), ('email',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT * FROM customers WHERE id = 999"
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["data"] == []
        assert result["row_count"] == 0
        assert result["columns"] == ['id', 'first_name', 'last_name', 'email']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_database_error(self, mock_sqlite3):
        """Test query execution with database error"""
        # Mock database error
        mock_sqlite3.connect.side_effect = Exception("Database connection failed")
        
        sql = "SELECT * FROM customers"
        result = self.executor.run_query(sql)
        
        assert result["success"] is False
        assert "error" in result
        assert "Database connection failed" in result["error"]
    
    @patch('backend.executor.sqlite3')
    def test_run_query_sql_error(self, mock_sqlite3):
        """Test query execution with SQL error"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock SQL error
        mock_cursor.execute.side_effect = Exception("no such table: nonexistent")
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT * FROM nonexistent_table"
        result = self.executor.run_query(sql)
        
        assert result["success"] is False
        assert "error" in result
        assert "no such table" in result["error"]
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_aggregation(self, mock_sqlite3):
        """Test query execution with aggregation functions"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock aggregation results
        mock_cursor.fetchall.return_value = [
            ('TX', 150, 50000.50),
            ('CA', 200, 75000.25)
        ]
        mock_cursor.description = [
            ('state',), ('customer_count',), ('total_balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT state, COUNT(*) as customer_count, SUM(balance) as total_balance FROM customers GROUP BY state"
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['state', 'customer_count', 'total_balance']
        assert result["data"][0][0] == 'TX'
        assert result["data"][0][1] == 150
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_joins(self, mock_sqlite3):
        """Test query execution with JOIN operations"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock join results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 'checking', 5000.00),
            ('Jane', 'Smith', 'savings', 10000.00)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('account_type',), ('balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT c.first_name, c.last_name, a.type as account_type, a.balance
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'account_type', 'balance']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_subquery(self, mock_sqlite3):
        """Test query execution with subquery"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock subquery results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 5000.00),
            ('Jane', 'Smith', 10000.00)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, balance
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        WHERE a.balance > (SELECT AVG(balance) FROM accounts)
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'balance']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_cte(self, mock_sqlite3):
        """Test query execution with Common Table Expression"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock CTE results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 5000.00),
            ('Jane', 'Smith', 10000.00)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        WITH high_balance AS (
            SELECT customer_id, balance
            FROM accounts
            WHERE balance > 5000
        )
        SELECT c.first_name, c.last_name, h.balance
        FROM customers c
        JOIN high_balance h ON c.id = h.customer_id
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'balance']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_window_functions(self, mock_sqlite3):
        """Test query execution with window functions"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock window function results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 5000.00, 1),
            ('Jane', 'Smith', 10000.00, 2)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('balance',), ('rank',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, balance,
               ROW_NUMBER() OVER (ORDER BY balance DESC) as rank
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'balance', 'rank']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_case_statements(self, mock_sqlite3):
        """Test query execution with CASE statements"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock CASE statement results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 5000.00, 'Medium'),
            ('Jane', 'Smith', 10000.00, 'High')
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('balance',), ('category',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, balance,
               CASE 
                   WHEN balance > 10000 THEN 'High'
                   WHEN balance > 5000 THEN 'Medium'
                   ELSE 'Low'
               END as category
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'balance', 'category']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_union(self, mock_sqlite3):
        """Test query execution with UNION"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock UNION results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 'TX'),
            ('Jane', 'Smith', 'CA'),
            ('Bob', 'Johnson', 'NY')
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('state',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, state FROM customers WHERE state = 'TX'
        UNION
        SELECT first_name, last_name, state FROM customers WHERE state = 'CA'
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 3
        assert result["columns"] == ['first_name', 'last_name', 'state']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_limit_offset(self, mock_sqlite3):
        """Test query execution with LIMIT and OFFSET"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock paginated results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe'),
            ('Jane', 'Smith')
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT first_name, last_name FROM customers ORDER BY id LIMIT 2 OFFSET 0"
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_distinct(self, mock_sqlite3):
        """Test query execution with DISTINCT"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock DISTINCT results
        mock_cursor.fetchall.return_value = [
            ('TX',),
            ('CA',),
            ('NY',)
        ]
        mock_cursor.description = [
            ('state',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = "SELECT DISTINCT state FROM customers ORDER BY state"
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 3
        assert result["columns"] == ['state']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_functions(self, mock_sqlite3):
        """Test query execution with built-in functions"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock function results
        mock_cursor.fetchall.return_value = [
            ('JOHN DOE', 'john@example.com', 4)
        ]
        mock_cursor.description = [
            ('full_name',), ('email',), ('name_length',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT 
            UPPER(first_name || ' ' || last_name) as full_name,
            LOWER(email) as email,
            LENGTH(first_name) as name_length
        FROM customers
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['full_name', 'email', 'name_length']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_date_functions(self, mock_sqlite3):
        """Test query execution with date functions"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock date function results
        mock_cursor.fetchall.return_value = [
            ('2024-01-15', '2024-01-15 10:30:00')
        ]
        mock_cursor.description = [
            ('date_only',), ('datetime_full',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT 
            DATE(created_at) as date_only,
            DATETIME(created_at) as datetime_full
        FROM customers
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['date_only', 'datetime_full']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_numeric_functions(self, mock_sqlite3):
        """Test query execution with numeric functions"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock numeric function results
        mock_cursor.fetchall.return_value = [
            (5000.50, 5000.50, 5001.0)
        ]
        mock_cursor.description = [
            ('rounded_balance',), ('absolute_balance',), ('ceiling_balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT 
            ROUND(balance, 2) as rounded_balance,
            ABS(balance) as absolute_balance,
            CEIL(balance) as ceiling_balance
        FROM accounts
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['rounded_balance', 'absolute_balance', 'ceiling_balance']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_string_functions(self, mock_sqlite3):
        """Test query execution with string functions"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock string function results
        mock_cursor.fetchall.return_value = [
            ('Joh', 'john[at]example.com', 'John Doe')
        ]
        mock_cursor.description = [
            ('name_substr',), ('email_replaced',), ('name_trimmed',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT 
            SUBSTR(first_name, 1, 3) as name_substr,
            REPLACE(email, '@', '[at]') as email_replaced,
            TRIM(first_name || ' ' || last_name) as name_trimmed
        FROM customers
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['name_substr', 'email_replaced', 'name_trimmed']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_arithmetic_operations(self, mock_sqlite3):
        """Test query execution with arithmetic operations"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock arithmetic operation results
        mock_cursor.fetchall.return_value = [
            (5250.00, 5100.00, 0.05)
        ]
        mock_cursor.description = [
            ('balance_with_interest',), ('balance_with_bonus',), ('interest_rate',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT 
            balance * 1.05 as balance_with_interest,
            balance + 100 as balance_with_bonus,
            interest_rate
        FROM accounts
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['balance_with_interest', 'balance_with_bonus', 'interest_rate']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_logical_operators(self, mock_sqlite3):
        """Test query execution with logical operators"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock logical operator results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 'TX')
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('state',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, state
        FROM customers
        WHERE (state = 'TX' OR state = 'CA') AND created_at > '2020-01-01'
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['first_name', 'last_name', 'state']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_comparison_operators(self, mock_sqlite3):
        """Test query execution with comparison operators"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock comparison operator results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 5000.00)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT c.first_name, c.last_name, a.balance
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        WHERE a.balance > 1000 AND a.balance <= 10000 AND a.type != 'savings'
        LIMIT 1
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ['first_name', 'last_name', 'balance']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_null_checks(self, mock_sqlite3):
        """Test query execution with NULL checks"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock NULL check results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 'john@example.com'),
            ('Jane', 'Smith', None)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('phone',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, phone
        FROM customers
        WHERE phone IS NULL OR email IS NOT NULL
        LIMIT 2
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'phone']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_like_patterns(self, mock_sqlite3):
        """Test query execution with LIKE patterns"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock LIKE pattern results
        mock_cursor.fetchall.return_value = [
            ('john@gmail.com',),
            ('jane@gmail.com',)
        ]
        mock_cursor.description = [
            ('email',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT email
        FROM customers
        WHERE email LIKE '%@gmail.com' OR phone LIKE '555-%'
        LIMIT 2
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['email']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_in_clause(self, mock_sqlite3):
        """Test query execution with IN clause"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock IN clause results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 'TX'),
            ('Jane', 'Smith', 'CA'),
            ('Bob', 'Johnson', 'NY')
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('state',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT first_name, last_name, state
        FROM customers
        WHERE state IN ('TX', 'CA', 'NY')
        LIMIT 3
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 3
        assert result["columns"] == ['first_name', 'last_name', 'state']
    
    @patch('backend.executor.sqlite3')
    def test_run_query_with_between_clause(self, mock_sqlite3):
        """Test query execution with BETWEEN clause"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock BETWEEN clause results
        mock_cursor.fetchall.return_value = [
            ('John', 'Doe', 5000.00),
            ('Jane', 'Smith', 7500.00)
        ]
        mock_cursor.description = [
            ('first_name',), ('last_name',), ('balance',)
        ]
        
        mock_sqlite3.connect.return_value = mock_connection
        
        sql = """
        SELECT c.first_name, c.last_name, a.balance
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        WHERE a.balance BETWEEN 1000 AND 10000
        LIMIT 2
        """
        result = self.executor.run_query(sql)
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["columns"] == ['first_name', 'last_name', 'balance']
