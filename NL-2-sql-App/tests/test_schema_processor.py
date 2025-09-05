import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, mock_open

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.schema_processor import SchemaProcessor


class TestSchemaProcessor:
    """Test cases for SchemaProcessor"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.sample_sql_schema = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            address TEXT,
            date_of_birth DATE,
            gender TEXT CHECK(gender IN ('M', 'F')),
            national_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            branch_id INTEGER REFERENCES branches(id)
        );
        
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            account_number TEXT UNIQUE NOT NULL,
            type TEXT CHECK(type IN ('checking', 'savings', 'credit')),
            balance REAL DEFAULT 0.0,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interest_rate REAL DEFAULT 0.0,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'suspended')),
            branch_id INTEGER REFERENCES branches(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE branches (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            manager_id INTEGER REFERENCES employees(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        self.processor = SchemaProcessor()
    
    def test_init(self):
        """Test SchemaProcessor initialization"""
        assert hasattr(self.processor, 'parse_schema')
        assert hasattr(self.processor, 'extract_tables')
        assert hasattr(self.processor, 'extract_columns')
        assert hasattr(self.processor, 'extract_relationships')
    
    def test_parse_schema_basic(self):
        """Test basic schema parsing"""
        result = self.processor.parse_schema(self.sample_sql_schema)
        
        assert "tables" in result
        assert "relationships" in result
        assert "constraints" in result
        
        # Check tables
        assert "customers" in result["tables"]
        assert "accounts" in result["tables"]
        assert "branches" in result["tables"]
        
        # Check relationships
        assert len(result["relationships"]) > 0
    
    def test_parse_schema_empty(self):
        """Test parsing empty schema"""
        result = self.processor.parse_schema("")
        
        assert result["tables"] == {}
        assert result["relationships"] == []
        assert result["constraints"] == []
    
    def test_parse_schema_invalid_sql(self):
        """Test parsing invalid SQL"""
        invalid_sql = "INVALID SQL STATEMENT"
        result = self.processor.parse_schema(invalid_sql)
        
        assert result["tables"] == {}
        assert result["relationships"] == []
        assert result["constraints"] == []
    
    def test_extract_tables(self):
        """Test table extraction"""
        tables = self.processor.extract_tables(self.sample_sql_schema)
        
        assert "customers" in tables
        assert "accounts" in tables
        assert "branches" in tables
        
        # Check table structure
        assert "columns" in tables["customers"]
        assert "primary_key" in tables["customers"]
        assert "constraints" in tables["customers"]
    
    def test_extract_columns(self):
        """Test column extraction"""
        table_sql = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            balance REAL DEFAULT 0.0
        );
        """
        
        columns = self.processor.extract_columns(table_sql)
        
        assert "id" in columns
        assert "first_name" in columns
        assert "last_name" in columns
        assert "email" in columns
        assert "phone" in columns
        assert "balance" in columns
        
        # Check column properties
        assert columns["id"]["type"] == "INTEGER"
        assert columns["id"]["primary_key"] is True
        assert columns["first_name"]["type"] == "TEXT"
        assert columns["first_name"]["nullable"] is False
        assert columns["email"]["unique"] is True
        assert columns["balance"]["default"] == "0.0"
    
    def test_extract_relationships(self):
        """Test relationship extraction"""
        relationships = self.processor.extract_relationships(self.sample_sql_schema)
        
        assert len(relationships) > 0
        
        # Check for foreign key relationships
        customer_account_relation = None
        for rel in relationships:
            if rel["table"] == "accounts" and rel["referenced_table"] == "customers":
                customer_account_relation = rel
                break
        
        assert customer_account_relation is not None
        assert customer_account_relation["column"] == "customer_id"
        assert customer_account_relation["referenced_column"] == "id"
    
    def test_extract_constraints(self):
        """Test constraint extraction"""
        constraints = self.processor.extract_constraints(self.sample_sql_schema)
        
        assert len(constraints) > 0
        
        # Check for CHECK constraints
        gender_constraint = None
        for constraint in constraints:
            if constraint["table"] == "customers" and constraint["column"] == "gender":
                gender_constraint = constraint
                break
        
        assert gender_constraint is not None
        assert gender_constraint["type"] == "CHECK"
        assert "gender IN ('M', 'F')" in gender_constraint["definition"]
    
    def test_parse_data_type(self):
        """Test data type parsing"""
        # Test various data types
        assert self.processor.parse_data_type("INTEGER") == "INTEGER"
        assert self.processor.parse_data_type("TEXT") == "TEXT"
        assert self.processor.parse_data_type("REAL") == "REAL"
        assert self.processor.parse_data_type("DATE") == "DATE"
        assert self.processor.parse_data_type("TIMESTAMP") == "TIMESTAMP"
        assert self.processor.parse_data_type("BLOB") == "BLOB"
        
        # Test with size specifications
        assert self.processor.parse_data_type("VARCHAR(255)") == "VARCHAR"
        assert self.processor.parse_data_type("DECIMAL(10,2)") == "DECIMAL"
    
    def test_parse_column_constraints(self):
        """Test column constraint parsing"""
        column_def = "email TEXT UNIQUE NOT NULL"
        constraints = self.processor.parse_column_constraints(column_def)
        
        assert "unique" in constraints
        assert "not_null" in constraints
        assert constraints["unique"] is True
        assert constraints["not_null"] is True
    
    def test_parse_column_default(self):
        """Test column default value parsing"""
        # Test with default value
        column_def = "balance REAL DEFAULT 0.0"
        default_value = self.processor.parse_column_default(column_def)
        assert default_value == "0.0"
        
        # Test without default value
        column_def = "name TEXT"
        default_value = self.processor.parse_column_default(column_def)
        assert default_value is None
    
    def test_parse_foreign_key(self):
        """Test foreign key parsing"""
        column_def = "customer_id INTEGER REFERENCES customers(id)"
        fk_info = self.processor.parse_foreign_key(column_def)
        
        assert fk_info is not None
        assert fk_info["referenced_table"] == "customers"
        assert fk_info["referenced_column"] == "id"
    
    def test_parse_check_constraint(self):
        """Test CHECK constraint parsing"""
        constraint_def = "CHECK(gender IN ('M', 'F'))"
        check_info = self.processor.parse_check_constraint(constraint_def)
        
        assert check_info is not None
        assert check_info["column"] == "gender"
        assert "IN ('M', 'F')" in check_info["condition"]
    
    def test_generate_schema_summary(self):
        """Test schema summary generation"""
        parsed_schema = self.processor.parse_schema(self.sample_sql_schema)
        summary = self.processor.generate_schema_summary(parsed_schema)
        
        assert "total_tables" in summary
        assert "total_columns" in summary
        assert "total_relationships" in summary
        assert "primary_keys" in summary
        assert "foreign_keys" in summary
        assert "unique_constraints" in summary
        assert "check_constraints" in summary
        
        assert summary["total_tables"] == 3
        assert summary["total_relationships"] > 0
    
    def test_validate_schema(self):
        """Test schema validation"""
        # Valid schema
        validation_result = self.processor.validate_schema(self.sample_sql_schema)
        assert validation_result["is_valid"] is True
        assert "errors" in validation_result
        assert len(validation_result["errors"]) == 0
        
        # Invalid schema
        invalid_schema = """
        CREATE TABLE test (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE test2 (
            id INTEGER REFERENCES nonexistent(id)
        );
        """
        
        validation_result = self.processor.validate_schema(invalid_schema)
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) > 0
    
    def test_extract_indexes(self):
        """Test index extraction"""
        schema_with_indexes = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT
        );
        CREATE INDEX idx_customers_email ON customers(email);
        CREATE INDEX idx_customers_name ON customers(name);
        """
        
        indexes = self.processor.extract_indexes(schema_with_indexes)
        
        assert len(indexes) == 2
        assert any(idx["name"] == "idx_customers_email" for idx in indexes)
        assert any(idx["name"] == "idx_customers_name" for idx in indexes)
    
    def test_extract_triggers(self):
        """Test trigger extraction"""
        schema_with_triggers = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            updated_at TIMESTAMP
        );
        
        CREATE TRIGGER update_customer_timestamp
        AFTER UPDATE ON customers
        FOR EACH ROW
        BEGIN
            UPDATE customers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
        
        triggers = self.processor.extract_triggers(schema_with_triggers)
        
        assert len(triggers) == 1
        assert triggers[0]["name"] == "update_customer_timestamp"
        assert triggers[0]["table"] == "customers"
        assert triggers[0]["event"] == "UPDATE"
    
    def test_extract_views(self):
        """Test view extraction"""
        schema_with_views = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT
        );
        
        CREATE VIEW active_customers AS
        SELECT * FROM customers WHERE email IS NOT NULL;
        """
        
        views = self.processor.extract_views(schema_with_views)
        
        assert len(views) == 1
        assert views[0]["name"] == "active_customers"
        assert "SELECT" in views[0]["definition"]
    
    def test_parse_schema_from_file(self):
        """Test parsing schema from file"""
        mock_file_content = self.sample_sql_schema
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            result = self.processor.parse_schema_from_file("test_schema.sql")
            
            assert "tables" in result
            assert "customers" in result["tables"]
            assert "accounts" in result["tables"]
            assert "branches" in result["tables"]
    
    def test_parse_schema_from_file_error(self):
        """Test parsing schema from file with error"""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            result = self.processor.parse_schema_from_file("nonexistent.sql")
            
            assert result["tables"] == {}
            assert result["relationships"] == []
            assert result["constraints"] == []
    
    def test_generate_erd_diagram(self):
        """Test ERD diagram generation"""
        parsed_schema = self.processor.parse_schema(self.sample_sql_schema)
        erd = self.processor.generate_erd_diagram(parsed_schema)
        
        assert "entities" in erd
        assert "relationships" in erd
        assert len(erd["entities"]) == 3
        assert len(erd["relationships"]) > 0
    
    def test_export_schema_to_json(self):
        """Test schema export to JSON"""
        parsed_schema = self.processor.parse_schema(self.sample_sql_schema)
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                self.processor.export_schema_to_json(parsed_schema, "test_schema.json")
                
                mock_file.assert_called_once_with("test_schema.json", 'w')
                mock_json_dump.assert_called_once()
    
    def test_import_schema_from_json(self):
        """Test schema import from JSON"""
        schema_data = {
            "tables": {
                "customers": {
                    "columns": {
                        "id": {"type": "INTEGER", "primary_key": True},
                        "name": {"type": "TEXT"}
                    }
                }
            },
            "relationships": [],
            "constraints": []
        }
        
        with patch('builtins.open', mock_open(read_data='{"tables": {"customers": {"columns": {"id": {"type": "INTEGER", "primary_key": True}, "name": {"type": "TEXT"}}}}, "relationships": [], "constraints": []}')):
            with patch('json.load') as mock_json_load:
                mock_json_load.return_value = schema_data
                
                result = self.processor.import_schema_from_json("test_schema.json")
                
                assert result == schema_data
    
    def test_compare_schemas(self):
        """Test schema comparison"""
        schema1 = self.processor.parse_schema(self.sample_sql_schema)
        
        modified_schema = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            address TEXT,
            date_of_birth DATE,
            gender TEXT CHECK(gender IN ('M', 'F')),
            national_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            branch_id INTEGER REFERENCES branches(id),
            new_column TEXT
        );
        """
        schema2 = self.processor.parse_schema(modified_schema)
        
        comparison = self.processor.compare_schemas(schema1, schema2)
        
        assert "added_tables" in comparison
        assert "removed_tables" in comparison
        assert "added_columns" in comparison
        assert "removed_columns" in comparison
        assert "modified_columns" in comparison
    
    def test_generate_migration_script(self):
        """Test migration script generation"""
        old_schema = self.processor.parse_schema(self.sample_sql_schema)
        
        new_schema_sql = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            address TEXT,
            date_of_birth DATE,
            gender TEXT CHECK(gender IN ('M', 'F')),
            national_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            branch_id INTEGER REFERENCES branches(id),
            new_column TEXT
        );
        """
        new_schema = self.processor.parse_schema(new_schema_sql)
        
        migration = self.processor.generate_migration_script(old_schema, new_schema)
        
        assert "ALTER TABLE" in migration
        assert "ADD COLUMN" in migration
