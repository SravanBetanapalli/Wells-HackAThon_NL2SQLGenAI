"""Metadata loader for database schema information"""
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MetadataLoader:
    _instance = None
    _metadata = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetadataLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._metadata is None:
            self.load_metadata()

    def load_metadata(self) -> None:
        """Load metadata from JSON file"""
        try:
            metadata_path = Path("db/db_dataset_LLM_input.json")
            
            if not metadata_path.exists():
                logger.error(f"Metadata file does not exist: {metadata_path.absolute()}")
                self._metadata = {"tables": {}}
                return
                
            with open(metadata_path, 'r') as f:
                self._metadata = json.load(f)
                
            logger.info(f"Successfully loaded schema metadata with {len(self._metadata.get('tables', {}))} tables")
            
        except Exception as e:
            logger.error(f"Error loading metadata: {str(e)}")
            self._metadata = {"tables": {}}

    def get_metadata(self) -> Dict[str, Any]:
        """Get the full metadata"""
        if self._metadata is None:
            logger.warning("Metadata is None, re-loading...")
            self.load_metadata()
        return self._metadata

    def get_table_metadata(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific table"""
        return self._metadata.get("tables", {}).get(table_name)

    def get_column_metadata(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific column"""
        table = self.get_table_metadata(table_name)
        if table:
            return table.get("columns", {}).get(column_name)
        return None

    def get_distinct_values(self, table_name: str, column_name: str) -> list:
        """Get distinct values for a column if available"""
        column = self.get_column_metadata(table_name, column_name)
        if column:
            return column.get("distinct_values", [])
        return []

    def get_column_pattern(self, table_name: str, column_name: str) -> Optional[str]:
        """Get regex pattern for a column if available"""
        column = self.get_column_metadata(table_name, column_name)
        if column:
            return column.get("pattern")
        return None

    def get_table_description(self, table_name: str) -> str:
        """Get description of a table"""
        table = self.get_table_metadata(table_name)
        if table:
            return table.get("description", "")
        return ""

    def validate_value(self, table_name: str, column_name: str, value: str) -> bool:
        """Check if a value is valid for a column"""
        values = self.get_distinct_values(table_name, column_name)
        if not values:  # If no distinct values defined, assume valid
            return True
        return value in values

    def get_llm_context(self) -> str:
        """Generate context string for LLM"""
        context = []
        for table_name, table_info in self._metadata.get("tables", {}).items():
            context.append(f"Table '{table_name}': {table_info.get('description', '')}")
            for col_name, col_info in table_info.get("columns", {}).items():
                col_desc = [f"- {col_name} ({col_info.get('type', 'TEXT')})"]
                if col_info.get("required"):
                    col_desc.append("required")
                if col_info.get("primary_key"):
                    col_desc.append("primary key")
                if "distinct_values" in col_info:
                    col_desc.append(f"values: {', '.join(col_info['distinct_values'])}")
                if "default" in col_info:
                    col_desc.append(f"default: {col_info['default']}")
                context.append(" ".join(col_desc))
        return "\n".join(context)
