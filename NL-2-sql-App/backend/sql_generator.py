"""SQL Generator Agent with schema awareness and LLM capabilities"""
import logging
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from .logger_config import log_agent_flow
from .metadata_loader import MetadataLoader
from .llm_provider import get_llm_provider
from .sql_validator import SQLValidator
from .llm_prompt_builder import PromptingAgent

# Configure logging
logger = logging.getLogger(__name__)

def log_llm_interaction(prompt: str, response: Dict[str, str], attempt: int) -> None:
    """Log LLM interaction with JSON input/output"""
    try:
        interaction = {
            "llm_interaction": {
                "attempt": attempt,
                "input": {
                    "prompt": prompt,
                    "temperature": 0.1 + (0.1 * (attempt - 1)),
                    "max_tokens": 512
                },
                "output": response,
                "timestamp": "✅"  # Green tick for successful LLM interaction
            }
        }
        logger.info(f"\n{json.dumps(interaction, indent=2)}")
    except Exception as err:
        logger.error(f"Failed to log LLM interaction: {str(err)}")

class SQLGeneratorAgent:
    def __init__(self, temperature: float = 0.1):
        self.temperature = temperature
        self.schema_tables = None
        self.metadata_loader = MetadataLoader()
        self.llm_provider = get_llm_provider()
        self.validator = SQLValidator(os.getenv("SQLITE_DB_PATH", "banking.db"))
        self.max_llm_attempts = 3
        self.prompting_agent = PromptingAgent()
        logger.info("Initialized SQLGeneratorAgent")

    def _get_foreign_key_info(self) -> Dict[str, List[Dict[str, str]]]:
        """Get foreign key relationships from schema metadata"""
        try:
            # Get schema metadata from the metadata loader
            schema_metadata = self.metadata_loader.get_metadata()
            
            # Define the foreign key relationships based on schema
            foreign_keys = {
                "branches": [
                    {"column": "manager_id", "references": "employees.id"}
                ],
                "customers": [
                    {"column": "branch_id", "references": "branches.id"}
                ],
                "employees": [
                    {"column": "branch_id", "references": "branches.id"}
                ],
                "accounts": [
                    {"column": "customer_id", "references": "customers.id"},
                    {"column": "branch_id", "references": "branches.id"}
                ],
                "transactions": [
                    {"column": "account_id", "references": "accounts.id"},
                    {"column": "employee_id", "references": "employees.id"}
                ]
            }
            
            # Log the foreign key information
            logger.info("Retrieved foreign key relationships from schema")
            logger.debug(f"Foreign keys: {json.dumps(foreign_keys, indent=2)}")
            
            return foreign_keys
            
        except Exception as err:
            logger.error(f"Error getting foreign key info: {str(err)}")
            # Return empty structure to avoid breaking the application
            return {}

    def _validate_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the schema"""
        return table_name in self.schema_tables

    def _validate_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        if not self._validate_table_exists(table_name):
            return False
        return column_name in self.schema_tables[table_name]

    def _validate_column_value(self, table_name: str, column_name: str, value: str) -> bool:
        """Validate a column value against known valid values"""
        return self.metadata_loader.validate_value(table_name, column_name, value)

    def _build_join_condition(self, table1: str, table2: str) -> Optional[str]:
        """Build a JOIN condition between two tables based on foreign keys"""
        fk_info = self._get_foreign_key_info()
        
        # Check direct relationship
        if table1 in fk_info:
            for fk in fk_info[table1]:
                ref_table, ref_col = fk["references"].split(".")
                if ref_table == table2:
                    return f"{table1}.{fk['column']} = {table2}.{ref_col}"
        
        # Check reverse relationship
        if table2 in fk_info:
            for fk in fk_info[table2]:
                ref_table, ref_col = fk["references"].split(".")
                if ref_table == table1:
                    return f"{table2}.{fk['column']} = {table1}.{ref_col}"
        
        return None

    def _parse_llm_response(self, response: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse the LLM response to extract SQL query and suggestion"""
        try:
            # Clean the response to handle markdown-wrapped JSON
            cleaned_response = self._clean_llm_response(response)
            
            # Parse the cleaned response as JSON
            response_json = json.loads(cleaned_response)
            
            # Extract SQL query and suggestion
            sql_query = response_json.get("SQLQuery", "").strip()
            suggestion = response_json.get("Suggestion", "").strip()
            
            # Validate both fields are present
            if not sql_query or not suggestion:
                logger.error("LLM response missing required fields")
                logger.error(f"SQLQuery: '{sql_query}', Suggestion: '{suggestion}'")
                return None, None
            
            logger.info("✅ Successfully parsed LLM response")
            logger.debug(f"Extracted SQL: {sql_query[:100]}...")
            logger.debug(f"Extracted Suggestion: {suggestion[:100]}...")
            
            return sql_query, suggestion
            
        except json.JSONDecodeError as err:
            logger.error(f"Failed to parse LLM response as JSON: {str(err)}")
            logger.error(f"Cleaned response: {cleaned_response[:200]}...")
            return None, None
        except Exception as err:
            logger.error(f"Error parsing LLM response: {str(err)}")
            return None, None

    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response by removing markdown code blocks and extra whitespace"""
        try:
            # Remove leading and trailing whitespace
            cleaned = response.strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith("```json"):
                # Find the end of the code block
                end_marker = cleaned.find("```", 7)  # Start after "```json"
                if end_marker != -1:
                    cleaned = cleaned[7:end_marker].strip()
                else:
                    # No closing marker found, take everything after ```json
                    cleaned = cleaned[7:].strip()
            elif cleaned.startswith("```"):
                # Generic code block
                end_marker = cleaned.find("```", 3)
                if end_marker != -1:
                    cleaned = cleaned[3:end_marker].strip()
                else:
                    cleaned = cleaned[3:].strip()
            
            # Remove any remaining backticks at start/end
            cleaned = cleaned.strip("`")
            
            # Log the cleaning process for debugging
            if cleaned != response.strip():
                logger.debug(f"Cleaned LLM response: removed markdown wrapping")
                logger.debug(f"Original: {response[:100]}...")
                logger.debug(f"Cleaned: {cleaned[:100]}...")
            
            return cleaned
            
        except Exception as err:
            logger.error(f"Error cleaning LLM response: {str(err)}")
            return response.strip()

    def _try_llm_error_correction(self, query: str, original_sql: str, error_msg: str, 
                                 context: Dict[str, Any], attempt: int) -> Tuple[bool, str, Optional[str]]:
        """Try to correct SQL using LLM with full error context"""
        
        # Build comprehensive error correction context
        error_context = {
            "nl_query": query,
            "original_sql": original_sql,
            "error_message": error_msg,
            "attempt_number": attempt,
            "schema_metadata": self.metadata_loader.get_metadata(),
            "retriever_context": context.get("retrieval_context", {}),
            "detected_tables": context.get("detected_tables", []),
            "detected_capabilities": context.get("detected_capabilities", [])
        }
        
        # Build enhanced prompt for error correction
        correction_prompt = self.prompting_agent.build_error_correction_prompt(error_context)
        
        logger.info(f"\n🔄 LLM Error Correction Attempt {attempt}")
        logger.info(f"Error: {error_msg}")
        
        # Get response from LLM
        response = self.llm_provider.generate_text(
            correction_prompt,
            temperature=0.1 + (0.1 * attempt),  # Increase temperature for creativity
            max_tokens=512
        )
        
        if response is None:
            logger.error(f"LLM returned None response on correction attempt {attempt}")
            return False, original_sql, None
        
        # Parse the response
        corrected_sql, suggestion = self._parse_llm_response(response.strip())
        if not corrected_sql:
            logger.warning(f"LLM correction attempt {attempt} failed: Invalid response format")
            return False, original_sql, None
        
        # Log the correction attempt
        log_llm_interaction(correction_prompt, {"SQLQuery": corrected_sql, "Suggestion": suggestion}, attempt)
        
        return True, corrected_sql, suggestion

    def _exclude_problematic_columns(self, sql: str, error_msg: str) -> str:
        """Exclude problematic columns from SQL query"""
        try:
            # Parse error message to identify problematic columns
            problematic_columns = self._extract_problematic_columns(error_msg)
            
            if not problematic_columns:
                return sql
            
            # Create a simplified query without problematic columns
            simplified_sql = self._create_simplified_query(sql, problematic_columns)
            
            logger.info(f"🔧 Excluded problematic columns: {problematic_columns}")
            logger.info(f"Simplified SQL: {simplified_sql}")
            
            return simplified_sql
            
        except Exception as err:
            logger.error(f"Error excluding problematic columns: {str(err)}")
            return sql

    def _extract_problematic_columns(self, error_msg: str) -> List[str]:
        """Extract problematic column names from error message"""
        problematic_columns = []
        
        # Common SQLite error patterns
        error_patterns = [
            r"no such column: (\w+)",
            r"column (\w+) does not exist",
            r"ambiguous column name: (\w+)"
        ]
        
        import re
        for pattern in error_patterns:
            matches = re.findall(pattern, error_msg.lower())
            problematic_columns.extend(matches)
        
        return list(set(problematic_columns))  # Remove duplicates

    def _create_simplified_query(self, original_sql: str, excluded_columns: List[str]) -> str:
        """Create a simplified query excluding problematic columns"""
        try:
            # Simple approach: remove problematic columns from SELECT clause
            sql_lower = original_sql.lower()
            
            # Find SELECT clause
            select_start = sql_lower.find("select")
            if select_start == -1:
                return original_sql
            
            # Find FROM clause
            from_start = sql_lower.find("from", select_start)
            if from_start == -1:
                return original_sql
            
            # Extract SELECT clause
            select_clause = original_sql[select_start:from_start]
            
            # Remove problematic columns
            import re
            for col in excluded_columns:
                # Remove the column from SELECT clause
                select_clause = re.sub(rf'\b{col}\b', '', select_clause, flags=re.IGNORECASE)
                select_clause = re.sub(r',\s*,', ',', select_clause)  # Clean up double commas
                select_clause = re.sub(r'^\s*,\s*', '', select_clause)  # Remove leading comma
                select_clause = re.sub(r',\s*$', '', select_clause)  # Remove trailing comma
            
            # Reconstruct SQL
            simplified_sql = select_clause + original_sql[from_start:]
            
            return simplified_sql
            
        except Exception as err:
            logger.error(f"Error creating simplified query: {str(err)}")
            return original_sql

    def _test_sql_execution(self, sql: str) -> Dict[str, Any]:
        """Test SQL execution against the database"""
        try:
            # Use the executor to test the SQL
            from .executor import ExecutorAgent
            executor = ExecutorAgent()
            exec_result = executor.run_query(sql, limit=1)
            return exec_result
        except Exception as err:
            return {"success": False, "error": str(err)}

    def _try_llm_generation(self, query: str, context: Dict[str, Any], attempts_left: int = 3) -> Tuple[bool, str, Optional[str]]:
        """Try generating SQL using LLM with enhanced error correction"""
        error_context = None
        attempt_number = 1
        current_sql = None
        
        while attempts_left > 0:
            try:
                # Generate prompt using the prompting agent
                if attempt_number == 1:
                    # First attempt: normal generation
                    prompt = self.prompting_agent.build_prompt(
                        query=query,
                        detected_tables=context.get("detected_tables", []),
                        capabilities=context.get("detected_capabilities", []),
                        error_context=error_context
                    )
                else:
                    # Subsequent attempts: error correction
                    if current_sql:
                        success, corrected_sql, suggestion = self._try_llm_error_correction(
                            query, current_sql, error_context, context, attempt_number
                        )
                        if success:
                            current_sql = corrected_sql
                            # Test the corrected SQL
                            is_valid, error_msg = self.validator.validate_sql(corrected_sql)
                            if is_valid:
                                return True, corrected_sql, suggestion
                            else:
                                error_context = error_msg
                                attempts_left -= 1
                                attempt_number += 1
                                continue
                
                # Log the attempt
                logger.info(f"\n🔄 LLM Generation Attempt {attempt_number}")
                logger.info(f"Temperature: {self.temperature + (0.1 * (3 - attempts_left))}")
                
                # Get response from LLM
                response = self.llm_provider.generate_text(
                prompt,
                    temperature=self.temperature + (0.1 * (3 - attempts_left)),
                    max_tokens=512
                )
                
                # Check if response is None (LLM error)
                if response is None:
                    logger.error(f"LLM returned None response on attempt {attempt_number}")
                    attempts_left -= 1
                    attempt_number += 1
                    continue
                
                # Log raw response for debugging
                logger.debug(f"Raw LLM Response:\n{response}")
                
                # Parse the response
                sql, suggestion = self._parse_llm_response(response.strip())
                if not sql or not suggestion:
                    logger.warning(f"LLM attempt {attempt_number} failed: Invalid response format")
                    logger.debug("Expected JSON with SQLQuery and Suggestion fields")
                    attempts_left -= 1
                    attempt_number += 1
                    continue
                
                current_sql = sql
                
                # Log the successful parsing
                log_llm_interaction(prompt, {"SQLQuery": sql, "Suggestion": suggestion}, attempt_number)
                
                # Test the SQL against database
                is_valid, error_msg = self.validator.validate_sql(sql)
                if is_valid:
                    # Test execution
                    exec_result = self._test_sql_execution(sql)
                    if exec_result.get("success"):
                        return True, sql, suggestion
                    else:
                        error_context = exec_result.get("error", "Execution failed")
                else:
                    error_context = error_msg
                
                logger.warning(f"LLM attempt {attempt_number} failed: {error_context}")
                attempts_left -= 1
                attempt_number += 1
                
            except json.JSONDecodeError as err:
                logger.error(f"JSON parsing error on attempt {attempt_number}: {str(err)}")
                attempts_left -= 1
                attempt_number += 1
            except Exception as err:
                logger.error(f"LLM generation error on attempt {attempt_number}: {str(err)}")
                attempts_left -= 1
                attempt_number += 1
        
        # If all attempts failed, try column exclusion
        if current_sql and error_context:
            simplified_sql = self._exclude_problematic_columns(current_sql, error_context)
            if simplified_sql != current_sql:
                logger.info("🔧 Trying simplified query with problematic columns excluded")
                is_valid, _ = self.validator.validate_sql(simplified_sql)
                if is_valid:
                    return True, simplified_sql, "Simplified query with problematic columns excluded"
        
        logger.error("❌ All LLM generation attempts failed")
        return False, "ERROR: Failed to generate valid SQL after multiple attempts", None

    def _try_pattern_matching(self, query: str) -> Tuple[str, str]:
        """Try to match query against known patterns"""
        query_lower = query.lower()
        
        # Branch and manager query pattern
        if "branch" in query_lower and "manager" in query_lower:
            if not all(self._validate_table_exists(t) for t in ["branches", "employees"]):
                return "ERROR: Required tables not found in schema", None
            
            sql = """
                SELECT 
                    b.name AS branch_name,
                    e.name AS manager_name
                FROM branches b
                LEFT JOIN employees e 
                    ON b.manager_id = e.id 
                    AND e.position = 'Branch Manager'
                ORDER BY b.name;
            """
            
            suggestion = """
                This query lists all bank branches along with their manager names.
                It uses a LEFT JOIN to include branches without managers, and
                filters for employees with the 'Branch Manager' position.
                Results are ordered by branch name.
            """.strip()
            
            # Validate the pattern-matched SQL
            is_valid, error_msg = self.validator.validate_sql(sql)
            if is_valid:
                return sql, suggestion
            return f"ERROR: Pattern matching failed validation: {error_msg}", None
        
        # Multiple account types query
        elif ("both" in query_lower or "multiple" in query_lower) and "account" in query_lower:
            if not self._validate_table_exists("accounts"):
                return "ERROR: Accounts table not found in schema", None
            
            account_types = []
            for acc_type in self.metadata_loader.get_column_values("accounts", "type"):
                if acc_type in query_lower:
                    account_types.append(acc_type)
            
            if len(account_types) >= 2:
                type_conditions = []
                joins = []
                for i, acc_type in enumerate(account_types, 1):
                    alias = f"a{i}"
                    type_conditions.append(f"{alias}.type = '{acc_type}'")
                    joins.append(f"""
                        JOIN accounts {alias} 
                            ON c.id = {alias}.customer_id 
                            AND {alias}.status = 'active'
                    """.strip())
                
                sql = f"""
                    SELECT DISTINCT
                        c.first_name || ' ' || c.last_name AS customer_name
                    FROM 
                        customers c
                        {' '.join(joins)}
                    WHERE 
                        {' AND '.join(type_conditions)}
                    ORDER BY 
                        customer_name;
                """
                
                suggestion = f"""
                    This query finds customers who have all of the following account types:
                    {', '.join(account_types)}. It only considers active accounts and
                    returns distinct customer names in alphabetical order.
                """.strip()
                
                # Validate the pattern-matched SQL
                is_valid, error_msg = self.validator.validate_sql(sql)
                if is_valid:
                    return sql, suggestion
                return f"ERROR: Pattern matching failed validation: {error_msg}", None
        
        # No pattern matched
        return "SELECT 1;", "Default fallback query"

    @log_agent_flow("SQLGeneratorAgent")
    def generate(self, query: str, retrieval_context: Dict[str, Any], gen_ctx: Dict[str, Any], schema_tables: Dict[str, List[str]]) -> str:
        """Generate SQL from natural language query"""
        self.schema_tables = schema_tables
        
        # Initialize prompting agent if not already done
        if not self.prompting_agent.context:
            self.prompting_agent.initialize_context(
                schema_metadata=self.metadata_loader.get_metadata(),
                foreign_keys=self._get_foreign_key_info()
            )
        
        # Update conversation context
        self.prompting_agent.update_conversation_context("current_query", query)
        self.prompting_agent.update_conversation_context("retrieval_context", retrieval_context)
        
        # Log input context
        logger.info("\n🔍 SQLGeneratorAgent Input Context:")
        logger.info(json.dumps({
            "query": query,
            "detected_capabilities": gen_ctx.get("detected_capabilities", []),
            "detected_tables": gen_ctx.get("detected_tables", []),
            "has_clarifications": bool(gen_ctx.get("clarified_values")),
            "has_metadata": bool(gen_ctx.get("metadata_context"))
        }, indent=2))
        
        # First try LLM generation with multiple attempts
        success, sql, suggestion = self._try_llm_generation(query, gen_ctx, self.max_llm_attempts)
        if success:
            logger.info("✅ Successfully generated SQL using LLM")
            logger.info(f"📝 Suggestion: {suggestion}")
            return sql
        
        # If LLM fails, fall back to pattern matching
        logger.info("LLM generation failed, trying pattern matching")
        sql, suggestion = self._try_pattern_matching(query)
        if sql != "SELECT 1;":
            # Add pattern-matched query to history
            self.prompting_agent.add_query_to_history(
                nl_query=query,
                sql=sql,
                suggestion=suggestion,
                success=True,
                reasoning=["Used pattern matching due to LLM failure"]
            )
            logger.info("✅ Successfully generated SQL using pattern matching")
            logger.info(f"📝 Suggestion: {suggestion}")
            return sql
        
        return "ERROR: Failed to generate valid SQL query"

    def repair_sql(self, query: str, gen_ctx: Dict[str, Any], hint: str = None) -> str:
        """Repair invalid SQL based on error hint"""
        try:
            # Get error context
            error_context = self.validator.get_error_context(hint)
            
            # Try LLM repair with error context
            success, sql, suggestion = self._try_llm_generation(
                query,
                gen_ctx,  # Use the full context for repair
                attempts_left=2,  # Fewer attempts for repair
            )
            
            if success:
                logger.info(f"✅ Successfully repaired SQL")
                logger.info(f"📝 Repair suggestion: {suggestion}")
                return sql
                
        except Exception as err:
            logger.error(f"SQL repair failed: {str(err)}")
                
        return "SELECT 1;"  # Default fallback