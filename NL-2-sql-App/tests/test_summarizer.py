import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.summarizer import SummarizerAgent


class TestSummarizerAgent:
    """Test cases for SummarizerAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.summarizer = SummarizerAgent()
    
    def test_init(self):
        """Test SummarizerAgent initialization"""
        assert hasattr(self.summarizer, 'summarize')
    
    def test_summarize_basic(self):
        """Test basic summarization"""
        query = "Show me all customers"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "first_name": "John", "last_name": "Doe", "email": "john@example.com"},
                {"id": 2, "first_name": "Jane", "last_name": "Smith", "email": "jane@example.com"}
            ],
            "columns": ["id", "first_name", "last_name", "email"],
            "row_count": 2
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert isinstance(result["summary"], str)
        assert isinstance(result["suggestions"], list)
    
    def test_summarize_empty_results(self):
        """Test summarization with empty results"""
        query = "Show me customers from Mars"
        execution_result = {
            "success": True,
            "data": [],
            "columns": ["id", "first_name", "last_name", "email"],
            "row_count": 0
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "no results" in result["summary"].lower() or "empty" in result["summary"].lower()
    
    def test_summarize_aggregation_results(self):
        """Test summarization with aggregation results"""
        query = "What is the total balance of all accounts?"
        execution_result = {
            "success": True,
            "data": [
                {"total_balance": 150000.50, "account_count": 25}
            ],
            "columns": ["total_balance", "account_count"],
            "row_count": 1
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "150000" in result["summary"] or "total" in result["summary"].lower()
    
    def test_summarize_group_by_results(self):
        """Test summarization with GROUP BY results"""
        query = "Show me customers by state"
        execution_result = {
            "success": True,
            "data": [
                {"state": "TX", "customer_count": 15},
                {"state": "CA", "customer_count": 12},
                {"state": "NY", "customer_count": 8}
            ],
            "columns": ["state", "customer_count"],
            "row_count": 3
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "TX" in result["summary"] or "Texas" in result["summary"]
        assert "CA" in result["summary"] or "California" in result["summary"]
    
    def test_summarize_error_results(self):
        """Test summarization with error results"""
        query = "Show me invalid data"
        execution_result = {
            "success": False,
            "error": "Table does not exist"
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "error" in result["summary"].lower() or "failed" in result["summary"].lower()
    
    def test_summarize_large_dataset(self):
        """Test summarization with large dataset"""
        query = "Show me all transactions"
        execution_result = {
            "success": True,
            "data": [{"id": i, "amount": 100 + i, "type": "deposit"} for i in range(1000)],
            "columns": ["id", "amount", "type"],
            "row_count": 1000
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "1000" in result["summary"] or "thousand" in result["summary"].lower()
    
    def test_summarize_with_numeric_data(self):
        """Test summarization with numeric data"""
        query = "Show me account balances"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "balance": 5000.00},
                {"id": 2, "balance": 15000.50},
                {"id": 3, "balance": 2500.75}
            ],
            "columns": ["id", "balance"],
            "row_count": 3
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        # Should mention balance ranges or statistics
        assert any(word in result["summary"].lower() for word in ["balance", "amount", "money"])
    
    def test_summarize_with_date_data(self):
        """Test summarization with date data"""
        query = "Show me recent transactions"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "date": "2024-01-15", "amount": 100.00},
                {"id": 2, "date": "2024-01-16", "amount": 250.00},
                {"id": 3, "date": "2024-01-17", "amount": 75.50}
            ],
            "columns": ["id", "date", "amount"],
            "row_count": 3
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "2024" in result["summary"] or "recent" in result["summary"].lower()
    
    def test_summarize_with_text_data(self):
        """Test summarization with text data"""
        query = "Show me customer names"
        execution_result = {
            "success": True,
            "data": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Smith"},
                {"first_name": "Bob", "last_name": "Johnson"}
            ],
            "columns": ["first_name", "last_name"],
            "row_count": 3
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "customer" in result["summary"].lower() or "name" in result["summary"].lower()
    
    def test_summarize_with_boolean_data(self):
        """Test summarization with boolean data"""
        query = "Show me active accounts"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "active": True, "balance": 5000.00},
                {"id": 2, "active": False, "balance": 0.00},
                {"id": 3, "active": True, "balance": 15000.00}
            ],
            "columns": ["id", "active", "balance"],
            "row_count": 3
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "active" in result["summary"].lower()
    
    def test_summarize_with_null_data(self):
        """Test summarization with null data"""
        query = "Show me customer phone numbers"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "phone": "555-1234"},
                {"id": 2, "phone": None},
                {"id": 3, "phone": "555-5678"}
            ],
            "columns": ["id", "phone"],
            "row_count": 3
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        # Should mention missing data or null values
        assert any(word in result["summary"].lower() for word in ["missing", "null", "empty", "phone"])
    
    def test_summarize_with_complex_query(self):
        """Test summarization with complex query results"""
        query = "Show me customers with high balance accounts in Texas"
        execution_result = {
            "success": True,
            "data": [
                {"customer_name": "John Doe", "balance": 25000.00, "state": "TX"},
                {"customer_name": "Jane Smith", "balance": 30000.00, "state": "TX"}
            ],
            "columns": ["customer_name", "balance", "state"],
            "row_count": 2
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "Texas" in result["summary"] or "TX" in result["summary"]
        assert "25000" in result["summary"] or "30000" in result["summary"] or "high" in result["summary"].lower()
    
    def test_summarize_suggestions_generation(self):
        """Test that suggestions are generated"""
        query = "Show me all customers"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "first_name": "John", "last_name": "Doe", "email": "john@example.com"}
            ],
            "columns": ["id", "first_name", "last_name", "email"],
            "row_count": 1
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0
        # Suggestions should be strings
        assert all(isinstance(s, str) for s in result["suggestions"])
    
    def test_summarize_error_handling(self):
        """Test error handling in summarization"""
        query = "Invalid query"
        execution_result = {
            "success": False,
            "error": "Some database error occurred"
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        # Should handle errors gracefully
        assert "error" in result["summary"].lower() or "failed" in result["summary"].lower()
    
    def test_summarize_with_single_result(self):
        """Test summarization with single result"""
        query = "Show me customer with ID 1"
        execution_result = {
            "success": True,
            "data": [
                {"id": 1, "first_name": "John", "last_name": "Doe", "email": "john@example.com"}
            ],
            "columns": ["id", "first_name", "last_name", "email"],
            "row_count": 1
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        assert "John" in result["summary"] or "Doe" in result["summary"]
    
    def test_summarize_with_multiple_columns(self):
        """Test summarization with many columns"""
        query = "Show me detailed customer information"
        execution_result = {
            "success": True,
            "data": [
                {
                    "id": 1, "first_name": "John", "last_name": "Doe", 
                    "email": "john@example.com", "phone": "555-1234",
                    "address": "123 Main St", "city": "Austin", "state": "TX",
                    "zip_code": "78701", "created_at": "2024-01-15"
                }
            ],
            "columns": ["id", "first_name", "last_name", "email", "phone", "address", "city", "state", "zip_code", "created_at"],
            "row_count": 1
        }
        
        result = self.summarizer.summarize(query, execution_result)
        
        assert "summary" in result
        assert "suggestions" in result
        # Should handle multiple columns gracefully
        assert "customer" in result["summary"].lower() or "information" in result["summary"].lower()
