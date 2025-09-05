"""LLM Prompt Builder with Schema-Infused, Few-Shot, and Chain-of-Thought Prompting"""
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class QueryExample:
    """Stores example NL queries and their SQL translations with reasoning"""
    nl_query: str
    sql_query: str
    suggestion: str
    reasoning_steps: List[str]
    tables_used: List[str]
    key_columns: List[str]
    conditions: List[str]

@dataclass
class QueryHistory:
    """Stores history of NL queries and their SQL translations"""
    nl_query: str
    generated_sql: str
    suggestion: str
    was_successful: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error_context: Optional[Dict[str, Any]] = None
    reasoning_steps: List[str] = field(default_factory=list)

@dataclass
class PromptContext:
    """Maintains context for the prompting session"""
    schema_metadata: Dict[str, Any]
    foreign_keys: Dict[str, List[Dict[str, str]]]
    query_history: List[QueryHistory] = field(default_factory=list)
    conversation_context: Dict[str, Any] = field(default_factory=dict)

class PromptingAgent:
    """Agent responsible for building and maintaining LLM prompts with schema-infused reasoning"""

    def __init__(self):
        self.context: Optional[PromptContext] = None
        self.max_history = 3
        self.example_queries = self._initialize_example_queries()
        logger.info("🔄 Initialized PromptingAgent")

    def _initialize_example_queries(self) -> List[QueryExample]:
        """Initialize example queries with detailed reasoning"""
        return [
            QueryExample(
                nl_query="List all branches and their managers' names. Include branches without a manager.",
                sql_query="""
                    SELECT 
                        b.name AS branch_name,
                        e.name AS manager_name
                    FROM branches b
                    LEFT JOIN employees e 
                        ON b.manager_id = e.id 
                        AND e.position = 'Branch Manager'
                    ORDER BY b.name;
                """,
                suggestion="This query retrieves all bank branches and their corresponding manager names, using a LEFT JOIN to include branches that don't have a manager assigned. Results are ordered by branch name for easy reading.",
                reasoning_steps=[
                    "1. Identify main entity: branches table (contains branch information)",
                    "2. Need manager names: requires join with employees table",
                    "3. Use LEFT JOIN to include branches without managers",
                    "4. Filter for Branch Manager position in employees",
                    "5. Order by branch name for readability"
                ],
                tables_used=["branches", "employees"],
                key_columns=["branches.manager_id", "employees.id", "employees.position"],
                conditions=["e.position = 'Branch Manager'"]
            ),
            QueryExample(
                nl_query="Find customers who have both checking and savings accounts.",
                sql_query="""
                    SELECT DISTINCT
                        c.first_name || ' ' || c.last_name AS customer_name,
                        c.email,
                        c.phone
                    FROM customers c
                    JOIN accounts a1 
                        ON c.id = a1.customer_id 
                        AND a1.type = 'checking' 
                        AND a1.status = 'active'
                    JOIN accounts a2 
                        ON c.id = a2.customer_id 
                        AND a2.type = 'savings' 
                        AND a2.status = 'active'
                    ORDER BY customer_name;
                """,
                suggestion="This query finds customers with both checking and savings accounts by joining the customers table twice with the accounts table. It only considers active accounts and returns customer details ordered by name.",
                reasoning_steps=[
                    "1. Start with customers table for personal info",
                    "2. Need two joins to accounts (a1, a2) to check both account types",
                    "3. Filter for active accounts only",
                    "4. Use DISTINCT to avoid duplicates",
                    "5. Concatenate first and last names for readability"
                ],
                tables_used=["customers", "accounts"],
                key_columns=["customers.id", "accounts.customer_id", "accounts.type", "accounts.status"],
                conditions=["a1.type = 'checking'", "a2.type = 'savings'", "status = 'active'"]
            )
        ]

    def initialize_context(self, schema_metadata: Dict[str, Any], foreign_keys: Dict[str, List[Dict[str, str]]]) -> None:
        """Initialize or update the context with schema information"""
        try:
            logger.info("🔄 Initializing PromptingAgent context")
            
            # Log schema metadata structure
            logger.info("📊 Schema metadata structure:")
            logger.info(f"- Tables: {list(schema_metadata.get('tables', {}).keys())}")
            logger.info(f"- Foreign keys: {len(foreign_keys)} relationships")
            
            # Create new context
            self.context = PromptContext(
                schema_metadata=schema_metadata,
                foreign_keys=foreign_keys,
                query_history=[],
                conversation_context={}
            )
            
            # Validate schema metadata
            if not schema_metadata or not isinstance(schema_metadata, dict):
                raise ValueError("Invalid schema metadata format")
            
            if 'tables' not in schema_metadata:
                raise ValueError("Schema metadata missing 'tables' key")
            
            # Validate foreign keys
            for table, fks in foreign_keys.items():
                if not isinstance(fks, list):
                    raise ValueError(f"Foreign keys for table {table} must be a list")
                for fk in fks:
                    if not isinstance(fk, dict) or 'column' not in fk or 'references' not in fk:
                        raise ValueError(f"Invalid foreign key format in table {table}")
            
            # Log successful initialization
            table_info = {
                table: {
                    "columns": len(table_data.get("columns", {})),
                    "has_description": bool(table_data.get("description")),
                    "foreign_keys": len(foreign_keys.get(table, []))
                }
                for table, table_data in schema_metadata.get("tables", {}).items()
            }
            
            logger.info("✅ Context initialization complete")
            logger.debug(f"Table information:\n{json.dumps(table_info, indent=2)}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing context: {str(e)}")
            raise ValueError(f"Failed to initialize context: {str(e)}")

    def _build_schema_infused_context(self) -> Dict[str, Any]:
        """Build comprehensive schema context with relationships and constraints"""
        if not self.context:
            raise ValueError("Context not initialized. Call initialize_context first.")
            
        try:
            logger.info("🔄 Building schema-infused context")
            
            schema_context = {
                "tables": {},
                "relationships": [],
                "constraints": [],
                "value_domains": {}
            }
            
            # Process each table
            for table_name, table_info in self.context.schema_metadata["tables"].items():
                logger.debug(f"Processing table: {table_name}")
                
                table_context = {
                    "name": table_name,
                    "description": table_info["description"],
                    "columns": {},
                    "primary_key": None,
                    "indexes": [],
                    "foreign_keys": []
                }
                
                # Process columns
                for col_name, col_info in table_info["columns"].items():
                    column_context = {
                        "name": col_name,
                        "type": col_info["type"],
                        "constraints": []
                    }
                    
                    # Add constraints
                    if col_info.get("primary_key"):
                        column_context["constraints"].append("PRIMARY KEY")
                        table_context["primary_key"] = col_name
                    if col_info.get("required"):
                        column_context["constraints"].append("NOT NULL")
                    if "default" in col_info:
                        column_context["constraints"].append(f"DEFAULT: {col_info['default']}")
                    
                    # Add patterns and valid values
                    if "pattern" in col_info:
                        column_context["pattern"] = col_info["pattern"]
                    if "distinct_values" in col_info:
                        column_context["valid_values"] = col_info["distinct_values"]
                        schema_context["value_domains"][f"{table_name}.{col_name}"] = col_info["distinct_values"]
                    
                    table_context["columns"][col_name] = column_context
                
                # Add foreign key relationships
                if table_name in self.context.foreign_keys:
                    for fk in self.context.foreign_keys[table_name]:
                        fk_info = {
                            "from": f"{table_name}.{fk['column']}",
                            "to": fk["references"]
                        }
                        table_context["foreign_keys"].append(fk_info)
                        schema_context["relationships"].append(fk_info)
                
                schema_context["tables"][table_name] = table_context
                
                # Log table processing completion
                logger.debug(f"✅ Processed table {table_name}: {len(table_context['columns'])} columns, {len(table_context['foreign_keys'])} foreign keys")
            
            logger.info("✅ Successfully built schema context")
            return schema_context
            
        except Exception as e:
            logger.error(f"❌ Error building schema context: {str(e)}")
            raise

    def _build_chain_of_thought_steps(self, query: str, detected_tables: List[str], 
                                    capabilities: List[str]) -> List[str]:
        """Build detailed chain-of-thought reasoning steps"""
        try:
            logger.info("🤔 Building chain-of-thought reasoning steps")
            steps = []
            
            # Step 1: Entity Identification
            query_lower = query.lower()
            entity_words = {
                "customer": ("customers", "person who has accounts"),
                "account": ("accounts", "banking account"),
                "branch": ("branches", "bank location"),
                "employee": ("employees", "bank staff"),
                "manager": ("employees", "branch manager"),
                "transaction": ("transactions", "account activity")
            }
            
            identified_entities = []
            for word, (table, description) in entity_words.items():
                if word in query_lower and table in detected_tables:
                    identified_entities.append(f"{word} ({description})")
            
            if identified_entities:
                steps.append(f"1. Identified entities: {', '.join(identified_entities)}")
            
            # Step 2: Schema Mapping
            if detected_tables:
                table_mappings = []
                for table in detected_tables:
                    table_info = self.context.schema_metadata["tables"].get(table, {})
                    columns = table_info.get("columns", {})
                    key_columns = [col for col, info in columns.items() 
                                 if info.get("primary_key") or info.get("required")]
                    if key_columns:
                        table_mappings.append(f"{table} (key columns: {', '.join(key_columns)})")
                if table_mappings:
                    steps.append(f"2. Required tables: {', '.join(table_mappings)}")
            
            # Step 3: Join Analysis
            if len(detected_tables) > 1:
                joins = []
                for i in range(len(detected_tables)-1):
                    table1, table2 = detected_tables[i:i+2]
                    for fk in self.context.foreign_keys.get(table1, []):
                        if fk["references"].split(".")[0] == table2:
                            joins.append(f"{table1} → {table2} via {fk['column']}")
                if joins:
                    steps.append(f"3. Join path: {' then '.join(joins)}")
            
            # Step 4: Conditions
            conditions = []
            if "aggregate" in capabilities:
                conditions.append("Apply aggregation functions")
            if "date_filter" in capabilities:
                conditions.append("Add date range filters")
            if any(t in detected_tables for t in ["accounts", "transactions"]):
                conditions.append("Check status='active' where applicable")
            
            # Add value domain conditions
            for table in detected_tables:
                table_info = self.context.schema_metadata["tables"].get(table, {})
                for col_name, col_info in table_info.get("columns", {}).items():
                    if col_info.get("distinct_values"):
                        values = col_info["distinct_values"]
                        if any(val in query_lower for val in values):
                            conditions.append(f"Validate {table}.{col_name} against allowed values: {', '.join(values)}")
            
            if conditions:
                steps.append(f"4. Required conditions: {', '.join(conditions)}")
            
            # Step 5: Output Planning
            outputs = []
            if "customers" in detected_tables:
                outputs.append("Concatenate first_name and last_name")
            if "aggregate" in capabilities:
                outputs.append("Include aggregated values")
            if any(word in query_lower for word in ["order", "sort", "rank"]):
                outputs.append("Add ORDER BY clause")
            if outputs:
                steps.append(f"5. Output formatting: {', '.join(outputs)}")
            
            logger.info(f"✅ Generated {len(steps)} reasoning steps")
            return steps
            
        except Exception as e:
            logger.error(f"❌ Error building reasoning steps: {str(e)}")
            # Return basic steps as fallback
            return [
                "1. Identify entities in the question",
                "2. Map to relevant tables/columns",
                "3. Plan necessary joins/filters",
                "4. Determine output columns",
                "5. Consider ordering and grouping"
            ]

    def build_prompt(self, query: str, detected_tables: List[str], 
                    capabilities: List[str], error_context: Optional[Dict[str, Any]] = None) -> str:
        """Build a complete structured prompt with schema-infused reasoning"""
        if not self.context:
            raise ValueError("Context not initialized. Call initialize_context first.")

        try:
            # Build chain-of-thought reasoning steps
            reasoning_steps = self._build_chain_of_thought_steps(query, detected_tables, capabilities)
            logger.info(f"Generated {len(reasoning_steps)} reasoning steps")
            
            # Get relevant examples
            relevant_examples = self._find_relevant_examples(query, detected_tables)
            logger.info(f"Found {len(relevant_examples)} relevant examples")
            
            # Build the complete prompt structure
            prompt = {
                "critical_requirements": {
                    "schema_adherence": [
                        "ONLY use columns that exist in the provided schema metadata",
                        "Verify each column name against the schema before using",
                        "Check data types and constraints from schema"
                    ],
                    "aggregation_guidelines": [
                        "Add COUNT, SUM, AVG where relevant to provide insights",
                        "Include GROUP BY when using aggregations",
                        "Consider HAVING clauses for aggregate filters"
                    ],
                    "join_validation": [
                        "Verify all required joins based on foreign key relationships",
                        "Use appropriate JOIN types (LEFT, INNER) based on requirements",
                        "Include all necessary join conditions"
                    ],
                    "where_conditions": [
                        "Add status='active' checks where applicable",
                        "Include date range filters when temporal context exists",
                        "Validate values against domain constraints"
                    ]
                },
                
                "analysis_steps": [
                    "1. Identify entities and columns from schema metadata",
                    "2. Map identified elements to relevant tables/columns",
                    "3. Plan necessary joins using foreign key relationships",
                    "4. Determine required aggregations and grouping",
                    "5. Add appropriate WHERE conditions and filters",
                    "6. Structure the final SQL query",
                    "7. Validate against schema constraints",
                    "8. Provide reasoning for choices made"
                ],
                
                "task": {
                    "objective": "Generate a SQLite SQL query",
                    "input_query": query,
                    "context": "Banking database query generation",
                    "output_format": {
                        "type": "json",
                        "structure": {
                            "SQLQuery": "The executable SQL query that fulfills the request",
                            "Suggestion": "A natural language description of what the SQL query does",
                            "Reasoning": {
                                "identified_entities": ["List of tables and columns identified"],
                                "join_logic": ["Explanation of join relationships used"],
                                "aggregation_choices": ["Why certain aggregations were added"],
                                "filter_conditions": ["Reasoning for WHERE conditions"]
                            }
                        }
                    }
                },
                
                "schema_context": self._build_schema_infused_context(),
                
                "reasoning": {
                    "chain_of_thought": {
                        "steps": reasoning_steps,
                        "explanation": "Following systematic analysis process"
                    },
                    "detected_capabilities": capabilities,
                    "required_tables": detected_tables
                },
                
                "examples": [
                    {
                        "natural_language": ex.nl_query,
                        "output": {
                            "SQLQuery": ex.sql_query.strip(),
                            "Suggestion": ex.suggestion,
                            "Reasoning": {
                                "identified_entities": [f"Using {table} for {purpose}" 
                                                     for table, purpose in [("primary data", "main entity"), ("related info", "related data")]],
                                "join_logic": [f"Joining {col}" for col in ex.key_columns],
                                "filter_conditions": ex.conditions
                            }
                        }
                    }
                    for ex in relevant_examples
                ],
                
                "requirements": {
                    "output_format": [
                        "Return a JSON object with SQLQuery, Suggestion, and Reasoning",
                        "SQLQuery must contain only the executable SQL query",
                        "Suggestion must provide a clear description of the query's purpose",
                        "Reasoning must explain all key decisions made"
                    ],
                    "schema_validation": [
                        "Verify every column exists in schema",
                        "Check data types match schema",
                        "Validate against domain constraints"
                    ],
                    "join_requirements": [
                        "Use proper table aliases",
                        "Include all necessary join conditions",
                        "Follow foreign key relationships"
                    ],
                    "aggregation_rules": [
                        "Add appropriate GROUP BY clauses",
                        "Consider HAVING for aggregate filters",
                        "Use DISTINCT when needed"
                    ],
                    "filter_guidelines": [
                        "Add status checks where relevant",
                        "Include date filters when needed",
                        "Validate literal values"
                    ]
                }
            }

            if error_context:
                prompt["error_context"] = {
                    "previous_error": error_context,
                    "correction_focus": [
                        "Verify column names against schema",
                        "Check join conditions",
                        "Validate value domains",
                        "Review aggregation logic"
                    ]
                }

            logger.info("✅ Successfully built prompt")
            return json.dumps(prompt, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Error building prompt: {str(e)}")
            raise

    def _find_relevant_examples(self, query: str, detected_tables: List[str]) -> List[QueryExample]:
        """Find relevant example queries based on similarity"""
        try:
            logger.info(f"🔍 Finding relevant examples for query: {query}")
            logger.info(f"📊 Detected tables: {detected_tables}")
            
            relevant_examples = []
            query_lower = query.lower()
            
            for example in self.example_queries:
                # Check table overlap
                table_overlap = set(example.tables_used) & set(detected_tables)
                
                # Check query similarity
                query_keywords = set(query_lower.split())
                example_keywords = set(example.nl_query.lower().split())
                keyword_overlap = query_keywords & example_keywords
                
                if table_overlap and keyword_overlap:
                    logger.debug("✅ Found relevant example:")
                    logger.debug(f"- Query: {example.nl_query}")
                    logger.debug(f"- Matching tables: {list(table_overlap)}")
                    logger.debug(f"- Matching keywords: {list(keyword_overlap)}")
                    relevant_examples.append(example)
            
            logger.info(f"📚 Found {len(relevant_examples)} relevant examples")
            return relevant_examples[:2]  # Return top 2 most relevant examples
            
        except Exception as e:
            logger.error(f"❌ Error finding relevant examples: {str(e)}")
            return []

    def add_query_to_history(self, nl_query: str, sql: str, suggestion: str, success: bool, 
                           error_context: Optional[Dict[str, Any]] = None,
                           reasoning: List[str] = None):
        """Add a query and its result to history"""
        if not self.context:
            raise ValueError("Context not initialized. Call initialize_context first.")
        
        history_entry = QueryHistory(
            nl_query=nl_query,
            generated_sql=sql,
            suggestion=suggestion,
            was_successful=success,
            error_context=error_context,
            reasoning_steps=reasoning or []
        )
        
        self.context.query_history.append(history_entry)
        if len(self.context.query_history) > self.max_history:
            self.context.query_history.pop(0)
        
        logger.info(f"📝 Added query to history (success: {success})")

    def update_conversation_context(self, key: str, value: Any):
        """Update the conversation context with new information"""
        if not self.context:
            raise ValueError("Context not initialized. Call initialize_context first.")
        self.context.conversation_context[key] = value
        logger.info(f"📝 Updated conversation context: {key}")

    def get_conversation_context(self, key: str) -> Any:
        """Get a value from the conversation context"""
        if not self.context:
            raise ValueError("Context not initialized. Call initialize_context first.")
        return self.context.conversation_context.get(key)
