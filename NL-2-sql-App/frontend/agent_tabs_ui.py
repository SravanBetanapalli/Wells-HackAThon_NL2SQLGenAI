"""Agent-specific tab interface components"""
import streamlit as st
import json
from typing import Dict, Any, List
import pandas as pd

def format_json(data: Any) -> str:
    """Format JSON data for display"""
    if isinstance(data, str):
        try:
            return json.dumps(json.loads(data), indent=2)
        except:
            return data
    return json.dumps(data, indent=2)

def render_agent_io(input_data: Any, output_data: Any, agent_name: str):
    """Render agent input/output in columns"""
    # Create two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Input")
        st.code(format_json(input_data), language="json")
        
    with col2:
        st.markdown("### 📤 Output")
        st.code(format_json(output_data), language="json")

def render_agent_status(status: str):
    """Render agent status with appropriate icon"""
    status_icons = {
        'started': '🟡',
        'completed': '🟢',
        'failed': '🔴',
        'pending': '⚪'
    }
    icon = status_icons.get(status.lower(), '⚪')
    st.markdown(f"### Status: {icon} {status}")

def extract_agent_io(state: Dict[str, Any], agent_name: str) -> tuple:
    """Extract and format input/output data from agent state"""
    try:
        # Get input data
        input_args = state.get('input_args', ())
        input_kwargs = state.get('input_kwargs', {})
        
        # Format input based on agent type
        if agent_name == "PlannerAgent":
            input_data = {
                'query': input_args[0] if input_args else None,
                'schema_tables': list(input_kwargs.get('schema_map', {}).keys()) if input_kwargs else [],
                'conversation_state': input_kwargs.get('conversation_state', {}) if input_kwargs else {}
            }
        elif agent_name == "RetrieverAgent":
            input_data = {
                'tables': input_args[0] if input_args else [],
                'context_type': input_kwargs.get('context_type', 'unknown')
            }
        elif agent_name == "SQLGeneratorAgent":
            input_data = {
                'query': input_args[0] if input_args else None,
                'retrieval_context': input_kwargs.get('retrieval_context', {}),
                'generation_context': input_kwargs.get('gen_ctx', {})
            }
        else:
            input_data = {
                'args': input_args,
                'kwargs': input_kwargs
            }
        
        # Get output data
        output = state.get('output', None)
        if isinstance(output, str):
            try:
                output_data = json.loads(output)
            except:
                output_data = output
        else:
            output_data = output
            
        # Add agent-specific output formatting
        if agent_name == "PlannerAgent" and isinstance(output_data, dict):
            output_data = {
                'plan': output_data,
                'analysis': {
                    'detected_tables': output_data.get('tables', []),
                    'detected_capabilities': output_data.get('capabilities', []),
                    'needs_clarification': bool(output_data.get('clarifications', [])),
                    'steps': output_data.get('steps', [])
                }
            }
        
        return input_data, output_data
        
    except Exception as e:
        st.error(f"Error parsing {agent_name} data: {str(e)}")
        return (
            {'error': f'Failed to parse input: {str(e)}'},
            {'error': f'Failed to parse output: {str(e)}'}
        )

def render_planner_tab(agent_data: Dict[str, Any]):
    """Render Planner Agent tab"""
    st.markdown("## 🎯 Planner Agent")
    
    if 'PlannerAgent' in agent_data['agent_states']:
        state = agent_data['agent_states']['PlannerAgent']
        render_agent_status(state.get('status', 'unknown'))
        input_data, output_data = extract_agent_io(state, "PlannerAgent")
        render_agent_io(input_data, output_data, "PlannerAgent")
    else:
        st.info("No planner data available yet. Run a query to see the planner in action.")

def render_retriever_tab(agent_data: Dict[str, Any]):
    """Render Retriever Agent tab"""
    st.markdown("## 🔍 Retriever Agent")
    
    if 'RetrieverAgent' in agent_data['agent_states']:
        state = agent_data['agent_states']['RetrieverAgent']
        render_agent_status(state.get('status', 'unknown'))
        input_data, output_data = extract_agent_io(state, "RetrieverAgent")
        render_agent_io(input_data, output_data, "RetrieverAgent")
    else:
        st.info("No retriever data available yet. Run a query to see the retriever in action.")

def render_generator_tab(agent_data: Dict[str, Any]):
    """Render SQL Generator Agent tab"""
    st.markdown("## 💻 SQL Generator Agent")
    
    if 'SQLGeneratorAgent' in agent_data['agent_states']:
        state = agent_data['agent_states']['SQLGeneratorAgent']
        render_agent_status(state.get('status', 'unknown'))
        input_data, output_data = extract_agent_io(state, "SQLGeneratorAgent")
        render_agent_io(input_data, output_data, "SQLGeneratorAgent")
    else:
        st.info("No generator data available yet. Run a query to see the SQL generation in action.")

def render_validator_tab(agent_data: Dict[str, Any]):
    """Render Validator Agent tab"""
    st.markdown("## ✅ Validator Agent")
    
    if 'ValidatorAgent' in agent_data['agent_states']:
        state = agent_data['agent_states']['ValidatorAgent']
        render_agent_status(state.get('status', 'unknown'))
        input_data, output_data = extract_agent_io(state, "ValidatorAgent")
        render_agent_io(input_data, output_data, "ValidatorAgent")
    else:
        st.info("No validator data available yet. Run a query to see the validation in action.")

def render_executor_tab(agent_data: Dict[str, Any]):
    """Render Executor Agent tab"""
    st.markdown("## ⚡ Executor Agent")
    
    if 'ExecutorAgent' in agent_data['agent_states']:
        state = agent_data['agent_states']['ExecutorAgent']
        render_agent_status(state.get('status', 'unknown'))
        input_data, output_data = extract_agent_io(state, "ExecutorAgent")
        render_agent_io(input_data, output_data, "ExecutorAgent")
    else:
        st.info("No executor data available yet. Run a query to see the execution in action.")

def render_summarizer_tab(agent_data: Dict[str, Any]):
    """Render Summarizer Agent tab"""
    st.markdown("## 📝 Summarizer Agent")
    
    if 'SummarizerAgent' in agent_data['agent_states']:
        state = agent_data['agent_states']['SummarizerAgent']
        render_agent_status(state.get('status', 'unknown'))
        input_data, output_data = extract_agent_io(state, "SummarizerAgent")
        render_agent_io(input_data, output_data, "SummarizerAgent")
    else:
        st.info("No summarizer data available yet. Run a query to see the summarization in action.")

def render_agent_tabs(agent_data: Dict[str, Any]):
    """Render all agent tabs"""
    # Create tabs for each agent
    planner_tab, retriever_tab, generator_tab, validator_tab, executor_tab, summarizer_tab = st.tabs([
        "🎯 Planner",
        "🔍 Retriever",
        "💻 Generator",
        "✅ Validator",
        "⚡ Executor",
        "📝 Summarizer"
    ])
    
    # Render each agent's tab
    with planner_tab:
        render_planner_tab(agent_data)
    
    with retriever_tab:
        render_retriever_tab(agent_data)
    
    with generator_tab:
        render_generator_tab(agent_data)
    
    with validator_tab:
        render_validator_tab(agent_data)
    
    with executor_tab:
        render_executor_tab(agent_data)
    
    with summarizer_tab:
        render_summarizer_tab(agent_data)