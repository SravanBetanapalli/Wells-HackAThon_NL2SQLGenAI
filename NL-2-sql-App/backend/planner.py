# backend/planner.py
from typing import Dict, List, Any, Optional
import re
import json
import logging
from datetime import datetime
from .metadata_loader import MetadataLoader
from .logger_config import log_agent_flow

logger = logging.getLogger(__name__)

class PlannerAgent:
    """
    PlannerAgent analyzes a natural-language query and returns:
      - tables: list of likely relevant tables
      - steps: ordered actions for pipeline
      - capabilities: short tags (exists, group_by, date_filter, window, etc.)
      - clarifications: if any ambiguity detected (thresholds, date ranges)
      - conversation_state: optional lightweight context to carry across turns
    """
    DATE_WORDS = ["q1", "q2", "q3", "q4", "quarter", "year", "month", "week", "today", "yesterday", "last", "first quarter", "2024", "2025"]
    AGG_WORDS = ["average", "avg", "sum", "count", "total", "number of", "how many"]
    EXISTS_WORDS = ["both", "either", "and", "have both", "have both a", "have both an"]
    WINDOW_WORDS = ["consecutive", "consecutive days", "lag", "lead"]
    WEEKEND_WORDS = ["weekend", "saturday", "sunday"]
    THRESHOLD_WORDS = ["greater than", "less than", "above", "below", "minimum", "max", "at least", "more than"]

    def __init__(self, schema_map: Dict[str, List[str]], conversation_state: Optional[Dict[str, Any]] = None):
        """
        schema_map: {"customers": ["id","first_name",...], "accounts": [...], ...}
        conversation_state: optional prior context (last_tables, last_filters)
        """
        self.schema_map = schema_map
        self.conversation_state = conversation_state or {}
        self.metadata_loader = MetadataLoader()

    def _detect_tables(self, text: str) -> List[str]:
        found = []
        tl = text.lower()
        
        # Check for table names
        for table in self.schema_map.keys():
            if table.lower() in tl:
                found.append(table)
                logger.info(f"📌 Found direct table mention: {table}")
        
        # Check for column values that might indicate tables
        metadata = self.metadata_loader.get_metadata()
        for table_name, table_info in metadata.get('tables', {}).items():
            for col_name, col_info in table_info.get('columns', {}).items():
                if col_info.get('distinct_values'):
                    matches = [val for val in col_info['distinct_values'] if val.lower() in tl]
                    if matches:
                        found.append(table_name)
                        logger.info(f"📌 Found table {table_name} via column value matches: {matches}")
                        break
        
        # Log heuristic matches
        if not found:
            heuristic_matches = []
            if "customer" in tl: 
                matches = [t for t in self.schema_map if "customer" in t]
                heuristic_matches.extend([("customer", m) for m in matches])
            if "account" in tl: 
                matches = [t for t in self.schema_map if "account" in t]
                heuristic_matches.extend([("account", m) for m in matches])
            if "transaction" in tl or "transactions" in tl: 
                matches = [t for t in self.schema_map if "transaction" in t]
                heuristic_matches.extend([("transaction", m) for m in matches])
            if "employee" in tl or "employees" in tl: 
                matches = [t for t in self.schema_map if "employee" in t]
                heuristic_matches.extend([("employee", m) for m in matches])
            if "branch" in tl or "branches" in tl: 
                matches = [t for t in self.schema_map if "branch" in t]
                heuristic_matches.extend([("branch", m) for m in matches])
            
            if heuristic_matches:
                logger.info("\n📌 Found tables via heuristics:")
                logger.info(json.dumps({"heuristic_matches": heuristic_matches}, indent=2))
                found.extend([m[1] for m in heuristic_matches])
        
        # unique preserving order
        unique_tables = list(dict.fromkeys(found)) or list(self.schema_map.keys())
        
        logger.info("\n📊 Table Detection Summary:")
        logger.info(json.dumps({
            "input_text": text,
            "tables_found": unique_tables,
            "total_tables": len(unique_tables),
            "fallback_to_all": len(found) == 0
        }, indent=2))
        
        return unique_tables

    def _detect_capabilities(self, text: str) -> List[str]:
        caps = set()
        tl = text.lower()
        
        # Standard capability detection
        if any(w in tl for w in self.AGG_WORDS): caps.add("aggregate")
        if any(w in tl for w in self.EXISTS_WORDS): caps.add("exists")
        if any(w in tl for w in self.WINDOW_WORDS): caps.add("window")
        if any(w in tl for w in self.WEEKEND_WORDS): caps.add("weekend")
        if any(w in tl for w in self.DATE_WORDS): caps.add("date_filter")
        if any(w in tl for w in self.THRESHOLD_WORDS): caps.add("threshold")
        
        # Metadata-based capability detection
        metadata = self.metadata_loader.get_metadata()
        
        # Check for specific account types
        if "accounts" in metadata.get('tables', {}):
            account_types = metadata['tables']['accounts']['columns'].get('type', {}).get('distinct_values', [])
            if any(acc_type.lower() in tl for acc_type in account_types):
                caps.add("account_type_filter")
        
        # Check for specific transaction types
        if "transactions" in metadata.get('tables', {}):
            transaction_types = metadata['tables']['transactions']['columns'].get('type', {}).get('distinct_values', [])
            if any(tx_type.lower() in tl for tx_type in transaction_types):
                caps.add("transaction_type_filter")
        
        # Check for specific employee positions
        if "employees" in metadata.get('tables', {}):
            positions = metadata['tables']['employees']['columns'].get('position', {}).get('distinct_values', [])
            if any(pos.lower() in tl for pos in positions):
                caps.add("position_filter")
        
        # detect join hint
        if "manager" in tl or "handled by" in tl or "handled" in tl: caps.add("join_employees")
        
        return sorted(list(caps))

    def _detect_clarifications(self, text: str) -> List[Dict[str, Any]]:
        tl = text.lower()
        clar = []
        
        # Get metadata for thresholds
        metadata = self.metadata_loader.get_metadata()
        
        # threshold numeric missing
        if any(k in tl for k in ["high value", "high balance", "rich", "wealthy"]) and not re.search(r"\b\d{2,}\b", text):
            # Check typical account balances from metadata if available
            default_threshold = 20000  # Default fallback
            if "accounts" in metadata.get('tables', {}):
                balance_info = metadata['tables']['accounts']['columns'].get('balance', {})
                if 'typical_high' in balance_info:
                    default_threshold = balance_info['typical_high']
            clar.append({
                "field": "min_balance",
                "prompt": "What minimum balance should count as 'high'?",
                "type": "number",
                "default": default_threshold
            })
        
        # ambiguous timeframe
        if "recent" in tl or "last" in tl and not re.search(r"\b(20\d{2}|202\d)\b", text):
            clar.append({
                "field": "date_range",
                "prompt": "What date range do you mean by 'recent'?",
                "type": "text",
                "default": "last 30 days"
            })
        
        # explicit q1 text -> convert to date_range default
        if "q1" in tl or "first quarter" in tl:
            clar.append({
                "field": "date_range",
                "prompt": "Confirm date range for Q1",
                "type": "text",
                "default": "2025-01-01..2025-03-31"
            })
        
        # Check for ambiguous account types
        if "account" in tl and not any(acc_type in tl for acc_type in self.metadata_loader.get_distinct_values('accounts', 'type')):
            clar.append({
                "field": "account_type",
                "prompt": "What type of account are you interested in?",
                "type": "select",
                "options": self.metadata_loader.get_distinct_values('accounts', 'type'),
                "default": "checking"
            })
        
        return clar

    @log_agent_flow("PlannerAgent")
    def analyze_query(self, nl_query: str) -> Dict[str, Any]:
        """
        Main entrypoint. Returns structured plan dict.
        """
        # Log input
        input_data = {
            "query": nl_query,
            "schema_tables": list(self.schema_map.keys()),
            "conversation_state": self.conversation_state
        }
        logger.info("\n🔍 PlannerAgent Input:")
        logger.info(json.dumps(input_data, indent=2))

        if not nl_query or not nl_query.strip():
            empty_plan = {
                "tables": list(self.schema_map.keys()),
                "steps": [{"action":"fetch_schema","tables": list(self.schema_map.keys())}],
                "capabilities": [],
                "clarifications": []
            }
            logger.info("\n📋 PlannerAgent Output (Empty Query):")
            logger.info(json.dumps(empty_plan, indent=2))
            return empty_plan

        # Detect components
        tables = self._detect_tables(nl_query)
        capabilities = self._detect_capabilities(nl_query)
        clarifications = self._detect_clarifications(nl_query)
        
        # Generate intelligent follow-up suggestions
        follow_up_suggestions = self._generate_follow_up_suggestions(nl_query, tables, capabilities)

        steps = [
            {"action":"fetch_schema","tables": tables},
            {"action":"retrieve_examples","tables": tables},
            {"action":"generate_sql"},
            {"action":"validate_sql"},
            {"action":"execute_sql"}
        ]

        # Add metadata context
        metadata_context = {}
        for table in tables:
            table_metadata = self.metadata_loader.get_table_metadata(table)
            if table_metadata:
                metadata_context[table] = {
                    "description": table_metadata.get("description", ""),
                    "columns": table_metadata.get("columns", {})
                }

        # Create plan
        plan = {
            "query": nl_query,
            "tables": tables,
            "steps": steps,
            "capabilities": capabilities,
            "clarifications": clarifications,
            "follow_up_suggestions": follow_up_suggestions,
            "conversation_state": self.conversation_state,
            "metadata_context": metadata_context
        }

        # Log detailed analysis
        analysis = {
            "detected_tables": {
                "tables_found": tables,
                "total_tables": len(tables)
            },
            "detected_capabilities": {
                "capabilities": capabilities,
                "total_capabilities": len(capabilities)
            },
            "needs_clarification": len(clarifications) > 0,
            "clarifications": clarifications,
            "suggested_steps": steps,
            "metadata_context_summary": {
                table: {
                    "description": meta.get("description", ""),
                    "column_count": len(meta.get("columns", {}))
                }
                for table, meta in metadata_context.items()
            }
        }
        
        logger.info("\n📋 PlannerAgent Analysis:")
        logger.info(json.dumps(analysis, indent=2))
        
        logger.info("\n📋 PlannerAgent Output Plan:")
        logger.info(json.dumps(plan, indent=2))
        
        return plan

    def _generate_follow_up_suggestions(self, query: str, tables: List[str], capabilities: List[str]) -> List[str]:
        """Generate intelligent follow-up questions based on the current query"""
        query_lower = query.lower()
        suggestions = []
        
        # Branch-related suggestions
        if "branch" in query_lower or "branches" in query_lower:
            if "transaction" in query_lower:
                suggestions.extend([
                    "Show me the bottom 5 performing branches",
                    "What's the average transaction amount by branch?",
                    "Show me branch performance by month",
                    "Compare branch performance by employee count"
                ])
            else:
                suggestions.extend([
                    "Show me the top 10 branches by transaction volume",
                    "Which branches have the most employees?",
                    "Show me branch performance by revenue",
                    "What's the average account balance by branch?"
                ])
        
        # Account-related suggestions with metadata
        if "account" in query_lower or "balance" in query_lower:
            account_types = self.metadata_loader.get_distinct_values('accounts', 'type')
            if len(account_types) >= 2:
                suggestions.append(f"Show me customers with both {account_types[0]} and {account_types[1]} accounts")
            suggestions.extend([
                "Show me the top 10 accounts by balance",
                "What's the average account balance?",
                "Show me account distribution by type"
            ])
        
        # Employee-related suggestions with metadata
        if "employee" in query_lower or "salary" in query_lower:
            positions = self.metadata_loader.get_distinct_values('employees', 'position')
            if positions:
                suggestions.append(f"Show me all {positions[0]}s")
            suggestions.extend([
                "Show me the top 10 highest paid employees",
                "What's the average employee salary?",
                "Show me salary distribution by position"
            ])
        
        # Transaction-related suggestions with metadata
        if "transaction" in query_lower:
            transaction_types = self.metadata_loader.get_distinct_values('transactions', 'type')
            if transaction_types:
                suggestions.append(f"Show me all {transaction_types[0]} transactions")
            suggestions.extend([
                "Show me transaction trends by month",
                "What's the average transaction amount?",
                "Show me transactions by type"
            ])
        
        # General database exploration suggestions
        if not suggestions:
            suggestions.extend([
                "Show me the count of rows by each table",
                "What's the top performing branch?",
                "Show me the highest balance account",
                "Which employee has the highest salary?"
            ])
        
        return suggestions[:4]  # Limit to 4 suggestions