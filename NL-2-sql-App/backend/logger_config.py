import logging
import os
import sys
from datetime import datetime
from functools import wraps
import json
from typing import Any, Dict, Optional

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'logs/agent_flow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

# Create a logger
logger = logging.getLogger('agent_flow')

class AgentLogger:
    """Logger class to track agent flow and store agent states"""
    
    def __init__(self):
        self.agent_states = {}
        self.flow_history = []
        
    def log_agent_state(self, agent_name: str, state: Dict[str, Any]):
        """Log agent state and store for UI display"""
        # Store the original data structures
        self.agent_states[agent_name] = state
        self.flow_history.append({
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'state': state
        })
        
    def get_agent_state(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the latest state of an agent"""
        return self.agent_states.get(agent_name)
    
    def get_flow_history(self) -> list:
        """Get the complete flow history"""
        return self.flow_history

# Create global agent logger instance
agent_logger = AgentLogger()

def log_agent_flow(agent_name: str):
    """Decorator to log agent entry and exit with input/output"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log entry
            entry_log = {
                'event': 'entry',
                'input_args': args,  # Keep as tuple
                'input_kwargs': kwargs,  # Keep as dict
                'timestamp': datetime.now().isoformat()
            }
            
            # For console logging, convert to JSON-safe format
            console_entry = {
                'event': 'entry',
                'input_args': [str(arg) if not isinstance(arg, (str, int, float, bool, list, dict)) else arg for arg in args],
                'input_kwargs': {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v for k, v in kwargs.items()},
                'timestamp': entry_log['timestamp']
            }
            logger.info(f"🔵 {agent_name} Entry | {json.dumps(console_entry, indent=2)}")
            
            # Store original data structures in agent state
            agent_logger.log_agent_state(agent_name, {'status': 'started', **entry_log})
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log success exit
                exit_log = {
                    'event': 'exit',
                    'status': 'success',
                    'output': result,  # Keep as original type
                    'timestamp': datetime.now().isoformat()
                }
                
                # For console logging, convert to JSON-safe format
                console_exit = {
                    'event': 'exit',
                    'status': 'success',
                    'output': str(result) if not isinstance(result, (str, int, float, bool, list, dict)) else result,
                    'timestamp': exit_log['timestamp']
                }
                logger.info(f"✅ {agent_name} Exit | {json.dumps(console_exit, indent=2)}")
                
                # Store original data structures in agent state
                agent_logger.log_agent_state(agent_name, {'status': 'completed', **exit_log})
                
                return result
                
            except Exception as e:
                # Log error exit
                error_log = {
                    'event': 'exit',
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"❌ {agent_name} Error | {json.dumps(error_log, indent=2)}")
                agent_logger.log_agent_state(agent_name, {'status': 'failed', **error_log})
                raise
                
        return wrapper
    return decorator

def get_agent_flow_data() -> Dict[str, Any]:
    """Get all agent flow data for UI display"""
    return {
        'agent_states': agent_logger.agent_states,
        'flow_history': agent_logger.flow_history
    }