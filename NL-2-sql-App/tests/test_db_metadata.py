import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock, mock_open

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.db_metadata import DBMetadata


class TestDBMetadata:
    """Test cases for DBMetadata"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.sample_metadata = {
            "tables": {
                "customers": {
                    "description": "Customer information table",
                    "columns": {
                        "id": {
                            "type": "INTEGER",
                            "primary_key": True,
                            "required": True
                        },
                        "first_name": {
                            "type": "TEXT",
                            "required": True,
                            "distinct_values": ["John", "Jane", "Bob"]
                        },
                        "last_name": {
                            "type": "TEXT",
                            "required": True,
                            "distinct_values": ["Doe", "Smith", "Johnson"]
                        },
                        "email": {
                            "type": "TEXT",
                            "unique": True,
                            "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        },
                        "balance": {
                            "type": "REAL",
                            "default": 0.0,
                            "sample_values": [1000.0, 2500.0, 500.0]
                        }
                    }
                },
                "accounts": {
                    "description": "Account information table",
                    "columns": {
                        "id": {
                            "type": "INTEGER",
                            "primary_key": True
                        },
                        "customer_id": {
                            "type": "INTEGER",
                            "foreign_key": "customers.id"
                        },
                        "account_number": {
                            "type": "TEXT",
                            "unique": True,
                            "pattern": r"^ACC\d{6}$"
                        }
                    }
                }
            }
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(self.sample_metadata))):
            with patch('json.load', return_value=self.sample_metadata):
                self.metadata = DBMetadata("test_metadata.json")
    
    def test_init(self):
        """Test DBMetadata initialization"""
        assert hasattr(self.metadata, 'metadata_file')
        assert hasattr(self.metadata, 'metadata')
        assert self.metadata.metadata_file == "test_metadata.json"
        assert "tables" in self.metadata.metadata
    
    def test_load_metadata_success(self):
        """Test successful metadata loading"""
        with patch('builtins.open', mock_open(read_data=json.dumps(self.sample_metadata))):
            with patch('json.load', return_value=self.sample_metadata):
                metadata = DBMetadata("test.json")
                assert metadata.metadata == self.sample_metadata
    
    def test_load_metadata_error(self):
        """Test metadata loading with error"""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            metadata = DBMetadata("nonexistent.json")
            assert metadata.metadata == {"tables": {}}
    
    def test_get_table_columns(self):
        """Test getting table columns"""
        columns = self.metadata.get_table_columns("customers")
        expected_columns = ["id", "first_name", "last_name", "email", "balance"]
        assert set(columns) == set(expected_columns)
    
    def test_get_table_columns_nonexistent(self):
        """Test getting columns for nonexistent table"""
        columns = self.metadata.get_table_columns("nonexistent")
        assert columns == []
    
    def test_get_column_values(self):
        """Test getting column distinct values"""
        values = self.metadata.get_column_values("customers", "first_name")
        expected_values = ["John", "Jane", "Bob"]
        assert set(values) == set(expected_values)
    
    def test_get_column_values_nonexistent(self):
        """Test getting values for nonexistent column"""
        values = self.metadata.get_column_values("customers", "nonexistent")
        assert values == []
    
    def test_get_column_values_no_distinct_values(self):
        """Test getting values when no distinct values defined"""
        values = self.metadata.get_column_values("customers", "id")
        assert values == []
    
    def test_validate_value_valid(self):
        """Test validating a valid value"""
        assert self.metadata.validate_value("customers", "first_name", "John") is True
        assert self.metadata.validate_value("customers", "first_name", "Jane") is True
    
    def test_validate_value_invalid(self):
        """Test validating an invalid value"""
        assert self.metadata.validate_value("customers", "first_name", "Invalid") is False
    
    def test_validate_value_no_constraints(self):
        """Test validating value when no distinct values defined"""
        assert self.metadata.validate_value("customers", "id", "any_value") is True
    
    def test_get_column_pattern(self):
        """Test getting column pattern"""
        pattern = self.metadata.get_column_pattern("customers", "email")
        assert pattern == r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    def test_get_column_pattern_nonexistent(self):
        """Test getting pattern for nonexistent column"""
        pattern = self.metadata.get_column_pattern("customers", "nonexistent")
        assert pattern is None
    
    def test_get_table_description(self):
        """Test getting table description"""
        description = self.metadata.get_table_description("customers")
        assert description == "Customer information table"
    
    def test_get_table_description_nonexistent(self):
        """Test getting description for nonexistent table"""
        description = self.metadata.get_table_description("nonexistent")
        assert description == ""
    
    def test_get_column_type(self):
        """Test getting column type"""
        column_type = self.metadata.get_column_type("customers", "first_name")
        assert column_type == "TEXT"
    
    def test_get_column_type_nonexistent(self):
        """Test getting type for nonexistent column"""
        column_type = self.metadata.get_column_type("customers", "nonexistent")
        assert column_type == "TEXT"  # Default value
    
    def test_is_required(self):
        """Test checking if column is required"""
        assert self.metadata.is_required("customers", "first_name") is True
        assert self.metadata.is_required("customers", "email") is False
    
    def test_is_required_nonexistent(self):
        """Test checking required for nonexistent column"""
        assert self.metadata.is_required("customers", "nonexistent") is False
    
    def test_get_default_value(self):
        """Test getting default value"""
        default_value = self.metadata.get_default_value("customers", "balance")
        assert default_value == 0.0
    
    def test_get_default_value_nonexistent(self):
        """Test getting default for nonexistent column"""
        default_value = self.metadata.get_default_value("customers", "nonexistent")
        assert default_value is None
    
    def test_get_sample_values(self):
        """Test getting sample values"""
        sample_values = self.metadata.get_sample_values("customers", "balance")
        expected_values = [1000.0, 2500.0, 500.0]
        assert set(sample_values) == set(expected_values)
    
    def test_get_sample_values_nonexistent(self):
        """Test getting sample values for nonexistent column"""
        sample_values = self.metadata.get_sample_values("customers", "nonexistent")
        assert sample_values == []
    
    def test_get_llm_context(self):
        """Test generating LLM context"""
        context = self.metadata.get_llm_context()
        
        # Check that context contains expected information
        assert "Table 'customers': Customer information table" in context
        assert "Table 'accounts': Account information table" in context
        assert "id (INTEGER) primary key" in context
        assert "first_name (TEXT) required" in context
        assert "email (TEXT)" in context
        assert "balance (REAL) default: 0.0" in context
    
    def test_get_llm_context_empty_metadata(self):
        """Test generating LLM context with empty metadata"""
        self.metadata.metadata = {"tables": {}}
        context = self.metadata.get_llm_context()
        assert context == ""
    
    def test_get_llm_context_missing_columns(self):
        """Test generating LLM context with missing column info"""
        self.metadata.metadata["tables"]["customers"]["columns"]["test"] = {}
        context = self.metadata.get_llm_context()
        assert "test (TEXT)" in context
    
    def test_get_llm_context_with_distinct_values(self):
        """Test generating LLM context with distinct values"""
        context = self.metadata.get_llm_context()
        assert "values: John, Jane, Bob" in context
    
    def test_get_llm_context_with_default_values(self):
        """Test generating LLM context with default values"""
        context = self.metadata.get_llm_context()
        assert "default: 0.0" in context
    
    def test_get_llm_context_with_unique_constraints(self):
        """Test generating LLM context with unique constraints"""
        context = self.metadata.get_llm_context()
        # Should include unique constraint information
        assert "email (TEXT)" in context
    
    def test_get_llm_context_with_primary_keys(self):
        """Test generating LLM context with primary keys"""
        context = self.metadata.get_llm_context()
        assert "primary key" in context
    
    def test_get_llm_context_with_required_fields(self):
        """Test generating LLM context with required fields"""
        context = self.metadata.get_llm_context()
        assert "required" in context
    
    def test_get_llm_context_multiple_tables(self):
        """Test generating LLM context with multiple tables"""
        context = self.metadata.get_llm_context()
        # Should include both tables
        assert "customers" in context
        assert "accounts" in context
    
    def test_get_llm_context_complex_metadata(self):
        """Test generating LLM context with complex metadata"""
        # Add more complex metadata
        self.metadata.metadata["tables"]["transactions"] = {
            "description": "Transaction records",
            "columns": {
                "id": {"type": "INTEGER", "primary_key": True},
                "amount": {"type": "REAL", "required": True},
                "status": {"type": "TEXT", "distinct_values": ["pending", "completed", "failed"]}
            }
        }
        
        context = self.metadata.get_llm_context()
        assert "transactions" in context
        assert "pending, completed, failed" in context
    
    def test_get_llm_context_special_characters(self):
        """Test generating LLM context with special characters"""
        self.metadata.metadata["tables"]["test"] = {
            "description": "Test table with special chars: @#$%",
            "columns": {
                "name": {"type": "TEXT", "distinct_values": ["test@example.com", "user#123"]}
            }
        }
        
        context = self.metadata.get_llm_context()
        assert "Test table with special chars: @#$%" in context
        assert "test@example.com, user#123" in context
