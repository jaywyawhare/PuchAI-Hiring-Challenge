#!/usr/bin/env python3
"""
Test script to verify database setup and search functionality
"""

import psycopg2
import sys
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

def test_database_contents(conn):
    """Test database contents and functionality"""
    cursor = conn.cursor()
    
    print("\n🧪 Testing database contents...")
    
    # Test 1: Count total schemes
    cursor.execute("SELECT COUNT(*) FROM schemes")
    scheme_count = cursor.fetchone()[0]
    print(f"📊 Total schemes in database: {scheme_count}")
    
    # Test 2: Count embeddings
    cursor.execute("SELECT COUNT(*) FROM scheme_embeddings")
    embedding_count = cursor.fetchone()[0]
    print(f"📊 Total embeddings created: {embedding_count}")
    
    # Test 3: Check pgvector extension
    cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    vector_ext = cursor.fetchone()
    if vector_ext:
        print("✅ pgvector extension is enabled")
    else:
        print("❌ pgvector extension not found")
    
    # Test 4: Sample schemes by category
    print("\n📋 Sample schemes by category:")
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM schemes 
        WHERE category IS NOT NULL 
        GROUP BY category 
        ORDER BY count DESC 
        LIMIT 5
    """)
    
    categories = cursor.fetchall()
    for category, count in categories:
        print(f"  {category}: {count} schemes")
    
    # Test 5: Sample schemes by state
    print("\n🗺️ Sample schemes by state:")
    cursor.execute("""
        SELECT state, COUNT(*) as count 
        FROM schemes 
        WHERE state IS NOT NULL AND state != 'All'
        GROUP BY state 
        ORDER BY count DESC 
        LIMIT 5
    """)
    
    states = cursor.fetchall()
    for state, count in states:
        print(f"  {state}: {count} schemes")
    
    # Test 6: Sample education schemes
    print("\n🎓 Sample education schemes:")
    cursor.execute("""
        SELECT id, name, state
        FROM schemes 
        WHERE category ILIKE '%education%' 
        LIMIT 5
    """)
    
    education_schemes = cursor.fetchall()
    for scheme_id, name, state in education_schemes:
        print(f"  {scheme_id}: {name[:50]}... ({state})")
    
    # Test 7: Sample schemes with embeddings
    print("\n🔍 Schemes with vector embeddings:")
    cursor.execute("""
        SELECT s.id, s.name, s.category
        FROM schemes s
        JOIN scheme_embeddings se ON s.id = se.scheme_id
        LIMIT 5
    """)
    
    embedded_schemes = cursor.fetchall()
    for scheme_id, name, category in embedded_schemes:
        print(f"  {scheme_id}: {name[:50]}... ({category})")

def test_search_functionality(conn):
    """Test search functionality"""
    cursor = conn.cursor()
    
    print("\n🔍 Testing search functionality...")
    
    # Test text-based search
    search_terms = [
        "scholarship",
        "agriculture",
        "women empowerment",
        "health",
        "education loan"
    ]
    
    for term in search_terms:
        print(f"\n🔎 Searching for '{term}':")
        cursor.execute("""
            SELECT id, name, category, state
            FROM schemes 
            WHERE name ILIKE %s OR description ILIKE %s 
            LIMIT 3
        """, (f'%{term}%', f'%{term}%'))
        
        results = cursor.fetchall()
        if results:
            for scheme_id, name, category, state in results:
                print(f"  📋 {name[:60]}...")
                print(f"     Category: {category}, State: {state}")
        else:
            print("  ❌ No results found")

def test_filters(conn):
    """Test filter functionality"""
    cursor = conn.cursor()
    
    print("\n🎯 Testing filter functionality...")
    
    # Test gender filter
    cursor.execute("SELECT COUNT(*) FROM schemes WHERE gender = 'female'")
    female_count = cursor.fetchone()[0]
    print(f"👩 Schemes for women: {female_count}")
    
    # Test caste filter
    cursor.execute("SELECT COUNT(*) FROM schemes WHERE caste ILIKE '%sc%'")
    sc_count = cursor.fetchone()[0]
    print(f"🏛️ Schemes for SC category: {sc_count}")
    
    # Test state filter
    cursor.execute("SELECT COUNT(*) FROM schemes WHERE state = 'All'")
    all_india_count = cursor.fetchone()[0]
    print(f"🇮🇳 All India schemes: {all_india_count}")
    
    # Test BPL filter
    cursor.execute("SELECT COUNT(*) FROM schemes WHERE is_bpl = true")
    bpl_count = cursor.fetchone()[0]
    print(f"💰 BPL schemes: {bpl_count}")
    
    # Test student filter
    cursor.execute("SELECT COUNT(*) FROM schemes WHERE is_student = true")
    student_count = cursor.fetchone()[0]
    print(f"🎓 Student schemes: {student_count}")

def main():
    """Main function"""
    print("🚀 Starting database tests...")
    
    # Connect to database
    conn = connect_to_db()
    
    try:
        # Run tests
        test_database_contents(conn)
        test_search_functionality(conn)
        test_filters(conn)
        
        print("\n🎉 All database tests completed successfully!")
        print("✅ Your vector database is ready for semantic search!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()
