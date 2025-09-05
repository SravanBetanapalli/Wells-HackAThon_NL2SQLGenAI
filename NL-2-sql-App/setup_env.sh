#!/bin/bash

# Create .env file with configuration
cat > .env << EOL
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-odhZJAn-z88ROhv6qkM4jGAKE35zhAbjD13FljoOfjKhQYgigffCgk2r08EYSpLIrmjYR9l7A5T3BlbkFJ7oPBwWuEDBbwkRtNPAYI6DikNRm1QEZ5wvy6n_txmLXcHpCbgJEdoqkifbQfIph7pMz8xW_cA
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Database Configuration
SQLITE_DB_PATH=banking.db

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_PII_SCANNING=true

# Application Settings
DEBUG=true
STREAMLIT_THEME=light
EOL

echo "✅ Environment configuration created!"
