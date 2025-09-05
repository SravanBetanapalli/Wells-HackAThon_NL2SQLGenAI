"""Integration tests for SQL generation pipeline"""
import os
import json
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from backend.sql_generator import SQLGeneratorAgent
from backend.llm_prompt_builder import PromptingAgent, QueryHistory
from backend.llm_provider import OpenAIProvider
from backend.metadata_loader import MetadataLoader

# Test data
SAMPLE_SCHEMA_METADATA = {
    "tables": {
        "customers": {
            "description": "Stores customer information",
            "columns": {
                "id": {
                    "type": "TEXT",
                    "primary_key": True,
                    "pattern": "CUST[A-Z0-9]{10}"
                },
                "first_name": {
                    "type": "TEXT",
                    "required": True
                },
                "last_name": {
                    "type": "TEXT",
                    "required": True
                },
                "email": {
                    "type": "TEXT",
                    "required": True,
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            }
        },
        "accounts": {
            "description": "Bank account information",
            "columns": {
                "id": {
                    "type": "TEXT",
                    "primary_key": True
                },
                "customer_id": {
                    "type": "TEXT",
                    "required": True
                },
                "type": {
                    "type": "TEXT",
                    "required": True,
                    "distinct_values": ["checking", "savings", "credit", "loan"]
                },
                "status": {
                    "type": "TEXT",
                    "default": "active",
                    "distinct_values": ["active", "inactive", "suspended", "closed"]
                },
                "balance": {
                    "type": "REAL",
                    "required": True,
                    "default": "0.00"
                }
            }
        },
        "transactions": {
            "description": "Account transaction records",
            "columns": {
                "id": {
                    "type": "TEXT",
                    "primary_key": True
                },
                "account_id": {
                    "type": "TEXT",
                    "required": True
                },
                "type": {
                    "type": "TEXT",
                    "required": True,
                    "distinct_values": ["deposit", "withdrawal", "transfer", "payment"]
                },
                "amount": {
                    "type": "REAL",
                    "required": True
                },
                "transaction_date": {
                    "type": "TIMESTAMP",
                    "required": True,
                    "default": "CURRENT_TIMESTAMP"
                }
            }
        }
    }
}

SAMPLE_FOREIGN_KEYS = {
    "accounts": [
        {"column": "customer_id", "references": "customers.id"}
    ],
    "transactions": [
        {"column": "account_id", "references": "accounts.id"}
    ]
}

SAMPLE_SCHEMA_TABLES = {
    "customers": ["id", "first_name", "last_name", "email"],
    "accounts": ["id", "customer_id", "type", "status", "balance"],
    "transactions": ["id", "account_id", "type", "amount", "transaction_date"]
}

@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider that returns predefined responses"""
    provider = Mock(spec=OpenAIProvider)
    
    def generate_text(prompt: str, **kwargs) -> str:
        # Parse the prompt to determine appropriate response
        prompt_data = json.loads(prompt)
        query = prompt_data["task"]["input_query"].lower()
        detected_tables = prompt_data["reasoning"]["required_tables"]
        capabilities = prompt_data["reasoning"]["detected_capabilities"]
        
        # Predefined responses for different query types
        if "high" in query and "value" in query and "transaction" in query:
            return json.dumps({
                "SQLQuery": """
                    SELECT 
                        c.first_name || ' ' || c.last_name AS customer_name,
                        COUNT(t.id) as transaction_count,
                        SUM(t.amount) as total_value
                    FROM customers c
                    JOIN accounts a ON c.id = a.customer_id
                    JOIN transactions t ON a.id = t.account_id
                    WHERE t.transaction_date >= date('now', '-1 month')
                    AND t.amount > 5000
                    GROUP BY c.id
                    HAVING total_value > 5000
                    ORDER BY total_value DESC;
                """,
                "Suggestion": "This query identifies high-value customers by analyzing their large transactions (>$5000) in the past month."
            })
        elif "customer" in query and "account" in query:
            if "count" in query or "aggregate" in capabilities:
                return json.dumps({
                    "SQLQuery": """
                        SELECT 
                            c.first_name || ' ' || c.last_name AS customer_name,
                            COUNT(a.id) as account_count,
                            SUM(a.balance) as total_balance
                        FROM customers c
                        LEFT JOIN accounts a ON c.id = a.customer_id
                        WHERE a.status = 'active'
                        GROUP BY c.id
                        ORDER BY total_balance DESC;
                    """,
                    "Suggestion": "This query shows customer account statistics including count and total balance."
                })
            else:
                return json.dumps({
                    "SQLQuery": """
                        SELECT DISTINCT
                            c.first_name || ' ' || c.last_name AS customer_name,
                            a.type AS account_type,
                            a.status,
                            a.balance
                        FROM customers c
                        JOIN accounts a ON c.id = a.customer_id
                        WHERE a.status = 'active'
                        ORDER BY customer_name, account_type;
                    """,
                    "Suggestion": "This query shows all customers with their active account details."
                })
        elif "transaction" in query and "date" in capabilities:
            return json.dumps({
                "SQLQuery": """
                    SELECT 
                        t.transaction_date,
                        t.type,
                        t.amount,
                        a.type as account_type,
                        c.first_name || ' ' || c.last_name AS customer_name
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.id
                    JOIN customers c ON a.customer_id = c.id
                    WHERE t.transaction_date >= date('now', '-7 days')
                    ORDER BY t.transaction_date DESC;
                """,
                "Suggestion": "This query shows recent transactions with customer and account details."
            })
        elif "customer" in detected_tables and "accounts" in detected_tables:
            return json.dumps({
                "SQLQuery": """
                    SELECT 
                        c.first_name || ' ' || c.last_name AS customer_name,
                        COUNT(a.id) as account_count
                    FROM customers c
                    LEFT JOIN accounts a ON c.id = a.customer_id
                    WHERE a.status = 'active'
                    GROUP BY c.id
                    ORDER BY account_count DESC;
                """,
                "Suggestion": "This query shows customers and their account counts."
            })
        else:
            return json.dumps({
                "SQLQuery": "SELECT * FROM customers;",
                "Suggestion": "Default query to list all customers."
            })
    
    provider.generate_text.side_effect = generate_text
    return provider

@pytest.fixture
def metadata_loader():
    """Mock metadata loader that returns sample data"""
    loader = Mock(spec=MetadataLoader)
    loader.get_metadata.return_value = SAMPLE_SCHEMA_METADATA
    return loader

@pytest.fixture
def mock_validator():
    """Mock SQL validator that always returns success"""
    validator = Mock()
    validator.validate_sql.return_value = (True, None)
    return validator

@pytest.fixture
def test_prompting_agent():
    """Create a test version of PromptingAgent with mock chain-of-thought steps"""
    class TestAgent(PromptingAgent):
        def _build_chain_of_thought_steps(self, query: str, detected_tables: List[str], 
                                        capabilities: List[str]) -> List[str]:
            """Mock implementation for testing"""
            steps = [
                f"1. Identified tables: {', '.join(detected_tables)}",
                f"2. Required capabilities: {', '.join(capabilities)}",
                "3. Planning query structure",
                "4. Determining output format"
            ]
            return steps
    
    agent = TestAgent()
    agent.initialize_context(SAMPLE_SCHEMA_METADATA, SAMPLE_FOREIGN_KEYS)
    return agent

@pytest.fixture
def sql_generator(mock_llm_provider, metadata_loader, mock_validator, test_prompting_agent):
    """Initialize SQLGeneratorAgent with mocked dependencies"""
    generator = SQLGeneratorAgent()
    generator.llm_provider = mock_llm_provider
    generator.metadata_loader = metadata_loader
    generator.validator = mock_validator
    generator.schema_tables = SAMPLE_SCHEMA_TABLES
    generator.prompting_agent = test_prompting_agent
    return generator

def test_prompt_builder_initialization(test_prompting_agent):
    """Test PromptingAgent initialization and context setup"""
    # Verify example queries are loaded
    assert len(test_prompting_agent.example_queries) > 0
    assert all(hasattr(ex, 'nl_query') for ex in test_prompting_agent.example_queries)
    assert all(hasattr(ex, 'sql_query') for ex in test_prompting_agent.example_queries)
    
    # Verify context initialization
    assert test_prompting_agent.context is not None
    assert test_prompting_agent.context.schema_metadata == SAMPLE_SCHEMA_METADATA
    assert test_prompting_agent.context.foreign_keys == SAMPLE_FOREIGN_KEYS

def test_schema_infused_context_building(test_prompting_agent):
    """Test building schema-infused context"""
    context = test_prompting_agent._build_schema_infused_context()
    
    # Verify schema structure
    assert "tables" in context
    assert "relationships" in context
    assert "value_domains" in context
    
    # Check table details
    assert "customers" in context["tables"]
    assert "accounts" in context["tables"]
    
    # Verify foreign key relationships
    relationships = context["relationships"]
    assert any(r["from"] == "accounts.customer_id" and r["to"] == "customers.id" 
              for r in relationships)
    
    # Check value domains
    assert "accounts.type" in context["value_domains"]
    assert "checking" in context["value_domains"]["accounts.type"]

def test_prompt_generation(test_prompting_agent):
    """Test complete prompt generation process"""
    query = "Show me all customers with their account counts"
    detected_tables = ["customers", "accounts"]
    capabilities = ["aggregate", "join"]
    
    prompt = test_prompting_agent.build_prompt(query, detected_tables, capabilities)
    prompt_data = json.loads(prompt)
    
    # Verify prompt structure
    assert "task" in prompt_data
    assert "schema_context" in prompt_data
    assert "reasoning" in prompt_data
    assert "examples" in prompt_data
    assert "requirements" in prompt_data
    
    # Check task details
    assert prompt_data["task"]["input_query"] == query
    assert "output_format" in prompt_data["task"]
    
    # Verify reasoning
    assert "chain_of_thought" in prompt_data["reasoning"]
    assert prompt_data["reasoning"]["detected_capabilities"] == capabilities
    assert prompt_data["reasoning"]["required_tables"] == detected_tables

def test_sql_generation_integration(sql_generator):
    """Test complete SQL generation flow with mocked LLM"""
    query = "Show me customers and their account counts"
    retrieval_context = {"relevant_schema": SAMPLE_SCHEMA_METADATA}
    gen_ctx = {
        "detected_tables": ["customers", "accounts"],
        "detected_capabilities": ["aggregate", "join"],
        "metadata_context": SAMPLE_SCHEMA_METADATA
    }
    
    sql = sql_generator.generate(query, retrieval_context, gen_ctx, SAMPLE_SCHEMA_TABLES)
    
    # Verify SQL was generated
    assert sql is not None
    assert "SELECT" in sql
    assert "customers" in sql.lower()
    assert "accounts" in sql.lower()
    assert "count" in sql.lower()
    
    # Verify LLM was called with correct prompt
    prompt_call = sql_generator.llm_provider.generate_text.call_args[0][0]
    prompt_data = json.loads(prompt_call)
    
    assert prompt_data["task"]["input_query"] == query
    assert "customers" in prompt_data["reasoning"]["required_tables"]
    assert "aggregate" in prompt_data["reasoning"]["detected_capabilities"]

def test_complex_query_generation(sql_generator):
    """Test generation of complex queries with multiple conditions"""
    query = "Find high-value customers with transactions over $5000 in the last month"
    retrieval_context = {"relevant_schema": SAMPLE_SCHEMA_METADATA}
    gen_ctx = {
        "detected_tables": ["customers", "accounts", "transactions"],
        "detected_capabilities": ["aggregate", "join", "date_filter"],
        "metadata_context": SAMPLE_SCHEMA_METADATA
    }
    
    sql = sql_generator.generate(query, retrieval_context, gen_ctx, SAMPLE_SCHEMA_TABLES)
    
    # Verify complex SQL generation
    assert sql is not None
    assert "SELECT" in sql
    assert "JOIN" in sql
    assert "WHERE" in sql
    assert "GROUP BY" in sql
    assert "HAVING" in sql
    assert "ORDER BY" in sql
    assert "5000" in sql
    assert "date" in sql.lower()
    assert "month" in sql.lower()

def test_error_handling_integration(sql_generator):
    """Test error handling in the integration flow"""
    # Test with invalid tables
    query = "Show me invalid_table data"
    retrieval_context = {}
    gen_ctx = {
        "detected_tables": ["invalid_table"],
        "detected_capabilities": [],
        "metadata_context": {}
    }
    
    # Should fall back to pattern matching
    sql = sql_generator.generate(query, retrieval_context, gen_ctx, SAMPLE_SCHEMA_TABLES)
    assert sql == "SELECT * FROM customers;" or "ERROR" in sql

def test_llm_retry_mechanism(sql_generator):
    """Test LLM retry mechanism with invalid responses"""
    # Make LLM fail first attempt
    def generate_text_with_retry(prompt: str, **kwargs) -> str:
        if generate_text_with_retry.attempts == 0:
            generate_text_with_retry.attempts += 1
            return "invalid json"
        return json.dumps({
            "SQLQuery": "SELECT * FROM customers;",
            "Suggestion": "Retry successful"
        })
    
    generate_text_with_retry.attempts = 0
    sql_generator.llm_provider.generate_text.side_effect = generate_text_with_retry
    
    query = "List all customers"
    retrieval_context = {}
    gen_ctx = {
        "detected_tables": ["customers"],
        "detected_capabilities": [],
        "metadata_context": SAMPLE_SCHEMA_METADATA
    }
    
    sql = sql_generator.generate(query, retrieval_context, gen_ctx, SAMPLE_SCHEMA_TABLES)
    
    # Verify retry was successful
    assert sql == "SELECT * FROM customers;"
    assert sql_generator.llm_provider.generate_text.call_count > 1

def test_prompt_history_management(test_prompting_agent):
    """Test query history management in PromptingAgent"""
    # Add multiple queries
    for i in range(5):
        test_prompting_agent.add_query_to_history(
            nl_query=f"Query {i}",
            sql=f"SELECT {i}",
            suggestion=f"Suggestion {i}",
            success=True
        )
    
    # Verify history limit
    assert len(test_prompting_agent.context.query_history) == test_prompting_agent.max_history
    
    # Verify order (most recent first)
    latest = test_prompting_agent.context.query_history[-1]
    assert latest.generated_sql == "SELECT 4"

if __name__ == "__main__":
    pytest.main([__file__])