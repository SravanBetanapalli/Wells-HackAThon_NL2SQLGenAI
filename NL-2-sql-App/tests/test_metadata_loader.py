import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
import json

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.metadata_loader import MetadataLoader


class TestMetadataLoader:
    """Test cases for MetadataLoader"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.sample_schema = """
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
            customer_id INTEGER NOT NULL,
            account_number TEXT UNIQUE NOT NULL,
            account_type TEXT CHECK(account_type IN ('checking', 'savings', 'credit')),
            balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            transaction_type TEXT CHECK(transaction_type IN ('deposit', 'withdrawal', 'transfer')),
            amount REAL NOT NULL,
            description TEXT,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );
        """
        
        self.sample_data = {
            "customers": [
                {
                    "id": 1,
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "555-1234",
                    "address": "123 Main St, Anytown, USA",
                    "date_of_birth": "1985-03-15",
                    "gender": "M",
                    "national_id": "123456789",
                    "created_at": "2024-01-01 10:00:00",
                    "updated_at": "2024-01-01 10:00:00",
                    "branch_id": 1
                },
                {
                    "id": 2,
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "email": "jane.smith@example.com",
                    "phone": "555-5678",
                    "address": "456 Oak Ave, Somewhere, USA",
                    "date_of_birth": "1990-07-22",
                    "gender": "F",
                    "national_id": "987654321",
                    "created_at": "2024-01-02 11:00:00",
                    "updated_at": "2024-01-02 11:00:00",
                    "branch_id": 2
                }
            ],
            "accounts": [
                {
                    "id": 1,
                    "customer_id": 1,
                    "account_number": "ACC001",
                    "account_type": "checking",
                    "balance": 5000.00,
                    "status": "active",
                    "created_at": "2024-01-01 10:30:00"
                },
                {
                    "id": 2,
                    "customer_id": 1,
                    "account_number": "ACC002",
                    "account_type": "savings",
                    "balance": 15000.00,
                    "status": "active",
                    "created_at": "2024-01-01 10:35:00"
                },
                {
                    "id": 3,
                    "customer_id": 2,
                    "account_number": "ACC003",
                    "account_type": "checking",
                    "balance": 3000.00,
                    "status": "active",
                    "created_at": "2024-01-02 11:30:00"
                }
            ],
            "transactions": [
                {
                    "id": 1,
                    "account_id": 1,
                    "transaction_type": "deposit",
                    "amount": 5000.00,
                    "description": "Initial deposit",
                    "transaction_date": "2024-01-01 10:30:00"
                },
                {
                    "id": 2,
                    "account_id": 2,
                    "transaction_type": "deposit",
                    "amount": 15000.00,
                    "description": "Initial deposit",
                    "transaction_date": "2024-01-01 10:35:00"
                },
                {
                    "id": 3,
                    "account_id": 3,
                    "transaction_type": "deposit",
                    "amount": 3000.00,
                    "description": "Initial deposit",
                    "transaction_date": "2024-01-02 11:30:00"
                }
            ]
        }
        
        with patch('backend.metadata_loader.open') as mock_open_func:
            mock_open_func.return_value.__enter__.return_value.read.return_value = self.sample_schema
            self.loader = MetadataLoader()
    
    def test_init(self):
        """Test MetadataLoader initialization"""
        assert hasattr(self.loader, 'load_schema')
        assert hasattr(self.loader, 'load_sample_data')
        assert hasattr(self.loader, 'extract_metadata')
    
    def test_load_schema_success(self):
        """Test successful schema loading"""
        with patch('builtins.open', mock_open(read_data=self.sample_schema)):
            schema = self.loader.load_schema("test_schema.sql")
            
            assert "customers" in schema
            assert "accounts" in schema
            assert "transactions" in schema
            assert "id" in schema["customers"]
            assert "first_name" in schema["customers"]
            assert "customer_id" in schema["accounts"]
    
    def test_load_schema_file_not_found(self):
        """Test schema loading with file not found"""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            schema = self.loader.load_schema("nonexistent.sql")
            assert schema == {}
    
    def test_load_schema_parse_error(self):
        """Test schema loading with parse error"""
        invalid_schema = "INVALID SQL CREATE TABLE;"
        
        with patch('builtins.open', mock_open(read_data=invalid_schema)):
            schema = self.loader.load_schema("invalid_schema.sql")
            # Should handle parse errors gracefully
            assert isinstance(schema, dict)
    
    def test_load_sample_data_success(self):
        """Test successful sample data loading"""
        sample_data_json = json.dumps(self.sample_data)
        
        with patch('builtins.open', mock_open(read_data=sample_data_json)):
            data = self.loader.load_sample_data("test_data.json")
            
            assert "customers" in data
            assert "accounts" in data
            assert "transactions" in data
            assert len(data["customers"]) == 2
            assert len(data["accounts"]) == 3
            assert len(data["transactions"]) == 3
    
    def test_load_sample_data_file_not_found(self):
        """Test sample data loading with file not found"""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            data = self.loader.load_sample_data("nonexistent.json")
            assert data == {}
    
    def test_load_sample_data_json_error(self):
        """Test sample data loading with JSON error"""
        invalid_json = "{ invalid json }"
        
        with patch('builtins.open', mock_open(read_data=invalid_json)):
            data = self.loader.load_sample_data("invalid_data.json")
            assert data == {}
    
    def test_extract_metadata_success(self):
        """Test successful metadata extraction"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        assert "tables" in metadata
        assert "customers" in metadata["tables"]
        assert "accounts" in metadata["tables"]
        assert "transactions" in metadata["tables"]
        
        # Check table descriptions
        assert "description" in metadata["tables"]["customers"]
        assert "description" in metadata["tables"]["accounts"]
        assert "description" in metadata["tables"]["transactions"]
        
        # Check columns
        assert "columns" in metadata["tables"]["customers"]
        assert "id" in metadata["tables"]["customers"]["columns"]
        assert "first_name" in metadata["tables"]["customers"]["columns"]
    
    def test_extract_metadata_empty_schema(self):
        """Test metadata extraction with empty schema"""
        metadata = self.loader.extract_metadata({}, {})
        assert metadata == {"tables": {}}
    
    def test_extract_metadata_empty_data(self):
        """Test metadata extraction with empty data"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        metadata = self.loader.extract_metadata(schema, {})
        
        assert "tables" in metadata
        assert "customers" in metadata["tables"]
        assert "columns" in metadata["tables"]["customers"]
        # Should still extract schema info even without data
    
    def test_extract_metadata_with_distinct_values(self):
        """Test metadata extraction with distinct values"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        # Check that distinct values are extracted
        customers_table = metadata["tables"]["customers"]
        assert "first_name" in customers_table["columns"]
        
        # Should have distinct values for text fields
        if "distinct_values" in customers_table["columns"]["first_name"]:
            distinct_values = customers_table["columns"]["first_name"]["distinct_values"]
            assert "John" in distinct_values
            assert "Jane" in distinct_values
    
    def test_extract_metadata_with_data_types(self):
        """Test metadata extraction with data types"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        customers_table = metadata["tables"]["customers"]
        assert "id" in customers_table["columns"]
        assert "type" in customers_table["columns"]["id"]
        assert customers_table["columns"]["id"]["type"] == "INTEGER"
        
        assert "first_name" in customers_table["columns"]
        assert "type" in customers_table["columns"]["first_name"]
        assert customers_table["columns"]["first_name"]["type"] == "TEXT"
    
    def test_extract_metadata_with_constraints(self):
        """Test metadata extraction with constraints"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        customers_table = metadata["tables"]["customers"]
        
        # Check primary key
        assert "primary_key" in customers_table["columns"]["id"]
        assert customers_table["columns"]["id"]["primary_key"] is True
        
        # Check unique constraints
        assert "unique" in customers_table["columns"]["email"]
        assert customers_table["columns"]["email"]["unique"] is True
        
        # Check NOT NULL constraints
        assert "required" in customers_table["columns"]["first_name"]
        assert customers_table["columns"]["first_name"]["required"] is True
    
    def test_extract_metadata_with_foreign_keys(self):
        """Test metadata extraction with foreign keys"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        accounts_table = metadata["tables"]["accounts"]
        
        # Check foreign key
        assert "customer_id" in accounts_table["columns"]
        assert "foreign_key" in accounts_table["columns"]["customer_id"]
        assert accounts_table["columns"]["customer_id"]["foreign_key"] == "customers.id"
    
    def test_extract_metadata_with_check_constraints(self):
        """Test metadata extraction with check constraints"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        customers_table = metadata["tables"]["customers"]
        
        # Check gender constraint
        assert "gender" in customers_table["columns"]
        if "check_constraint" in customers_table["columns"]["gender"]:
            check_constraint = customers_table["columns"]["gender"]["check_constraint"]
            assert "M" in check_constraint
            assert "F" in check_constraint
    
    def test_extract_metadata_with_default_values(self):
        """Test metadata extraction with default values"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        accounts_table = metadata["tables"]["accounts"]
        
        # Check default values
        assert "balance" in accounts_table["columns"]
        if "default" in accounts_table["columns"]["balance"]:
            assert accounts_table["columns"]["balance"]["default"] == 0.0
        
        assert "status" in accounts_table["columns"]
        if "default" in accounts_table["columns"]["status"]:
            assert accounts_table["columns"]["status"]["default"] == "active"
    
    def test_extract_metadata_with_sample_values(self):
        """Test metadata extraction with sample values"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        customers_table = metadata["tables"]["customers"]
        
        # Check sample values for numeric fields
        if "sample_values" in customers_table["columns"]["id"]:
            sample_values = customers_table["columns"]["id"]["sample_values"]
            assert 1 in sample_values
            assert 2 in sample_values
    
    def test_extract_metadata_with_patterns(self):
        """Test metadata extraction with patterns"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        customers_table = metadata["tables"]["customers"]
        
        # Check email pattern
        if "pattern" in customers_table["columns"]["email"]:
            pattern = customers_table["columns"]["email"]["pattern"]
            assert "@" in pattern
            assert "example.com" in pattern
    
    def test_extract_metadata_with_relationships(self):
        """Test metadata extraction with relationships"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        data = self.sample_data
        
        metadata = self.loader.extract_metadata(schema, data)
        
        # Check that relationships are identified
        if "relationships" in metadata:
            relationships = metadata["relationships"]
            assert len(relationships) > 0
            
            # Should have customer-account relationship
            customer_account_rel = next((r for r in relationships if r["from_table"] == "customers" and r["to_table"] == "accounts"), None)
            assert customer_account_rel is not None
            assert customer_account_rel["from_column"] == "id"
            assert customer_account_rel["to_column"] == "customer_id"
    
    def test_load_schema_from_string(self):
        """Test loading schema from string"""
        schema = self.loader.load_schema_from_string(self.sample_schema)
        
        assert "customers" in schema
        assert "accounts" in schema
        assert "transactions" in schema
        
        # Check table structure
        customers_table = schema["customers"]
        assert "columns" in customers_table
        assert "id" in customers_table["columns"]
        assert "first_name" in customers_table["columns"]
        assert "last_name" in customers_table["columns"]
    
    def test_load_schema_from_string_invalid_sql(self):
        """Test loading schema from invalid SQL string"""
        invalid_sql = "INVALID SQL STATEMENT;"
        schema = self.loader.load_schema_from_string(invalid_sql)
        
        # Should handle invalid SQL gracefully
        assert isinstance(schema, dict)
    
    def test_load_schema_from_string_empty(self):
        """Test loading schema from empty string"""
        schema = self.loader.load_schema_from_string("")
        assert schema == {}
    
    def test_load_schema_from_string_partial_sql(self):
        """Test loading schema from partial SQL"""
        partial_sql = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL
        );
        -- Incomplete SQL
        """
        schema = self.loader.load_schema_from_string(partial_sql)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "first_name" in schema["customers"]["columns"]
    
    def test_load_schema_from_string_with_comments(self):
        """Test loading schema with SQL comments"""
        sql_with_comments = """
        -- This is a comment
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY, -- Primary key
            first_name TEXT NOT NULL, -- Customer first name
            last_name TEXT NOT NULL -- Customer last name
        );
        -- Another comment
        """
        schema = self.loader.load_schema_from_string(sql_with_comments)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "first_name" in schema["customers"]["columns"]
        assert "last_name" in schema["customers"]["columns"]
    
    def test_load_schema_from_string_with_multiple_statements(self):
        """Test loading schema with multiple CREATE TABLE statements"""
        multiple_tables_sql = """
        CREATE TABLE table1 (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        
        CREATE TABLE table2 (
            id INTEGER PRIMARY KEY,
            table1_id INTEGER REFERENCES table1(id)
        );
        """
        schema = self.loader.load_schema_from_string(multiple_tables_sql)
        
        assert "table1" in schema
        assert "table2" in schema
        assert "id" in schema["table1"]["columns"]
        assert "id" in schema["table2"]["columns"]
        assert "table1_id" in schema["table2"]["columns"]
    
    def test_load_schema_from_string_with_indexes(self):
        """Test loading schema with indexes"""
        sql_with_indexes = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT
        );
        
        CREATE INDEX idx_customers_name ON customers(name);
        CREATE UNIQUE INDEX idx_customers_email ON customers(email);
        """
        schema = self.loader.load_schema_from_string(sql_with_indexes)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "email" in schema["customers"]["columns"]
        assert "name" in schema["customers"]["columns"]
    
    def test_load_schema_from_string_with_views(self):
        """Test loading schema with views"""
        sql_with_views = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT
        );
        
        CREATE VIEW active_customers AS
        SELECT * FROM customers WHERE email IS NOT NULL;
        """
        schema = self.loader.load_schema_from_string(sql_with_views)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "name" in schema["customers"]["columns"]
        assert "email" in schema["customers"]["columns"]
    
    def test_load_schema_from_string_with_triggers(self):
        """Test loading schema with triggers"""
        sql_with_triggers = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TRIGGER update_created_at
        BEFORE INSERT ON customers
        FOR EACH ROW
        BEGIN
            UPDATE customers SET created_at = CURRENT_TIMESTAMP;
        END;
        """
        schema = self.loader.load_schema_from_string(sql_with_triggers)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "name" in schema["customers"]["columns"]
        assert "created_at" in schema["customers"]["columns"]
    
    def test_load_schema_from_string_with_complex_constraints(self):
        """Test loading schema with complex constraints"""
        complex_sql = """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL CHECK(price > 0),
            category TEXT CHECK(category IN ('electronics', 'clothing', 'books')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        schema = self.loader.load_schema_from_string(complex_sql)
        
        assert "products" in schema
        products_table = schema["products"]
        
        assert "id" in products_table["columns"]
        assert "name" in products_table["columns"]
        assert "price" in products_table["columns"]
        assert "category" in products_table["columns"]
        assert "created_at" in products_table["columns"]
        assert "updated_at" in products_table["columns"]
    
    def test_load_schema_from_string_with_aliases(self):
        """Test loading schema with table aliases"""
        sql_with_aliases = """
        CREATE TABLE customers AS cust (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        """
        schema = self.loader.load_schema_from_string(sql_with_aliases)
        
        # Should still extract the table name correctly
        assert "customers" in schema or "cust" in schema
    
    def test_load_schema_from_string_with_temporary_tables(self):
        """Test loading schema with temporary tables"""
        temp_sql = """
        CREATE TEMPORARY TABLE temp_customers (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        """
        schema = self.loader.load_schema_from_string(temp_sql)
        
        # Should handle temporary tables
        assert isinstance(schema, dict)
    
    def test_load_schema_from_string_with_if_not_exists(self):
        """Test loading schema with IF NOT EXISTS clause"""
        if_not_exists_sql = """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        """
        schema = self.loader.load_schema_from_string(if_not_exists_sql)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "name" in schema["customers"]["columns"]
    
    def test_load_schema_from_string_with_replace(self):
        """Test loading schema with REPLACE clause"""
        replace_sql = """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        
        DROP TABLE customers;
        
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT
        );
        """
        schema = self.loader.load_schema_from_string(replace_sql)
        
        assert "customers" in schema
        assert "id" in schema["customers"]["columns"]
        assert "name" in schema["customers"]["columns"]
        assert "email" in schema["customers"]["columns"]
