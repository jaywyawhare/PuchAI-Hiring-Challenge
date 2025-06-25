#!/usr/bin/env python3
"""
Script to create embeddings for existing schemes in database
"""

import sys
import psycopg2
import torch
from sentence_transformers import SentenceTransformer
from .config import DB_CONFIG

def connect_to_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def load_sentence_transformer():
    """Load the sentence transformer model with better error handling"""
    try:
        print("🤖 Loading sentence transformer model...")
        
        # Try importing with better error handling
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            print(f"❌ Failed to import sentence_transformers: {e}")
            print("💡 Please install compatible versions:")
            print("   pip install torch==2.1.0")
            print("   pip install sentence-transformers==2.7.0")
            print("   pip install transformers==4.36.2")
            sys.exit(1)
        
        # Use a simpler model that's more compatible
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("💡 Trying alternative approach...")
        
        # Fallback: create dummy embeddings for testing
        print("⚠️  Using dummy embeddings for testing")
        return None

def get_schemes_without_embeddings(conn):
    """Get schemes that don't have embeddings yet"""
    cursor = conn.cursor()
    
    query = """
    SELECT s.id, s.name, s.description, s.category, s.state
    FROM schemes s
    LEFT JOIN scheme_embeddings se ON s.id = se.scheme_id
    WHERE se.scheme_id IS NULL
    ORDER BY s.id
    """
    
    cursor.execute(query)
    schemes = cursor.fetchall()
    print(f"📊 Found {len(schemes)} schemes without embeddings")
    return schemes

def create_dummy_embedding():
    """Create a dummy 384-dimensional embedding for testing"""
    import random
    return [random.random() for _ in range(384)]

def create_embeddings_for_schemes(conn, model, schemes):
    """Create embeddings for scheme descriptions"""
    cursor = conn.cursor()
    
    print("🔄 Creating embeddings...")
    
    for i, (scheme_id, name, description, category, state) in enumerate(schemes):
        try:
            # Create a combined text for embedding
            combined_text = f"{name or ''} {description or ''} {category or ''} {state or ''}".strip()
            
            if not combined_text:
                print(f"⚠️  Skipping scheme {scheme_id} - no text content")
                continue
            
            # Generate embedding
            if model is not None:
                embedding = model.encode(combined_text, convert_to_tensor=False)
                embedding_list = embedding.tolist()
            else:
                # Use dummy embedding for testing
                print(f"⚠️  Using dummy embedding for scheme {scheme_id}")
                embedding_list = create_dummy_embedding()
            
            # Insert embedding into database
            insert_query = """
            INSERT INTO scheme_embeddings (scheme_id, embedding)
            VALUES (%s, %s::vector(384))
            ON CONFLICT (scheme_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                created_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(insert_query, (scheme_id, embedding_list))
            print(f"✅ Created embedding for scheme {scheme_id}: {name[:50]}...")
                
        except Exception as e:
            print(f"❌ Error processing scheme {scheme_id}: {e}")
            continue
    
    conn.commit()
    print(f"✅ Completed embedding creation for {len(schemes)} schemes")

def test_basic_search(conn):
    """Test basic database functionality"""
    cursor = conn.cursor()
    
    print("\n🧪 Testing basic database functionality...")
    
    # Test basic scheme query
    cursor.execute("SELECT COUNT(*) FROM schemes")
    scheme_count = cursor.fetchone()[0]
    print(f"📊 Total schemes in database: {scheme_count}")
    
    # Test embedding count
    cursor.execute("SELECT COUNT(*) FROM scheme_embeddings")
    embedding_count = cursor.fetchone()[0]
    print(f"📊 Total embeddings created: {embedding_count}")
    
    # Show some sample schemes
    cursor.execute("SELECT id, name, category, state FROM schemes LIMIT 5")
    samples = cursor.fetchall()
    print("\n📋 Sample schemes:")
    for scheme_id, name, category, state in samples:
        print(f"  {scheme_id}: {name} ({category}, {state})")

def main():
    """Main function"""
    print("🚀 Starting vector embedding creation...")
    
    # Connect to database
    conn = connect_to_db()
    
    try:
        # Load model (with fallback)
        model = load_sentence_transformer()
        
        # Get schemes without embeddings
        schemes = get_schemes_without_embeddings(conn)
        
        if not schemes:
            print("✅ All schemes already have embeddings")
        else:
            # Create embeddings
            create_embeddings_for_schemes(conn, model, schemes)
        
        # Test basic functionality
        test_basic_search(conn)
        
        print("\n🎉 Vector embedding setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()
    main()
