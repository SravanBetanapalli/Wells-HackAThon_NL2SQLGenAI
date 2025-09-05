"""Initialize schema embeddings"""
import logging
from backend.schema_processor import initialize_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Initializing schema embeddings...")
        initialize_schema()
        logger.info("Schema initialization completed successfully")
    except Exception as e:
        logger.error(f"Schema initialization failed: {str(e)}")
        raise
