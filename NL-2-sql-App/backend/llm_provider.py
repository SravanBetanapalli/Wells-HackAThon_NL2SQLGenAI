"""LLM Provider Abstraction Layer"""
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
import json
from openai import OpenAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_openai_error(error: Exception) -> None:
    """Log OpenAI error details"""
    try:
        error_dict = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": "❌"
        }
        logger.error(f"OpenAI API Error:\n{json.dumps(error_dict, indent=2)}")
    except Exception as e:
        logger.error(f"Error logging OpenAI error: {str(e)}")

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text from prompt"""
        pass

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings for texts"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI-specific implementation"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            raise ValueError("OPENAI_API_KEY not found")
            
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"✅ Initialized OpenAI provider with model: {self.model}")
    

    def generate_text(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text using OpenAI's chat completion"""
        try:
            # Log the input prompt as JSON
            logger.info("🤖 LLM PROVIDER - INPUT JSON:")
            logger.info("=" * 80)
            try:
                # Check if prompt is already a dict
                if isinstance(prompt, dict):
                    logger.info(json.dumps(prompt, indent=2))
                    logger.info("✅ Input is already a dictionary")
                else:
                    # Try to parse as JSON for pretty printing
                    prompt_dict = json.loads(prompt)
                    logger.info(json.dumps(prompt_dict, indent=2))
                    logger.info("✅ Input successfully parsed as JSON")
            except json.JSONDecodeError:
                # If not JSON, log as regular text
                logger.info("Raw prompt (not JSON):")
                logger.info(prompt)
                logger.info("⚠️ Input is not valid JSON format")
            except Exception as e:
                logger.error(f"Error processing prompt: {str(e)}")
                logger.info("Raw prompt:")
                logger.info(prompt)
            logger.info("=" * 80)
            
            # Log additional parameters
            if kwargs:
                logger.info("🔧 Additional parameters:")
                logger.info(json.dumps(kwargs, indent=2))
            
            temperature = kwargs.get('temperature', 0.1)
            max_tokens = kwargs.get('max_tokens', 1024)
            
            logger.info(f"🚀 Calling OpenAI API with model: {self.model}, temperature: {temperature}, max_tokens: {max_tokens}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Log the raw response
            logger.info("🤖 LLM PROVIDER - RAW RESPONSE:")
            logger.info("=" * 80)
            logger.info(f"Response object: {response}")
            logger.info(f"Choices count: {len(response.choices) if response.choices else 0}")
            if response.choices:
                logger.info(f"First choice content: {response.choices[0].message.content if response.choices[0].message else 'No content'}")
            logger.info("=" * 80)
            
            if not response.choices:
                logger.error("❌ OpenAI returned empty choices")
                return None
                
            generated_text = response.choices[0].message.content
            
            # Log the final output as JSON
            logger.info("🤖 LLM PROVIDER - OUTPUT JSON:")
            logger.info("=" * 80)
            try:
                # Try to parse as JSON for pretty printing
                response_dict = json.loads(generated_text)
                logger.info(json.dumps(response_dict, indent=2))
                logger.info("✅ Response successfully parsed as JSON")
            except json.JSONDecodeError:
                # If not JSON, log as regular text
                logger.info("Response (not JSON):")
                logger.info(generated_text)
                logger.info("⚠️ Response is not valid JSON format")
            logger.info("=" * 80)
            
            # Log success with green tick
            logger.info("✅ LLM interaction completed successfully")
            logger.debug(f"Generated text length: {len(generated_text)}")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"❌ LLM PROVIDER - ERROR:")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("=" * 80)
            log_openai_error(e)
            return None
    

    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings using OpenAI's embedding model"""
        try:
            logger.info(f"🔄 Generating embeddings with {self.embedding_model}")
            logger.info(f"Number of texts: {len(texts)}")
            
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            if not response.data:
                logger.error("❌ OpenAI returned empty embedding data")
                return None
            
            embeddings = [data.embedding for data in response.data]
            
            # Log success
            logger.info("✅ Successfully generated embeddings")
            logger.debug(f"Generated {len(embeddings)} embeddings")
            
            return embeddings
            
        except Exception as e:
            log_openai_error(e)
            return None

class LLMFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(provider_type: str = "openai") -> LLMProvider:
        """Create and return an LLM provider instance"""
        logger.info(f"Creating LLM provider of type: {provider_type}")
        
        if provider_type.lower() == "openai":
            return OpenAIProvider()
        else:
            logger.error(f"❌ Unsupported provider type: {provider_type}")
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

# Global LLM provider instance
_llm_provider: Optional[LLMProvider] = None

def get_llm_provider() -> LLMProvider:
    """Get or create the global LLM provider instance"""
    global _llm_provider
    if _llm_provider is None:
        provider_type = os.getenv("LLM_PROVIDER", "openai")
        logger.info(f"Initializing global LLM provider of type: {provider_type}")
        _llm_provider = LLMFactory.create_provider(provider_type)
    return _llm_provider