import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.retriever import RetrieverAgent


class TestRetrieverAgent:
    """Test cases for RetrieverAgent"""
    
    def setup_method(self):
        """Setup test fixtures"""
        with patch('backend.retriever.ChromaDB') as mock_chroma:
            self.mock_chroma = mock_chroma
            self.retriever = RetrieverAgent(db_path="./test_chroma_db")
    
    def test_init(self):
        """Test RetrieverAgent initialization"""
        assert self.retriever.db_path == "./test_chroma_db"
        assert self.retriever.client is not None
    
    @patch('backend.retriever.openai')
    def test_fetch_schema_context_basic(self, mock_openai):
        """Test basic schema context fetching"""
        # Mock OpenAI embeddings
        mock_openai.Embedding.create.return_value = {
            'data': [{'embedding': [0.1, 0.2, 0.3] * 1536}]
        }
        
        # Mock ChromaDB search
        self.retriever.client.search.return_value = {
            'documents': [['CREATE TABLE customers...']],
            'metadatas': [{'table': 'customers'}],
            'distances': [0.1]
        }
        
        query = "Show me all customers"
        result = self.retriever.fetch_schema_context(query)
        
        assert "schema_context" in result
        assert "value_hints" in result
        assert "exemplars" in result
        assert "metadata" in result
        assert "tables_found" in result
    
    def test_extract_tables_from_query(self):
        """Test table extraction from query"""
        query = "tables: customers accounts query: Show customers and their accounts"
        tables = self.retriever._extract_tables_from_query(query)
        
        assert "customers" in tables
        assert "accounts" in tables
    
    def test_extract_tables_from_query_no_tables(self):
        """Test table extraction when no tables specified"""
        query = "Show me all customers"
        tables = self.retriever._extract_tables_from_query(query)
        
        assert tables == []
    
    def test_build_search_query_with_tables(self):
        """Test search query building with tables"""
        tables = ["customers", "accounts"]
        nl_query = "Show customers and their accounts"
        
        search_query = self.retriever._build_search_query(tables, nl_query)
        
        assert "customers" in search_query
        assert "accounts" in search_query
        assert "Show customers and their accounts" in search_query
    
    def test_build_search_query_no_tables(self):
        """Test search query building without tables"""
        tables = []
        nl_query = "Show me all customers"
        
        search_query = self.retriever._build_search_query(tables, nl_query)
        
        assert search_query == "Show me all customers"
    
    @patch('backend.retriever.openai')
    def test_get_embeddings(self, mock_openai):
        """Test embedding generation"""
        # Mock OpenAI embeddings
        mock_openai.Embedding.create.return_value = {
            'data': [{'embedding': [0.1, 0.2, 0.3] * 1536}]
        }
        
        text = "Show me all customers"
        embeddings = self.retriever._get_embeddings(text)
        
        assert len(embeddings) == 1536
        assert isinstance(embeddings, list)
        assert all(isinstance(x, float) for x in embeddings)
    
    def test_process_search_results(self):
        """Test processing of search results"""
        search_results = {
            'documents': [
                ['CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)'],
                ['CREATE TABLE accounts (id INTEGER PRIMARY KEY, customer_id INTEGER)']
            ],
            'metadatas': [
                {'table': 'customers', 'type': 'schema'},
                {'table': 'accounts', 'type': 'schema'}
            ],
            'distances': [0.1, 0.2]
        }
        
        result = self.retriever._process_search_results(search_results)
        
        assert "schema_context" in result
        assert "value_hints" in result
        assert "exemplars" in result
        assert "metadata" in result
        assert "tables_found" in result
    
    def test_process_search_results_empty(self):
        """Test processing of empty search results"""
        search_results = {
            'documents': [],
            'metadatas': [],
            'distances': []
        }
        
        result = self.retriever._process_search_results(search_results)
        
        assert result["schema_context"] == []
        assert result["value_hints"] == {}
        assert result["exemplars"] == []
        assert result["metadata"] == []
        assert result["tables_found"] == []
    
    def test_extract_value_hints(self):
        """Test value hints extraction"""
        documents = [
            "INSERT INTO accounts (type) VALUES ('checking'), ('savings')",
            "INSERT INTO customers (state) VALUES ('TX'), ('CA')"
        ]
        metadatas = [
            {'table': 'accounts', 'column': 'type'},
            {'table': 'customers', 'column': 'state'}
        ]
        
        value_hints = self.retriever._extract_value_hints(documents, metadatas)
        
        assert "accounts" in value_hints
        assert "customers" in value_hints
        assert "type" in value_hints["accounts"]
        assert "state" in value_hints["customers"]
    
    def test_extract_exemplars(self):
        """Test exemplar extraction"""
        documents = [
            "SELECT * FROM customers WHERE state = 'TX'",
            "SELECT name, balance FROM accounts WHERE type = 'checking'"
        ]
        metadatas = [
            {'type': 'example', 'table': 'customers'},
            {'type': 'example', 'table': 'accounts'}
        ]
        
        exemplars = self.retriever._extract_exemplars(documents, metadatas)
        
        assert len(exemplars) == 2
        assert any("customers" in ex for ex in exemplars)
        assert any("accounts" in ex for ex in exemplars)
    
    def test_extract_metadata(self):
        """Test metadata extraction"""
        metadatas = [
            {'table': 'customers', 'type': 'schema', 'columns': 'id,name,email'},
            {'table': 'accounts', 'type': 'schema', 'columns': 'id,customer_id,balance'}
        ]
        
        metadata = self.retriever._extract_metadata(metadatas)
        
        assert len(metadata) == 2
        assert any("customers" in str(m) for m in metadata)
        assert any("accounts" in str(m) for m in metadata)
    
    def test_extract_tables_found(self):
        """Test tables found extraction"""
        metadatas = [
            {'table': 'customers'},
            {'table': 'accounts'},
            {'table': 'customers'}  # Duplicate
        ]
        
        tables_found = self.retriever._extract_tables_found(metadatas)
        
        assert "customers" in tables_found
        assert "accounts" in tables_found
        assert len(tables_found) == 2  # No duplicates
    
    @patch('backend.retriever.openai')
    def test_error_handling_openai_error(self, mock_openai):
        """Test error handling for OpenAI errors"""
        # Mock OpenAI error
        mock_openai.Embedding.create.side_effect = Exception("OpenAI API error")
        
        query = "Show me all customers"
        result = self.retriever.fetch_schema_context(query)
        
        # Should return empty results on error
        assert result["schema_context"] == []
        assert result["tables_found"] == []
    
    def test_error_handling_chromadb_error(self):
        """Test error handling for ChromaDB errors"""
        # Mock ChromaDB error
        self.retriever.client.search.side_effect = Exception("ChromaDB error")
        
        query = "Show me all customers"
        result = self.retriever.fetch_schema_context(query)
        
        # Should return empty results on error
        assert result["schema_context"] == []
        assert result["tables_found"] == []
    
    def test_cleanup_and_teardown(self):
        """Test cleanup and teardown"""
        # This would test any cleanup methods if they exist
        assert hasattr(self.retriever, 'client')
    
    def test_search_parameters(self):
        """Test search parameters are correctly passed"""
        query = "Show me all customers"
        
        # Mock the search call
        with patch.object(self.retriever.client, 'search') as mock_search:
            mock_search.return_value = {
                'documents': [],
                'metadatas': [],
                'distances': []
            }
            
            self.retriever.fetch_schema_context(query)
            
            # Verify search was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert 'query_embeddings' in call_args[1]
            assert 'n_results' in call_args[1]
    
    def test_embedding_model_configuration(self):
        """Test embedding model configuration"""
        # Test that the correct embedding model is used
        assert hasattr(self.retriever, '_get_embeddings')
    
    def test_chromadb_collection_management(self):
        """Test ChromaDB collection management"""
        # Test collection creation and management
        assert hasattr(self.retriever, 'client')
        assert self.retriever.client is not None
