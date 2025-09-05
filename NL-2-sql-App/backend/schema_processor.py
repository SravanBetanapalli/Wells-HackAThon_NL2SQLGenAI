"""Process and embed database schema"""
import os
import logging
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv
from .metadata_loader import MetadataLoader

load_dotenv()
logger = logging.getLogger(__name__)

class SchemaProcessor:
    def __init__(self):
        self.openai_client = OpenAI()
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.metadata_loader = MetadataLoader()
        
    def process_schema_file(self, schema_file: str) -> List[Dict[str, Any]]:
        """Process SQL schema file into chunks"""
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        chunks = []
        current_table = None
        current_chunk = []
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
                
            if line.startswith('CREATE TABLE'):
                if current_table and current_chunk:
                    chunks.append({
                        'content': '\n'.join(current_chunk),
                        'metadata': {'type': 'table_schema', 'table': current_table}
                    })
                current_table = line.split('CREATE TABLE')[1].split('(')[0].strip().strip('`')
                current_chunk = [line]
            elif line.startswith(');'):
                if current_chunk:
                    current_chunk.append(line)
                    chunks.append({
                        'content': '\n'.join(current_chunk),
                        'metadata': {'type': 'table_schema', 'table': current_table}
                    })
                current_chunk = []
                current_table = None
            elif current_chunk is not None:
                current_chunk.append(line)
                
        return chunks

    def extract_table_info(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed table information"""
        content = chunk['content']
        table_name = chunk['metadata']['table']
        
        # Get metadata for the table
        table_metadata = self.metadata_loader.get_table_metadata(table_name) or {}
        
        # Extract columns
        columns = []
        foreign_keys = []
        
        for line in content.split('\n'):
            line = line.strip().strip(',')
            if 'FOREIGN KEY' in line:
                # Extract foreign key relationship
                parts = line.split('REFERENCES')
                local_col = parts[0].split('(')[1].split(')')[0].strip()
                ref_table = parts[1].split('(')[0].strip()
                ref_col = parts[1].split('(')[1].split(')')[0].strip()
                foreign_keys.append({
                    'column': local_col,
                    'references': f"{ref_table}.{ref_col}"
                })
            elif line and not line.startswith(('CREATE', 'PRIMARY', 'FOREIGN', ');')):
                # Extract column definition
                col_parts = line.split()
                col_name = col_parts[0].strip('`')
                col_type = col_parts[1]
                
                # Get column metadata
                col_metadata = table_metadata.get("columns", {}).get(col_name, {})
                
                columns.append({
                    'name': col_name,
                    'type': col_type,
                    'nullable': 'NOT NULL' not in line,
                    'default': col_metadata.get('default'),
                    'distinct_values': col_metadata.get('distinct_values', []),
                    'pattern': col_metadata.get('pattern')
                })
        
        return {
            'table': table_name,
            'description': table_metadata.get('description', ''),
            'columns': columns,
            'foreign_keys': foreign_keys
        }

    def generate_schema_description(self, table_info: Dict[str, Any]) -> str:
        """Generate natural language description of table schema"""
        table_name = table_info['table']
        columns = table_info['columns']
        foreign_keys = table_info['foreign_keys']
        description = table_info.get('description', '')
        
        # Basic table description
        desc_parts = [
            f"Table '{table_name}': {description}",
            "\nColumns:"
        ]
        
        # Column descriptions with metadata
        for col in columns:
            nullable = "" if col['nullable'] else " (required)"
            desc_parts.append(f"- {col['name']}: {col['type']}{nullable}")
            
            if col.get('distinct_values'):
                desc_parts.append(f"  Valid values: {', '.join(col['distinct_values'])}")
            if col.get('pattern'):
                desc_parts.append(f"  Pattern: {col['pattern']}")
            if col.get('default'):
                desc_parts.append(f"  Default: {col['default']}")
        
        # Foreign key relationships
        if foreign_keys:
            desc_parts.append("\nRelationships:")
            for fk in foreign_keys:
                desc_parts.append(f"- {fk['column']} references {fk['references']}")
        
        return '\n'.join(desc_parts)

    def initialize_schema_embeddings(self, schema_file: str):
        """Initialize ChromaDB with schema embeddings"""
        try:
            # Process schema into chunks
            chunks = self.process_schema_file(schema_file)
            logger.info(f"Processed schema into {len(chunks)} chunks")
            
            # Extract and enhance schema information
            schema_docs = []
            schema_metadatas = []
            schema_ids = []
            
            for i, chunk in enumerate(chunks):
                # Get detailed table information
                table_info = self.extract_table_info(chunk)
                
                # Generate natural language description
                description = self.generate_schema_description(table_info)
                
                schema_docs.append(description)
                schema_metadatas.append({
                    'type': 'table_schema',
                    'table': table_info['table'],
                    'columns_str': ', '.join(col['name'] for col in table_info['columns']),
                    'foreign_keys_str': ', '.join(f"{fk['column']} -> {fk['references']}" for fk in table_info['foreign_keys'])
                })
                schema_ids.append(f"schema_chunk_{i}")
            
            # Store in ChromaDB
            collection = self.chroma_client.get_or_create_collection(
                name="database_schema",
                embedding_function=self.embedding_function
            )
            
            # Get existing IDs
            try:
                existing_ids = collection.get()["ids"]
                if existing_ids:
                    collection.delete(ids=existing_ids)
            except Exception as e:
                logger.warning(f"Error clearing existing embeddings: {str(e)}")
            
            # Add new embeddings
            collection.add(
                documents=schema_docs,
                metadatas=schema_metadatas,
                ids=schema_ids
            )
            
            logger.info("Successfully initialized schema embeddings")
            
            # Log sample embeddings
            sample_query = "customers who have both checking and savings accounts"
            results = collection.query(
                query_texts=[sample_query],
                n_results=2
            )
            logger.info(f"Sample query '{sample_query}' results:")
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                logger.info(f"Table: {metadata['table']}")
                logger.info(f"Columns: {metadata.get('columns_str', '')}")
                logger.info(f"Description: {doc[:200]}...")
            
        except Exception as e:
            logger.error(f"Error initializing schema embeddings: {str(e)}")
            raise

def initialize_schema():
    """Initialize schema embeddings from SQL file"""
    schema_file = "db/schema.sql"  # Updated path
    processor = SchemaProcessor()
    processor.initialize_schema_embeddings(schema_file)