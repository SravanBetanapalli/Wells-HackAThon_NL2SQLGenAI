"""Initialize the SQLite database with schema and sample data"""
import os
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database with schema and sample data"""
    # Get the current directory
    current_dir = Path(__file__).parent
    db_path = current_dir.parent / "banking.db"
    schema_path = current_dir / "schema.sql"
    data_path = current_dir / "sample_data.sql"
    
    logger.info(f"Initializing database at: {db_path}")
    logger.info(f"Using schema from: {schema_path}")
    logger.info(f"Using sample data from: {data_path}")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop all existing tables
        logger.info("Dropping existing tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[0]
            logger.info(f"Dropping table: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
        
        # Execute schema SQL
        logger.info("Creating database schema...")
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            cursor.executescript(schema_sql)
        
        # Execute sample data SQL
        logger.info("Loading sample data...")
        with open(data_path, 'r') as f:
            data_sql = f.read()
            cursor.executescript(data_sql)
        
        conn.commit()
        logger.info("Database initialized successfully!")
        
        # Verify tables and data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info("Created tables: %s", ", ".join(table[0] for table in tables))
        
        # Sample counts
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
            count = cursor.fetchone()[0]
            logger.info(f"Table {table[0]}: {count} rows")
        
    except sqlite3.Error as e:
        logger.error("Database initialization failed: %s", str(e))
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db()