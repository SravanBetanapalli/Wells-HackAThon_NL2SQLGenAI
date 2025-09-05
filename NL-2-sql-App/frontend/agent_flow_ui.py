import streamlit as st
import json
from typing import Dict, Any
import pandas as pd

def render_json(data: Any) -> None:
    """Render JSON data in a formatted way"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    st.json(data)

def render_agent_flow_tabs(agent_data: Dict[str, Any]) -> None:
    """Render agent flow information in tabs"""
    
    # Create tabs for different views
    overview_tab, details_tab, history_tab = st.tabs([
        "🔍 Agent Overview",
        "📊 Agent Details",
        "📜 Flow History"
    ])
    
    with overview_tab:
        st.markdown("### 🤖 Agent Status Overview")
        
        # Create status indicators
        for agent_name, state in agent_data['agent_states'].items():
            status = state.get('status', 'unknown')
            status_color = {
                'started': '🟡',
                'completed': '🟢',
                'failed': '🔴',
                'unknown': '⚪'
            }.get(status, '⚪')
            
            st.markdown(f"{status_color} **{agent_name}**: {status}")
    
    with details_tab:
        st.markdown("### 📊 Agent Details")
        
        # Create expandable sections for each agent
        for agent_name, state in agent_data['agent_states'].items():
            with st.expander(f"🤖 {agent_name}"):
                # Input section
                st.markdown("#### 📥 Input")
                if 'input_args' in state:
                    render_json(state['input_args'])
                if 'input_kwargs' in state:
                    render_json(state['input_kwargs'])
                
                # Output section
                st.markdown("#### 📤 Output")
                if 'output' in state:
                    render_json(state['output'])
                
                # Error section if applicable
                if 'error' in state:
                    st.markdown("#### ❌ Error")
                    st.error(state['error'])
    
    with history_tab:
        st.markdown("### 📜 Flow History")
        
        # Convert flow history to DataFrame for better display
        if agent_data['flow_history']:
            df = pd.DataFrame(agent_data['flow_history'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp', ascending=False)
            
            # Display as table
            st.dataframe(
                df,
                column_config={
                    "timestamp": "Time",
                    "agent": "Agent",
                    "state": "State"
                },
                hide_index=True
            )
            
            # Show detailed view in expander
            with st.expander("🔍 Detailed Flow History"):
                for entry in agent_data['flow_history']:
                    st.markdown(f"**{entry['timestamp']}** - {entry['agent']}")
                    render_json(entry['state'])
