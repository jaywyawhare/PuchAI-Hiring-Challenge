import psycopg2
import logging
from typing import Dict, List, Optional, Any
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'whatsapp_bot'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

class SchemeSearchService:
    """Service for searching government schemes using vector embeddings."""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            logger.info("Loading sentence transformer model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None
    
    def _get_db_connection(self):
        """Get database connection."""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def search_schemes(
        self,
        query: str,
        state: Optional[str] = None,
        category: Optional[str] = None,
        gender: Optional[str] = None,
        caste: Optional[str] = None,
        is_bpl: Optional[bool] = None,
        is_student: Optional[bool] = None,
        is_minority: Optional[bool] = None,
        is_differently_abled: Optional[bool] = None,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search schemes using vector embeddings with optional filters.
        
        Args:
            query: Search query text
            state: Optional state filter
            category: Optional category filter
            gender: Optional gender filter
            caste: Optional caste filter
            is_bpl: Optional BPL filter
            is_student: Optional student filter
            is_minority: Optional minority filter
            is_differently_abled: Optional disability filter
            age_min: Optional minimum age
            age_max: Optional maximum age
            limit: Maximum number of results
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            if not self.model:
                return {
                    "error": "Search model not available",
                    "results": [],
                    "total_count": 0
                }
            
            # Generate embedding for the query
            query_embedding = self.model.encode(query, convert_to_tensor=False)
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Build the SQL query with filters
            base_query = """
                SELECT 
                    s.id,
                    s.name,
                    s.description,
                    s.category,
                    s.state,
                    s.gender,
                    s.caste,
                    s.is_bpl,
                    s.is_student,
                    s.is_minority,
                    s.is_differently_abled,
                    s.age_requirements,
                    s.url,
                    s.tags,
                    (se.embedding <=> %s::vector(384)) AS similarity_score
                FROM schemes s
                JOIN scheme_embeddings se ON s.id = se.scheme_id
                WHERE se.embedding IS NOT NULL
            """
            
            params = [query_embedding.tolist()]
            conditions = []
            
            # Add optional filters
            if state and state.lower() != 'all':
                conditions.append("(s.state ILIKE %s OR s.state = 'All')")
                params.append(f"%{state}%")
            
            if category:
                conditions.append("s.category ILIKE %s")
                params.append(f"%{category}%")
            
            if gender:
                conditions.append("(s.gender ILIKE %s OR s.gender = 'female')")
                params.append(f"%{gender}%")
            
            if caste:
                conditions.append("s.caste ILIKE %s")
                params.append(f"%{caste}%")
            
            if is_bpl is not None:
                conditions.append("s.is_bpl = %s")
                params.append(is_bpl)
            
            if is_student is not None:
                conditions.append("s.is_student = %s")
                params.append(is_student)
            
            if is_minority is not None:
                conditions.append("s.is_minority = %s")
                params.append(is_minority)
            
            if is_differently_abled is not None:
                conditions.append("s.is_differently_abled = %s")
                params.append(is_differently_abled)
            
            # Add age filters (simplified - you may need to adjust based on age_requirements structure)
            if age_min is not None or age_max is not None:
                if age_min is not None and age_max is not None:
                    conditions.append("""
                        (s.age_requirements IS NULL OR 
                         s.age_requirements::text LIKE '%"gte":' || %s || '%' OR
                         s.age_requirements::text LIKE '%"lte":' || %s || '%')
                    """)
                    params.extend([age_min, age_max])
            
            # Add conditions to query
            if conditions:
                base_query += " AND " + " AND ".join(conditions)
            
            # Add ordering and limit
            base_query += " ORDER BY similarity_score ASC LIMIT %s"
            params.append(limit)
            
            logger.info(f"Executing search query with {len(params)} parameters")
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            # Format results
            formatted_results = []
            for row in results:
                scheme = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "category": row[3],
                    "state": row[4],
                    "gender": row[5],
                    "caste": row[6],
                    "is_bpl": row[7],
                    "is_student": row[8],
                    "is_minority": row[9],
                    "is_differently_abled": row[10],
                    "age_requirements": row[11],
                    "url": row[12],
                    "tags": row[13],
                    "similarity_score": float(row[14])
                }
                formatted_results.append(scheme)
            
            # Get total count for metadata
            count_query = """
                SELECT COUNT(*)
                FROM schemes s
                JOIN scheme_embeddings se ON s.id = se.scheme_id
                WHERE se.embedding IS NOT NULL
            """
            
            if conditions:
                count_query += " AND " + " AND ".join(conditions[:-1] if age_min or age_max else conditions)
            
            cursor.execute(count_query, params[1:-1])  # Exclude embedding and limit params
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "results": formatted_results,
                "total_count": len(formatted_results),
                "total_available": total_count,
                "query": query,
                "filters_applied": {
                    "state": state,
                    "category": category,
                    "gender": gender,
                    "caste": caste,
                    "is_bpl": is_bpl,
                    "is_student": is_student,
                    "is_minority": is_minority,
                    "is_differently_abled": is_differently_abled,
                    "age_range": f"{age_min}-{age_max}" if age_min or age_max else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in scheme search: {e}")
            return {
                "error": str(e),
                "results": [],
                "total_count": 0
            }
    
    async def get_scheme_categories(self) -> List[str]:
        """Get all available scheme categories."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT category 
                FROM schemes 
                WHERE category IS NOT NULL 
                ORDER BY category
            """)
            
            categories = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return categories
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def get_scheme_states(self) -> List[str]:
        """Get all available states."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT state 
                FROM schemes 
                WHERE state IS NOT NULL 
                ORDER BY state
            """)
            
            states = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return states
            
        except Exception as e:
            logger.error(f"Error getting states: {e}")
            return []
