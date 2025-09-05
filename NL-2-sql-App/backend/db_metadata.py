"""Database metadata manager for enhanced SQL generation"""
import json
import os
from typing import Dict, Any, List, Optional, Set

class DBMetadata:
    def __init__(self, metadata_file: str = "db/db_dataset_LLM_input.json"):
        self.metadata_file = metadata_file
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from JSON file"""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {str(e)}")
            return {"tables": {}}
            
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get all column names for a table"""
        if table_name not in self.metadata["tables"]:
            return []
        return list(self.metadata["tables"][table_name]["columns"].keys())
        
    def get_column_values(self, table_name: str, column_name: str) -> List[str]:
        """Get distinct values for a column if available"""
        try:
            return self.metadata["tables"][table_name]["columns"][column_name].get("distinct_values", [])
        except KeyError:
            return []
            
    def validate_value(self, table_name: str, column_name: str, value: str) -> bool:
        """Check if a value is valid for a column"""
        values = self.get_column_values(table_name, column_name)
        if not values:  # If no distinct values defined, assume valid
            return True
        return value in values
        
    def get_column_pattern(self, table_name: str, column_name: str) -> Optional[str]:
        """Get regex pattern for a column if available"""
        try:
            return self.metadata["tables"][table_name]["columns"][column_name].get("pattern")
        except KeyError:
            return None
            
    def get_table_description(self, table_name: str) -> str:
        """Get description of a table"""
        try:
            return self.metadata["tables"][table_name]["description"]
        except KeyError:
            return ""
            
    def get_column_type(self, table_name: str, column_name: str) -> str:
        """Get data type of a column"""
        try:
            return self.metadata["tables"][table_name]["columns"][column_name]["type"]
        except KeyError:
            return "TEXT"  # Default to TEXT
            
    def is_required(self, table_name: str, column_name: str) -> bool:
        """Check if a column is required"""
        try:
            return self.metadata["tables"][table_name]["columns"][column_name].get("required", False)
        except KeyError:
            return False
            
    def get_default_value(self, table_name: str, column_name: str) -> Optional[Any]:
        """Get default value for a column if available"""
        try:
            return self.metadata["tables"][table_name]["columns"][column_name].get("default")
        except KeyError:
            return None
            
    def get_sample_values(self, table_name: str, column_name: str) -> List[str]:
        """Get sample values for a column if available"""
        try:
            return self.metadata["tables"][table_name]["columns"][column_name].get("sample_values", [])
        except KeyError:
            return []
            
    def get_llm_context(self) -> str:
        """Generate context string for LLM"""
        context = []
        for table_name, table_info in self.metadata["tables"].items():
            context.append(f"Table '{table_name}': {table_info['description']}")
            for col_name, col_info in table_info["columns"].items():
                col_desc = [f"- {col_name} ({col_info['type']})"]
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
