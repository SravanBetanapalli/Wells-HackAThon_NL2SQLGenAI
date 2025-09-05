import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.planner import PlannerAgent
from backend.metadata_loader import MetadataLoader


class TestPlannerAgent:
    """Test cases for PlannerAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.schema_map = {
            "customers": ["id", "first_name", "last_name", "email", "phone", "address", "date_of_birth", "gender", "national_id", "created_at", "updated_at", "branch_id"],
            "accounts": ["id", "customer_id", "account_number", "type", "balance", "opened_at", "interest_rate", "status", "branch_id", "created_at", "updated_at"],
            "branches": ["id", "name", "address", "city", "state", "zip_code", "manager_id", "created_at", "updated_at"],
            "employees": ["id", "branch_id", "name", "email", "phone", "position", "hire_date", "salary", "created_at", "updated_at"],
            "transactions": ["id", "account_id", "transaction_date", "amount", "type", "description", "status", "created_at", "updated_at", "employee_id"]
        }
        
        with patch('backend.planner.MetadataLoader'):
            self.planner = PlannerAgent(self.schema_map)
    
    def test_init(self):
        """Test PlannerAgent initialization"""
        assert self.planner.schema_map == self.schema_map
        assert self.planner.conversation_state == {}
    
    def test_detect_tables_basic(self):
        """Test basic table detection"""
        query = "Show me all customers"
        tables = self.planner._detect_tables(query)
        assert "customers" in tables
    
    def test_detect_tables_multiple(self):
        """Test detection of multiple tables"""
        query = "Find customers and their accounts"
        tables = self.planner._detect_tables(query)
        assert "customers" in tables
        assert "accounts" in tables
    
    def test_analyze_query_basic(self):
        """Test basic query analysis"""
        query = "Show me all customers"
        result = self.planner.analyze_query(query)
        
        assert "tables" in result
        assert "capabilities" in result
        assert "steps" in result
        assert "customers" in result["tables"]
    
    def test_analyze_query_with_aggregation(self):
        """Test query analysis with aggregation"""
        query = "What is the total balance of all accounts"
        result = self.planner.analyze_query(query)
        
        assert "accounts" in result["tables"]
        assert "aggregation" in result["capabilities"]
    
    def test_error_handling_invalid_query(self):
        """Test error handling for invalid queries"""
        query = ""
        result = self.planner.analyze_query(query)
        
        assert "tables" in result
        assert "capabilities" in result
        # Should handle empty query gracefully
