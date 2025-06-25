#!/usr/bin/env python3
"""
Script to set up the database schema for vector embeddings
"""

import psycopg2
import sys
from .config import DB_CONFIG

def setup_database():
    """Set up database and schema"""
    try:
        # Connect to whatsapp_bot database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Enable pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ Enabled pgvector extension")
        
        # Create schemes table with proper structure matching CSV
        create_schemes_table = """
        CREATE TABLE IF NOT EXISTS schemes (
            id BIGSERIAL PRIMARY KEY,
            slug VARCHAR(255) UNIQUE NOT NULL,
            url TEXT,
            name VARCHAR(500) NOT NULL,
            tags TEXT,
            state VARCHAR(100),
            category VARCHAR(255),
            description TEXT,
            age_requirements JSONB,
            gender VARCHAR(100),
            caste TEXT,
            is_minority BOOLEAN DEFAULT false,
            is_differently_abled BOOLEAN DEFAULT false,
            is_dbt BOOLEAN DEFAULT false,
            is_widowed_or_divorced BOOLEAN DEFAULT false,
            is_bpl BOOLEAN DEFAULT false,
            is_student BOOLEAN DEFAULT false,
            occupation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_schemes_table)
        print("✅ Created schemes table")
        
        # Create scheme_embeddings table
        create_embeddings_table = """
        CREATE TABLE IF NOT EXISTS scheme_embeddings (
            id BIGSERIAL PRIMARY KEY,
            scheme_id BIGINT REFERENCES schemes(id) ON DELETE CASCADE,
            embedding vector(384),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scheme_id)
        )
        """
        cursor.execute(create_embeddings_table)
        print("✅ Created scheme_embeddings table")
        
        # Create index for vector similarity search
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheme_embeddings_vector ON scheme_embeddings USING ivfflat (embedding vector_cosine_ops)")
        print("✅ Created vector search index")
        
        # Create additional indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_schemes_slug ON schemes(slug);",
            "CREATE INDEX IF NOT EXISTS idx_schemes_state ON schemes(state);",
            "CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);",
            "CREATE INDEX IF NOT EXISTS idx_schemes_caste ON schemes(caste);",
            "CREATE INDEX IF NOT EXISTS idx_schemes_is_bpl ON schemes(is_bpl);",
            "CREATE INDEX IF NOT EXISTS idx_schemes_is_student ON schemes(is_student);"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        print("✅ Created additional indexes")
        
        conn.close()
        print("🎉 Database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database()
if __name__ == "__main__":
    setup_database()
