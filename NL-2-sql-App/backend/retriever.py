"""Retriever Agent for fetching schema context"""
import chromadb
import logging
from typing import Dict, Any, List
from .logger_config import log_agent_flow
from .metadata_loader import MetadataLoader

logger = logging.getLogger(__name__)

class RetrieverAgent:
    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize with ChromaDB connection"""
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.schema_collection = self.client.get_or_create_collection("database_schema")
        self.metadata_loader = MetadataLoader()
        logger.info(f"RetrieverAgent initialized with path: {db_path}")

    @log_agent_flow("RetrieverAgent")
    def fetch_schema_context(self, query: str) -> Dict[str, Any]:
        """Fetch relevant schema context for the query"""
        logger.info(f"🔍 RetrieverAgent called with query: {query}")
        
        try:
            # Query schema collection
            results = self.schema_collection.query(
                query_texts=[query],
                n_results=3  # Get top 3 most relevant schema chunks
            )
            
            if not results["documents"] or not results["documents"][0]:
                logger.warning("No schema context found in ChromaDB, using fallback")
                return self._get_fallback_schema()
            
            # Extract schema information
            schema_context = []
            tables_found = set()
            
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                schema_context.append(doc)
                if metadata and metadata.get('table'):
                    tables_found.add(metadata['table'])
            
            # Enhance context with metadata
            enhanced_context = []
            for table in tables_found:
                table_metadata = self.metadata_loader.get_table_metadata(table)
                if table_metadata:
                    enhanced_context.append(f"\nTable '{table}' metadata:")
                    for col_name, col_info in table_metadata.get('columns', {}).items():
                        if col_info.get('distinct_values'):
                            enhanced_context.append(
                                f"- {col_name}: Valid values = {', '.join(col_info['distinct_values'])}"
                            )
            
            if enhanced_context:
                schema_context.extend(enhanced_context)
            
            logger.info(f"✅ Retrieved schema context for tables: {', '.join(tables_found)}")
            
            return {
                "schema_context": schema_context,
                "tables_found": list(tables_found),
                "metadata": results["metadatas"][0] if results["metadatas"] else []
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving schema context: {str(e)}")
            return self._get_fallback_schema()

    def _get_fallback_schema(self) -> Dict[str, Any]:
        """Provide fallback schema information"""
        logger.info("Using fallback schema from metadata loader")
        
        try:
            # Use metadata for fallback
            metadata = self.metadata_loader.get_metadata()
            schema_context = []
            tables_found = []
            
            for table_name, table_info in metadata.get('tables', {}).items():
                tables_found.append(table_name)
                schema_context.append(f"Table '{table_name}': {table_info.get('description', '')}")
                
                # Add column information
                for col_name, col_info in table_info.get('columns', {}).items():
                    if col_info.get('distinct_values'):
                        schema_context.append(
                            f"- {col_name}: Valid values = {', '.join(col_info['distinct_values'])}"
                        )
            
            logger.info(f"✅ Fallback schema prepared with {len(tables_found)} tables")
            
            return {
                "schema_context": schema_context,
                "tables_found": tables_found,
                "metadata": []
            }
            
        except Exception as e:
            logger.error(f"❌ Error in fallback schema: {str(e)}")
            return {
                "schema_context": ["Error loading schema"],
                "tables_found": [],
                "metadata": []
            }

    @log_agent_flow("RetrieverAgent")
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get columns for a specific table"""
        try:
            # First try ChromaDB
            results = self.schema_collection.query(
                query_texts=[f"table {table_name} columns"],
                n_results=1
            )
            
            if results["metadatas"]:
                columns_str = results["metadatas"][0][0].get('columns_str', '')
                if columns_str:
                    return columns_str.split(', ')
            
            # Fallback to metadata
            table_metadata = self.metadata_loader.get_table_metadata(table_name)
            if table_metadata:
                return list(table_metadata.get('columns', {}).keys())
            
        except Exception as e:
            logger.error(f"Error retrieving columns for table {table_name}: {str(e)}")
        
        return []

    @log_agent_flow("RetrieverAgent")
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        """Get foreign key relationships for a table"""
        try:
            # First try ChromaDB
            results = self.schema_collection.query(
                query_texts=[f"table {table_name} foreign keys"],
                n_results=1
            )
            
            if results["metadatas"]:
                fk_str = results["metadatas"][0][0].get('foreign_keys_str', '')
                if fk_str:
                    fk_list = []
                    for fk in fk_str.split(', '):
                        if '->' in fk:
                            col, ref = fk.split(' -> ')
                            fk_list.append({
                                'column': col.strip(),
                                'references': ref.strip()
                            })
                    return fk_list
            
            # Fallback to metadata
            table_metadata = self.metadata_loader.get_table_metadata(table_name)
            if table_metadata:
                return table_metadata.get('foreign_keys', [])
            
        except Exception as e:
            logger.error(f"Error retrieving foreign keys for table {table_name}: {str(e)}")
        
        return []

    def get_column_values(self, table_name: str, column_name: str) -> List[str]:
        """Get valid values for a column"""
        return self.metadata_loader.get_distinct_values(table_name, column_name)

    def validate_value(self, table_name: str, column_name: str, value: str) -> bool:
        """Validate a value against known valid values"""
        return self.metadata_loader.validate_value(table_name, column_name, value)