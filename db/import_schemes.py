"""
Script to import schemes from CSV to database with embeddings
"""

import csv
import sys
import os
import json
import psycopg2
from psycopg2.extras import execute_values
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

def parse_age_requirements(age_str):
    """Parse age requirements from JSON string and return as JSON string or None"""
    try:
        if not age_str or age_str == '':
            return None
        val = json.loads(age_str)
        return json.dumps(val)  # Always return as JSON string
    except:
        return None

def parse_boolean_field(value):
    """Parse boolean fields from CSV"""
    if not value or value == '':
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'y']
    return False

def clean_text_field(value, max_length=None):
    """Clean and truncate text fields if necessary"""
    if not value:
        return ''
    
    # Clean the text
    cleaned = str(value).strip()
    
    # Truncate if max_length is specified
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length-3] + '...'
    
    return cleaned

def import_schemes_data(conn, csv_file):
    """Import schemes data from CSV file"""
    print(f"📖 Reading CSV file: {csv_file}")
    
    try:
        # Read CSV file
        schemes_data = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row_num, row in enumerate(reader, 1):
                try:
                    # Clean and prepare data
                    scheme_data = (
                        clean_text_field(row.get('slug', ''), 255),
                        clean_text_field(row.get('url', '')),
                        clean_text_field(row.get('name', ''), 500),
                        clean_text_field(row.get('tags', '')),
                        clean_text_field(row.get('state', ''), 100),
                        clean_text_field(row.get('category', ''), 255),
                        clean_text_field(row.get('description', '')),
                        parse_age_requirements(row.get('age', '')),
                        clean_text_field(row.get('gender', ''), 100),
                        clean_text_field(row.get('caste', '')),
                        parse_boolean_field(row.get('is_minority', False)),
                        parse_boolean_field(row.get('is_differently_abled', False)),
                        parse_boolean_field(row.get('is_dbt', False)),
                        parse_boolean_field(row.get('is_widowed_or_divorced', False)),
                        parse_boolean_field(row.get('is_bpl', False)),
                        parse_boolean_field(row.get('is_student', False)),
                        clean_text_field(row.get('occupation', ''))
                    )
                    schemes_data.append(scheme_data)
                except Exception as e:
                    print(f"⚠️  Warning: Error processing row {row_num}: {e}")
                    continue
        
        print(f"📊 Found {len(schemes_data)} valid schemes in CSV")
        
        # Insert data using execute_values for better performance
        cursor = conn.cursor()
        
        insert_sql = """
        INSERT INTO schemes (
            slug, url, name, tags, state, category, description, 
            age_requirements, gender, caste, is_minority, is_differently_abled,
            is_dbt, is_widowed_or_divorced, is_bpl, is_student, occupation
        ) VALUES %s
        ON CONFLICT (slug) DO UPDATE SET
            url = EXCLUDED.url,
            name = EXCLUDED.name,
            tags = EXCLUDED.tags,
            state = EXCLUDED.state,
            category = EXCLUDED.category,
            description = EXCLUDED.description,
            age_requirements = EXCLUDED.age_requirements,
            gender = EXCLUDED.gender,
            caste = EXCLUDED.caste,
            is_minority = EXCLUDED.is_minority,
            is_differently_abled = EXCLUDED.is_differently_abled,
            is_dbt = EXCLUDED.is_dbt,
            is_widowed_or_divorced = EXCLUDED.is_widowed_or_divorced,
            is_bpl = EXCLUDED.is_bpl,
            is_student = EXCLUDED.is_student,
            occupation = EXCLUDED.occupation
        """
        
        execute_values(cursor, insert_sql, schemes_data)
        conn.commit()
        
        print(f"✅ Successfully imported {len(schemes_data)} schemes")
        
        # Verify import
        cursor.execute("SELECT COUNT(*) FROM schemes")
        count = cursor.fetchone()[0]
        print(f"📊 Total schemes in database: {count}")
        
    except Exception as e:
        print(f"❌ Error importing data: {e}")
        conn.rollback()
        raise

def main():
    """Main function"""
    print("🚀 Starting schemes data import...")
    
    csv_file = "data_new.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Connect to database
    conn = connect_to_db()
    
    try:
        # Import data
        import_schemes_data(conn, csv_file)
        
        print("🎉 Schemes data import completed successfully!")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()