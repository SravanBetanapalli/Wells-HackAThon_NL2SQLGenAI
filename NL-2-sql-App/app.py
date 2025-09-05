"""Main Streamlit Application"""
import os
import streamlit as st
from dotenv import load_dotenv
from backend.pipeline import NL2SQLPipeline, PipelineConfig
from backend.planner import PlannerAgent
from backend.retriever import RetrieverAgent
from backend.sql_generator import SQLGeneratorAgent
from backend.validator import ValidatorAgent
from backend.executor import ExecutorAgent
from backend.summarizer import SummarizerAgent
from backend.logger_config import log_agent_flow, get_agent_flow_data
from frontend.agent_tabs_ui import render_agent_tabs
from db.init_db import init_db
from backend.schema_processor import initialize_schema

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = os.getenv("SQLITE_DB_PATH", "banking.db")
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# Schema definition
# Schema definition
schema_tables = {
    "accounts": ["id", "customer_id", "account_number", "type", "balance", "opened_at", "interest_rate", "status", "branch_id", "created_at", "updated_at"],
    "branches": ["id", "name", "address", "city", "state", "zip_code", "manager_id", "created_at", "updated_at"],
    "customers": ["id", "email", "phone", "address", "first_name", "last_name", "date_of_birth", "gender", "national_id", "created_at", "updated_at", "branch_id"],
    "employees": ["id", "branch_id", "name", "email", "phone", "position", "hire_date", "salary", "created_at", "updated_at"],
    "transactions": ["id", "account_id", "transaction_date", "amount", "type", "description", "status", "created_at", "updated_at", "employee_id"]
}
def show_system_status():
    """Display system initialization status"""
    st.sidebar.markdown("### 🔧 System Status")
    
    # Database Status
    if os.path.exists(DB_PATH):
        st.sidebar.success("✅ Database: Connected")
        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            table_count = cursor.fetchone()[0]
            st.sidebar.markdown(f"📊 Tables: {table_count}")
            
            # Show table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                count = cursor.fetchone()[0]
                st.sidebar.markdown(f"• {table[0]}: {count:,} rows")
            conn.close()
        except Exception as e:
            st.sidebar.error(f"❌ Database Error: {str(e)}")
    else:
        st.sidebar.error("❌ Database: Not Found")
    
    # ChromaDB Status
    if os.path.exists(CHROMA_PATH):
        st.sidebar.success("✅ ChromaDB: Connected")
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            collection = client.get_collection("database_schema")
            st.sidebar.markdown(f"📚 Schema Embeddings: {collection.count()} chunks")
        except Exception as e:
            st.sidebar.error(f"❌ ChromaDB Error: {str(e)}")
    else:
        st.sidebar.error("❌ ChromaDB: Not Found")

    # Reinitialize Button
    if st.sidebar.button("🔄 Reinitialize System"):
        st.session_state.system_initialized = False
        st.rerun()

# Initialize system
def initialize_system():
    """Initialize database and schema embeddings"""
    status = {"success": True, "messages": []}
    
    try:
        # Initialize SQLite database
        with st.spinner("🔄 Initializing database..."):
            try:
                init_db()
                status["messages"].append("✅ Database initialized successfully!")
            except Exception as e:
                status["success"] = False
                status["messages"].append(f"❌ Database initialization failed: {str(e)}")
        
        # Initialize schema embeddings
        with st.spinner("🔄 Initializing schema embeddings..."):
            try:
                initialize_schema()
                status["messages"].append("✅ Schema embeddings initialized successfully!")
            except Exception as e:
                status["success"] = False
                status["messages"].append(f"❌ Schema initialization failed: {str(e)}")
        
        # Display initialization messages
        for msg in status["messages"]:
            if "❌" in msg:
                st.error(msg)
            else:
                st.success(msg)
        
        return status["success"]
            
    except Exception as e:
        st.error(f"❌ System initialization failed: {str(e)}")
        return False

# Initialize agents
@log_agent_flow("initialize_pipeline")
def initialize_pipeline():
    """Initialize the NL2SQL pipeline with all agents"""
    generator = SQLGeneratorAgent(temperature=0.1)
    generator.schema_tables = schema_tables

    return NL2SQLPipeline(
        planner=PlannerAgent(schema_tables),
        retriever=RetrieverAgent(db_path=CHROMA_PATH),
        generator=generator,
        validator=ValidatorAgent(schema_tables),
        executor=ExecutorAgent(DB_PATH),
        summarizer=SummarizerAgent(),
        schema_tables=schema_tables,
        config=PipelineConfig()
    )

# Streamlit UI
st.set_page_config(layout="wide")
st.title("🤖 NL→SQL Assistant")

# Show system status in sidebar
show_system_status()

# Initialize system if not done
if "system_initialized" not in st.session_state or not st.session_state.system_initialized:
    st.session_state.system_initialized = initialize_system()

if not st.session_state.system_initialized:
    st.error("❌ System initialization failed. Please check the logs and try again.")
    if st.button("🔄 Retry Initialization"):
        st.session_state.system_initialized = False
        st.rerun()
    st.stop()

# Create tabs for different views
main_tab, agents_tab = st.tabs(["🔍 Main", "🤖 Agents"])

with main_tab:
    # Initialize session state
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = initialize_pipeline()
        
        # Query input
    query = st.chat_input("Ask about the database...")

    # Handle re-run queries from history
    if "rerun_query" in st.session_state:
        query = st.session_state.rerun_query
        del st.session_state.rerun_query

    # Display conversation history
    if st.session_state.conversation_history:
        # Create collapsible conversation history section
        with st.expander("📝 **Conversation History**", expanded=True):
            for i, (user_query, response) in enumerate(st.session_state.conversation_history):
                with st.expander(f"💬 Q{i+1}: {user_query[:50]}{'...' if len(user_query) > 50 else ''}", expanded=False):
                    # Re-run button
                    if st.button(f"🔄 Re-run: {user_query[:30]}{'...' if len(user_query) > 30 else ''}", key=f"rerun_{i}"):
                        st.session_state.rerun_query = user_query
                    
                    st.markdown(f"**Your Question:** {user_query}")
                    st.divider()
                    
                    if response.get("summary"):
                        st.markdown(response.get("summary"))
                    
                    if response.get("sql"):
                        with st.expander("🔧 SQL Query", expanded=False):
                            st.code(response["sql"], language="sql")
                    
                    if response.get("table"):
                        st.subheader("📋 Results")
                        import pandas as pd
                        
                        # Display execution message if available
                        if response.get("execution_message"):
                            st.info(f"💡 {response['execution_message']}")
                        
                        # Display results count
                        results_count = len(response["table"])
                        st.markdown(f"**Found {results_count} record{'s' if results_count != 1 else ''}**")
                        
                        # Create DataFrame and display
                        df = pd.DataFrame(response["table"])
                        if not df.empty:
                            st.dataframe(df, width='stretch')
                            
                            # Add download button for results
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results as CSV",
                                data=csv,
                                file_name=f"query_results_{i+1}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("No data found for this query.")
                    elif response.get("success") and not response.get("table"):
                        st.info("✅ Query executed successfully but returned no results.")
        
        st.divider()

    # Process new query
    if query:
        st.markdown("---")
        st.markdown(f"### 💬 **Your Question:**")
        st.info(f"**{query}**")
        st.markdown("---")
        
        with st.spinner("🔄 Processing your query..."):
            try:
                resp = st.session_state.pipeline.run(query)
                st.session_state.conversation_history.append((query, resp))
                
                # Show summary
                if resp.get("summary"): 
                    st.markdown("### 📊 **Data Insights:**")
                    st.markdown(resp.get("summary"))
                    st.divider()
                
                # Show SQL
                if resp.get("sql"): 
                    with st.expander("🔧 Generated SQL Query", expanded=False):
                        st.code(resp["sql"], language="sql")
                
                # Show results
                if resp.get("table"):
                    st.subheader("📋 Results")
                    import pandas as pd
                    
                    # Display execution message if available
                    if resp.get("execution_message"):
                        st.info(f"💡 {resp['execution_message']}")
                    
                    # Display results count
                    results_count = len(resp["table"])
                    st.markdown(f"**Found {results_count} record{'s' if results_count != 1 else ''}**")
                    
                    # Create DataFrame and display
                    df = pd.DataFrame(resp["table"])
                    if not df.empty:
                        st.dataframe(df, width='stretch'
                        )
                        
                        # Add download button for results
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv,
                            file_name=f"query_results_{len(st.session_state.conversation_history)}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("No data found for this query.")
                elif resp.get("success") and not resp.get("table"):
                    st.info("✅ Query executed successfully but returned no results.")
                
                # Show suggestions
                if resp.get("suggestions"):
                    st.divider()
                    st.subheader("💡 Suggested Follow-up Questions")
                    
                    # Create columns for suggestions
                    cols = st.columns(2)
                    for i, suggestion in enumerate(resp["suggestions"]):
                        col = cols[i % 2]
                        if col.button(suggestion, key=f"suggestion_{i}"):
                            st.info(f"💡 You can copy and paste this question: **{suggestion}**")
                    
                    st.markdown("**Or copy these questions:**")
                    for suggestion in resp["suggestions"]:
                        st.markdown(f"• `{suggestion}`")
            
            except Exception as e:
                st.error(f"❌ Error processing query: {str(e)}")
        
        # Clear history button
        if st.button("🗑️ Clear Conversation History"):
            st.session_state.conversation_history = []


with agents_tab:
    # Display detailed agent information
    agent_data = get_agent_flow_data()
    render_agent_tabs(agent_data)