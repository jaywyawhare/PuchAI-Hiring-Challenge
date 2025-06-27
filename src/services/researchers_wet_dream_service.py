"""
Researcher's Wet Dream Service - Advanced Autonomous Research Tool
Combines deep research with intelligent thinking for comprehensive research sessions.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Set
import logging
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription, ToolService
from datetime import datetime
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class ResearchTopicManager:
    """Manages research topics and their data in JSON format."""
    
    def __init__(self, storage_file: str = "research_topics.json"):
        self.storage_file = Path(storage_file)
        self.research_topics = self._load_research_topics()
        
    def _load_research_topics(self) -> Dict[str, Any]:
        """Load research topics from JSON file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data.get('topics', {}))} research topics from {self.storage_file}")
                    return data
            except Exception as e:
                logger.error(f"Error loading research topics: {e}")
                return self._create_default_structure()
        else:
            logger.info(f"Creating new research topics file: {self.storage_file}")
            return self._create_default_structure()
    
    def _create_default_structure(self) -> Dict[str, Any]:
        """Create default JSON structure for research topics."""
        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Research topics and their associated data"
            },
            "topics": {},
            "concepts": {},
            "sessions": {},
            "relationships": [],
            "statistics": {
                "total_topics": 0,
                "total_sessions": 0,
                "total_concepts": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def _save_research_topics(self) -> None:
        """Save research topics to JSON file."""
        try:
            # Update statistics
            self.research_topics["statistics"]["total_topics"] = len(self.research_topics["topics"])
            self.research_topics["statistics"]["total_sessions"] = len(self.research_topics["sessions"])
            self.research_topics["statistics"]["total_concepts"] = len(self.research_topics["concepts"])
            self.research_topics["statistics"]["last_updated"] = datetime.now().isoformat()
            
            # Ensure directory exists
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.research_topics, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved research topics to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving research topics: {e}")
    
    def add_research_topic(self, topic: str, research_data: Dict[str, Any]) -> None:
        """Add or update a research topic."""
        topic_hash = self._hash_topic(topic)
        
        # Create topic entry
        topic_entry = {
            "topic": topic,
            "hash": topic_hash,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "sessions": [],
            "concepts": [],
            "related_topics": [],
            "summary": {
                "total_sessions": 0,
                "total_citations": 0,
                "total_concepts": 0,
                "last_session_date": None
            }
        }
        
        # Add session data
        session_id = research_data.get('session_id', f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        session_entry = {
            "session_id": session_id,
            "created": datetime.now().isoformat(),
            "research_depth": research_data.get('research_depth', 3),
            "thinking_depth": research_data.get('thinking_depth', 5),
            "total_iterations": research_data.get('total_iterations', 0),
            "total_sources": research_data.get('total_sources', 0),
            "citations": research_data.get('citations', []),
            "concepts": research_data.get('concepts', []),
            "knowledge_graph": research_data.get('knowledge_graph', {}),
            "final_analysis": research_data.get('final_analysis', ''),
            "reused_existing": research_data.get('reused_existing', False)
        }
        
        # Update topic with session data
        if topic_hash in self.research_topics["topics"]:
            # Update existing topic
            existing_topic = self.research_topics["topics"][topic_hash]
            existing_topic["last_updated"] = datetime.now().isoformat()
            existing_topic["sessions"].append(session_entry)
            
            # Update concepts
            existing_concepts = set(existing_topic["concepts"])
            new_concepts = set(research_data.get('concepts', []))
            existing_topic["concepts"] = list(existing_concepts | new_concepts)
            
            # Update summary
            existing_topic["summary"]["total_sessions"] = len(existing_topic["sessions"])
            existing_topic["summary"]["total_citations"] = sum(len(s.get('citations', [])) for s in existing_topic["sessions"])
            existing_topic["summary"]["total_concepts"] = len(existing_topic["concepts"])
            existing_topic["summary"]["last_session_date"] = datetime.now().isoformat()
        else:
            # Create new topic
            topic_entry["sessions"].append(session_entry)
            topic_entry["concepts"] = research_data.get('concepts', [])
            topic_entry["summary"]["total_sessions"] = 1
            topic_entry["summary"]["total_citations"] = len(research_data.get('citations', []))
            topic_entry["summary"]["total_concepts"] = len(research_data.get('concepts', []))
            topic_entry["summary"]["last_session_date"] = datetime.now().isoformat()
            
            self.research_topics["topics"][topic_hash] = topic_entry
        
        # Add to sessions
        self.research_topics["sessions"][session_id] = {
            "topic": topic,
            "topic_hash": topic_hash,
            "session_data": session_entry
        }
        
        # Index concepts
        for concept in research_data.get('concepts', []):
            if concept not in self.research_topics["concepts"]:
                self.research_topics["concepts"][concept] = []
            if topic_hash not in self.research_topics["concepts"][concept]:
                self.research_topics["concepts"][concept].append(topic_hash)
        
        # Save to file
        self._save_research_topics()
    
    def get_research_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get research data for a topic."""
        topic_hash = self._hash_topic(topic)
        return self.research_topics["topics"].get(topic_hash)
    
    def get_related_topics(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get related topics based on concept overlap."""
        topic_hash = self._hash_topic(topic)
        current_topic = self.research_topics["topics"].get(topic_hash)
        
        if not current_topic:
            return []
        
        current_concepts = set(current_topic["concepts"])
        related = []
        
        for other_hash, other_topic in self.research_topics["topics"].items():
            if other_hash == topic_hash:
                continue
            
            other_concepts = set(other_topic["concepts"])
            overlap = len(current_concepts & other_concepts)
            
            if overlap > 0:
                related.append({
                    "topic": other_topic["topic"],
                    "overlap_score": overlap / len(current_concepts) if current_concepts else 0,
                    "shared_concepts": list(current_concepts & other_concepts),
                    "last_updated": other_topic["last_updated"],
                    "total_sessions": other_topic["summary"]["total_sessions"]
                })
        
        # Sort by overlap score and return top results
        related.sort(key=lambda x: x['overlap_score'], reverse=True)
        return related[:limit]
    
    def search_concepts(self, concept: str) -> List[Dict[str, Any]]:
        """Search for topics containing a specific concept."""
        results = []
        if concept in self.research_topics["concepts"]:
            for topic_hash in self.research_topics["concepts"][concept]:
                topic_data = self.research_topics["topics"].get(topic_hash)
                if topic_data:
                    results.append({
                        "topic": topic_data["topic"],
                        "concept": concept,
                        "last_updated": topic_data["last_updated"],
                        "total_sessions": topic_data["summary"]["total_sessions"]
                    })
        return results
    
    def get_thinking_context(self, topic: str) -> Dict[str, Any]:
        """Get comprehensive context for thinking process."""
        topic_data = self.get_research_topic(topic)
        related_topics = self.get_related_topics(topic)
        
        # Get all concepts from this topic
        concepts = topic_data["concepts"] if topic_data else []
        
        # Get related concepts from other topics
        related_concepts = []
        for related in related_topics:
            related_topic_data = self.get_research_topic(related["topic"])
            if related_topic_data:
                related_concepts.extend(related_topic_data["concepts"])
        
        # Get recent sessions for context
        recent_sessions = []
        if topic_data:
            recent_sessions = sorted(
                topic_data["sessions"], 
                key=lambda x: x["created"], 
                reverse=True
            )[:3]  # Last 3 sessions
        
        return {
            "current_topic": topic,
            "topic_data": topic_data,
            "related_topics": related_topics,
            "concepts": list(set(concepts + related_concepts)),  # Remove duplicates
            "recent_sessions": recent_sessions,
            "total_research_topics": self.research_topics["statistics"]["total_topics"],
            "total_concepts": self.research_topics["statistics"]["total_concepts"]
        }
    
    def _hash_topic(self, topic: str) -> str:
        """Create a hash for a topic."""
        return hashlib.md5(topic.lower().encode()).hexdigest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get research statistics."""
        return self.research_topics["statistics"]
    
    def export_research_data(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Export research data for a specific topic or all topics."""
        if topic:
            topic_data = self.get_research_topic(topic)
            return {
                "topic": topic,
                "data": topic_data,
                "related_topics": self.get_related_topics(topic),
                "thinking_context": self.get_thinking_context(topic)
            }
        else:
            return self.research_topics


class KnowledgeBase:
    """Knowledge base for storing and retrieving research data."""
    
    def __init__(self):
        self.research_data = {}  # topic -> research_data
        self.url_cache = {}      # url_hash -> content_data
        self.concept_index = {}  # concept -> [topic, citation_id]
        self.visited_urls = set()  # Set of visited URLs
        self.research_sessions = {}  # session_id -> session_data
        
    def add_research_data(self, topic: str, research_data: Dict[str, Any]) -> None:
        """Add research data for a topic."""
        topic_hash = self._hash_topic(topic)
        self.research_data[topic_hash] = {
            'topic': topic,
            'data': research_data,
            'timestamp': datetime.now().isoformat(),
            'citations_count': len(research_data.get('citations', [])),
            'concepts': self._extract_concepts(research_data)
        }
        
        # Index concepts for quick lookup
        for concept in self._extract_concepts(research_data):
            if concept not in self.concept_index:
                self.concept_index[concept] = []
            self.concept_index[concept].append((topic_hash, research_data.get('session_id', '')))
    
    def get_research_data(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get research data for a topic."""
        topic_hash = self._hash_topic(topic)
        return self.research_data.get(topic_hash)
    
    def add_url_content(self, url: str, content_data: Dict[str, Any]) -> None:
        """Cache content from a URL."""
        url_hash = self._hash_url(url)
        self.url_cache[url_hash] = {
            'url': url,
            'content': content_data,
            'timestamp': datetime.now().isoformat()
        }
        self.visited_urls.add(url)
    
    def is_url_visited(self, url: str) -> bool:
        """Check if a URL has been visited."""
        return url in self.visited_urls
    
    def get_url_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for a URL."""
        url_hash = self._hash_url(url)
        return self.url_cache.get(url_hash)
    
    def search_concepts(self, concept: str) -> List[Dict[str, Any]]:
        """Search for research data containing a specific concept."""
        results = []
        if concept in self.concept_index:
            for topic_hash, session_id in self.concept_index[concept]:
                research_data = self.research_data.get(topic_hash)
                if research_data:
                    results.append({
                        'topic': research_data['topic'],
                        'session_id': session_id,
                        'concept': concept,
                        'timestamp': research_data['timestamp']
                    })
        return results
    
    def get_related_research(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get related research based on concept overlap."""
        topic_hash = self._hash_topic(topic)
        current_data = self.research_data.get(topic_hash)
        if not current_data:
            return []
        
        current_concepts = set(current_data['concepts'])
        related = []
        
        for other_hash, other_data in self.research_data.items():
            if other_hash == topic_hash:
                continue
            
            other_concepts = set(other_data['concepts'])
            overlap = len(current_concepts & other_concepts)
            
            if overlap > 0:
                related.append({
                    'topic': other_data['topic'],
                    'overlap_score': overlap / len(current_concepts),
                    'shared_concepts': list(current_concepts & other_concepts),
                    'timestamp': other_data['timestamp']
                })
        
        # Sort by overlap score and return top results
        related.sort(key=lambda x: x['overlap_score'], reverse=True)
        return related[:limit]
    
    def _hash_topic(self, topic: str) -> str:
        """Create a hash for a topic."""
        return hashlib.md5(topic.lower().encode()).hexdigest()
    
    def _hash_url(self, url: str) -> str:
        """Create a hash for a URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _extract_concepts(self, research_data: Dict[str, Any]) -> List[str]:
        """Extract concepts from research data."""
        concepts = []
        citations = research_data.get('citations', [])
        
        for citation in citations:
            if isinstance(citation, dict):
                key_concepts = citation.get('key_concepts', [])
                if isinstance(key_concepts, list):
                    concepts.extend(key_concepts)
        
        return list(set(concepts))  # Remove duplicates
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get a summary of the knowledge base."""
        return {
            'total_topics': len(self.research_data),
            'total_urls_visited': len(self.visited_urls),
            'total_concepts_indexed': len(self.concept_index),
            'total_sessions': len(self.research_sessions),
            'recent_topics': [
                {'topic': data['topic'], 'timestamp': data['timestamp']}
                for data in sorted(
                    self.research_data.values(),
                    key=lambda x: x['timestamp'],
                    reverse=True
                )[:5]
            ]
        }


class DeepResearchTracker:
    """Tracks all deep research tool calls in a JSON file for analysis and reuse."""
    
    def __init__(self, storage_file: str = "deep_research_history.json"):
        self.storage_file = Path(storage_file)
        self.research_history = self._load_research_history()
        
    def _load_research_history(self) -> Dict[str, Any]:
        """Load research history from JSON file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data.get('research_sessions', {}))} research sessions from {self.storage_file}")
                    return data
            except Exception as e:
                logger.error(f"Error loading research history: {e}")
                return self._create_default_structure()
        else:
            logger.info(f"Creating new research history file: {self.storage_file}")
            return self._create_default_structure()
    
    def _create_default_structure(self) -> Dict[str, Any]:
        """Create default JSON structure for research history."""
        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Deep research tool call history and analysis"
            },
            "research_sessions": {},
            "tool_calls": [],
            "topics_analyzed": {},
            "concepts_index": {},
            "relationships": [],
            "statistics": {
                "total_sessions": 0,
                "total_tool_calls": 0,
                "total_topics": 0,
                "total_concepts": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def _save_research_history(self) -> None:
        """Save research history to JSON file."""
        try:
            # Update statistics
            self.research_history["statistics"]["total_sessions"] = len(self.research_history["research_sessions"])
            self.research_history["statistics"]["total_tool_calls"] = len(self.research_history["tool_calls"])
            self.research_history["statistics"]["total_topics"] = len(self.research_history["topics_analyzed"])
            self.research_history["statistics"]["total_concepts"] = len(self.research_history["concepts_index"])
            self.research_history["statistics"]["last_updated"] = datetime.now().isoformat()
            
            # Ensure directory exists
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.research_history, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved research history to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving research history: {e}")
    
    def record_deep_research_call(self, topic: str, research_data: Dict[str, Any], 
                                 source_tool: str = "deep_research") -> str:
        """Record a deep research tool call."""
        session_id = f"dr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(topic.encode()).hexdigest()[:8]}"
        
        # Create session record
        session_record = {
            "session_id": session_id,
            "topic": topic,
            "source_tool": source_tool,
            "timestamp": datetime.now().isoformat(),
            "research_data": research_data,
            "citations_count": len(research_data.get('citations', [])),
            "concepts": self._extract_concepts_from_research(research_data),
            "source_breakdown": research_data.get('source_breakdown', {}),
            "content_metrics": research_data.get('content_metrics', {}),
            "analysis_summary": research_data.get('analysis', '')[:500] + "..." if len(research_data.get('analysis', '')) > 500 else research_data.get('analysis', '')
        }
        
        # Add to research sessions
        self.research_history["research_sessions"][session_id] = session_record
        
        # Add to tool calls
        tool_call_record = {
            "session_id": session_id,
            "topic": topic,
            "source_tool": source_tool,
            "timestamp": datetime.now().isoformat(),
            "success": research_data.get('success', False)
        }
        self.research_history["tool_calls"].append(tool_call_record)
        
        # Index by topic
        topic_hash = self._hash_topic(topic)
        if topic_hash not in self.research_history["topics_analyzed"]:
            self.research_history["topics_analyzed"][topic_hash] = {
                "topic": topic,
                "sessions": [],
                "total_citations": 0,
                "concepts": [],
                "last_researched": None
            }
        
        topic_data = self.research_history["topics_analyzed"][topic_hash]
        topic_data["sessions"].append(session_id)
        topic_data["total_citations"] += session_record["citations_count"]
        # Add new concepts to the list, avoiding duplicates
        existing_concepts = set(topic_data["concepts"])
        new_concepts = set(session_record["concepts"])
        topic_data["concepts"] = list(existing_concepts | new_concepts)
        topic_data["last_researched"] = datetime.now().isoformat()
        
        # Index concepts
        for concept in session_record["concepts"]:
            if concept not in self.research_history["concepts_index"]:
                self.research_history["concepts_index"][concept] = []
            if session_id not in self.research_history["concepts_index"][concept]:
                self.research_history["concepts_index"][concept].append(session_id)
        
        # Save to file
        self._save_research_history()
        
        logger.info(f"Recorded deep research call for topic '{topic}' with session ID: {session_id}")
        return session_id
    
    def get_research_context_for_topic(self, topic: str) -> Dict[str, Any]:
        """Get comprehensive research context for a topic."""
        topic_hash = self._hash_topic(topic)
        topic_data = self.research_history["topics_analyzed"].get(topic_hash, {})
        
        # Get all sessions for this topic
        sessions = []
        for session_id in topic_data.get("sessions", []):
            session_data = self.research_history["research_sessions"].get(session_id)
            if session_data:
                sessions.append(session_data)
        
        # Get related topics based on concept overlap
        related_topics = self._find_related_topics(set(topic_data.get("concepts", [])))
        
        # Get recent research trends
        recent_sessions = sorted(
            self.research_history["research_sessions"].values(),
            key=lambda x: x["timestamp"],
            reverse=True
        )[:5]
        
        return {
            "topic": topic,
            "topic_data": topic_data,
            "sessions": sessions,
            "related_topics": related_topics,
            "recent_research_trends": recent_sessions,
            "total_research_sessions": self.research_history["statistics"]["total_sessions"],
            "total_concepts_indexed": self.research_history["statistics"]["total_concepts"]
        }
    
    def get_thinking_context(self, topic: str) -> Dict[str, Any]:
        """Get comprehensive context for thinking process."""
        research_context = self.get_research_context_for_topic(topic)
        
        # Extract key insights from previous research
        insights = []
        for session in research_context["sessions"]:
            analysis = session.get("analysis_summary", "")
            if analysis:
                insights.append({
                    "session_id": session["session_id"],
                    "timestamp": session["timestamp"],
                    "insight": analysis[:200] + "..." if len(analysis) > 200 else analysis
                })
        
        # Get concept evolution
        concept_evolution = {}
        for session in research_context["sessions"]:
            concepts = session.get("concepts", [])
            for concept in concepts:
                if concept not in concept_evolution:
                    concept_evolution[concept] = []
                concept_evolution[concept].append({
                    "session_id": session["session_id"],
                    "timestamp": session["timestamp"]
                })
        
        return {
            "research_context": research_context,
            "insights": insights,
            "concept_evolution": concept_evolution,
            "research_gaps": self._identify_research_gaps(topic, research_context),
            "recommendations": self._generate_research_recommendations(topic, research_context)
        }
    
    def _extract_concepts_from_research(self, research_data: Dict[str, Any]) -> List[str]:
        """Extract concepts from research data."""
        concepts = []
        citations = research_data.get('citations', [])
        
        for citation in citations:
            if isinstance(citation, dict):
                key_concepts = citation.get('key_concepts', [])
                if isinstance(key_concepts, list):
                    concepts.extend(key_concepts)
            elif hasattr(citation, 'key_concepts'):
                concepts.extend(citation.key_concepts)
        
        return list(set(concepts))  # Remove duplicates
    
    def _find_related_topics(self, concepts: Set[str]) -> List[Dict[str, Any]]:
        """Find related topics based on concept overlap."""
        related = []
        
        for topic_hash, topic_data in self.research_history["topics_analyzed"].items():
            # Handle concepts whether they're stored as set or list
            topic_concepts_raw = topic_data.get("concepts", [])
            if isinstance(topic_concepts_raw, set):
                topic_concepts = topic_concepts_raw
            else:
                topic_concepts = set(topic_concepts_raw)
            
            overlap = len(concepts & topic_concepts)
            
            if overlap > 0:
                related.append({
                    "topic": topic_data["topic"],
                    "overlap_score": overlap / len(concepts) if concepts else 0,
                    "shared_concepts": list(concepts & topic_concepts),
                    "last_researched": topic_data.get("last_researched"),
                    "total_citations": topic_data.get("total_citations", 0)
                })
        
        # Sort by overlap score
        related.sort(key=lambda x: x['overlap_score'], reverse=True)
        return related[:5]  # Return top 5
    
    def _identify_research_gaps(self, topic: str, research_context: Dict[str, Any]) -> List[str]:
        """Identify research gaps based on previous research."""
        gaps = []
        sessions = research_context["sessions"]
        
        if not sessions:
            gaps.append("No previous research found - comprehensive initial research needed")
            return gaps
        
        # Analyze source coverage
        all_sources = set()
        for session in sessions:
            source_breakdown = session.get("source_breakdown", {})
            all_sources.update(source_breakdown.keys())
        
        if "wikipedia" not in all_sources:
            gaps.append("Missing Wikipedia coverage - need encyclopedia perspective")
        if "arxiv" not in all_sources:
            gaps.append("Missing arXiv coverage - need academic paper analysis")
        if "semantic_scholar" not in all_sources:
            gaps.append("Missing Semantic Scholar coverage - need citation analysis")
        
        # Analyze content quality
        low_quality_sessions = [s for s in sessions if s.get("citations_count", 0) < 3]
        if low_quality_sessions:
            gaps.append("Previous sessions had low citation counts - need deeper research")
        
        # Analyze concept coverage
        all_concepts = set()
        for session in sessions:
            all_concepts.update(session.get("concepts", []))
        
        if len(all_concepts) < 5:
            gaps.append("Limited concept coverage - need broader topic exploration")
        
        return gaps
    
    def _generate_research_recommendations(self, topic: str, research_context: Dict[str, Any]) -> List[str]:
        """Generate research recommendations based on previous work."""
        recommendations = []
        sessions = research_context["sessions"]
        
        if not sessions:
            recommendations.append("Start with comprehensive multi-source research")
            recommendations.append("Focus on recent developments and current state")
            recommendations.append("Include both academic and practical perspectives")
            return recommendations
        
        # Analyze recent trends
        recent_sessions = sorted(sessions, key=lambda x: x["timestamp"], reverse=True)[:3]
        if len(recent_sessions) >= 2:
            recommendations.append("Build on recent research findings and identify new directions")
        
        # Check for gaps
        gaps = self._identify_research_gaps(topic, research_context)
        for gap in gaps:
            recommendations.append(f"Address gap: {gap}")
        
        # Suggest new angles
        recommendations.append("Explore interdisciplinary connections and cross-domain applications")
        recommendations.append("Investigate emerging trends and future directions")
        
        return recommendations
    
    def _hash_topic(self, topic: str) -> str:
        """Create a hash for a topic."""
        return hashlib.md5(topic.lower().encode()).hexdigest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get research history statistics."""
        return self.research_history["statistics"]
    
    def export_research_history(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Export research history for a specific topic or all topics."""
        if topic:
            return self.get_research_context_for_topic(topic)
        else:
            return self.research_history


class ResearchersWetDreamEngine:
    """Advanced research engine that combines deep research with thinking for autonomous iteration."""
    
    def __init__(self):
        self.research_sessions = {}
        self.session_counter = 0
        self.max_iterations = 10
        self.max_thinking_steps = 20
        
        # Global visited URLs and paper IDs to avoid duplicate requests across sessions
        self.global_visited_urls = set()
        self.global_visited_paper_ids = set()
        
        # Initialize research topic manager
        self.topic_manager = ResearchTopicManager("research_topics.json")
        
        # Initialize deep research tracker
        self.deep_research_tracker = DeepResearchTracker("deep_research_history.json")
        
        # Microsoft-style Knowledge Graph Structure
        self.knowledge_graph = {
            "entities": {},  # entity_id -> entity_data
            "relationships": {},  # relationship_id -> relationship_data
            "triples": [],  # List of (head_entity, relation, tail_entity, confidence, timestamp)
            "semantic_embeddings": {},  # entity_id -> embedding vector
            "temporal_contexts": {},  # entity_id -> temporal information
            "provenance_tracking": {},  # triple_id -> source information
            "confidence_scores": {},  # triple_id -> confidence score
            "concept_hierarchy": {},  # concept -> subconcepts
            "cross_references": {},  # entity_id -> related entities
            "metadata": {
                "total_entities": 0,
                "total_relationships": 0,
                "total_triples": 0,
                "avg_confidence": 0.0,
                "temporal_span": None,
                "source_coverage": {}
            }
        }
        
        # Entity and relationship counters
        self.entity_counter = 0
        self.relationship_counter = 0
        self.triple_counter = 0
        
        self.knowledge_base = KnowledgeBase()
        self.visited_urls: Set[str] = set()
        self.current_session_id = None
        self.session_data = {}
        
    def _get_source_breakdown(self) -> Dict[str, int]:
        """Get breakdown of sources by type."""
        breakdown = {}
        citations = self.session_data.get('citations', [])
        for citation in citations:
            source = citation.get('source', 'unknown')
            breakdown[source] = breakdown.get(source, 0) + 1
        return breakdown
    
    def _calculate_content_metrics(self) -> Dict[str, Any]:
        """Calculate content quality metrics for all citations."""
        citations = self.session_data.get('citations', [])
        total_citations = len(citations)
        
        if total_citations == 0:
            return {
                "total_citations": 0,
                "sources_with_abstracts": 0,
                "sources_with_full_content": 0,
                "abstract_coverage": 0.0,
                "full_content_coverage": 0.0,
                "average_abstract_length": 0,
                "average_content_length": 0,
                "total_content_length": 0,
                "total_abstract_length": 0,
                "avg_content_per_source": 0,
                "avg_abstract_per_source": 0,
                "citation_coverage": 0.0,
                "total_citations": 0,
                "avg_citation_count": 0.0
            }
        
        sources_with_abstracts = 0
        sources_with_full_content = 0
        total_abstract_length = 0
        total_content_length = 0
        total_citation_count = 0
        
        for citation in citations:
            # Check for abstracts (non-empty abstract field)
            if citation.get('abstract') and len(citation.get('abstract', '').strip()) > 10:
                sources_with_abstracts += 1
                total_abstract_length += len(citation.get('abstract', ''))
            
            # Check for full content (non-empty full_content field)
            if citation.get('full_content') and len(citation.get('full_content', '').strip()) > 100:
                sources_with_full_content += 1
                total_content_length += len(citation.get('full_content', ''))
            
            # Count citations
            citation_count = citation.get('citation_count', 0)
            total_citation_count += citation_count
        
        return {
            "total_citations": total_citations,
            "sources_with_abstracts": sources_with_abstracts,
            "sources_with_full_content": sources_with_full_content,
            "abstract_coverage": sources_with_abstracts / total_citations if total_citations > 0 else 0.0,
            "full_content_coverage": sources_with_full_content / total_citations if total_citations > 0 else 0.0,
            "average_abstract_length": total_abstract_length // sources_with_abstracts if sources_with_abstracts > 0 else 0,
            "average_content_length": total_content_length // sources_with_full_content if sources_with_full_content > 0 else 0,
            "total_content_length": total_content_length,
            "total_abstract_length": total_abstract_length,
            "avg_content_per_source": total_content_length / total_citations if total_citations > 0 else 0,
            "avg_abstract_per_source": total_abstract_length / total_citations if total_citations > 0 else 0,
            "citation_coverage": sources_with_abstracts / total_citations if total_citations > 0 else 0.0,
            "avg_citation_count": total_citation_count / total_citations if total_citations > 0 else 0.0
        }
    
    async def _conduct_thinking_session(self, thinking_engine, research_result: Dict[str, Any], 
                                      topic: str, thinking_depth: int, iteration_count: int) -> Dict[str, Any]:
        """Conduct a thinking session with research context."""
        logger.info(f"Starting thinking session for iteration {iteration_count}")
        
        # Get thinking context from deep research tracker
        thinking_context = self.deep_research_tracker.get_thinking_context(topic)
        
        # Prepare research summary for thinking
        citations = research_result.get('citations', [])
        source_breakdown = research_result.get('source_breakdown', {})
        content_metrics = research_result.get('content_metrics', {})
        
        # Create thinking prompt with comprehensive research context
        thinking_prompt = f"""
**CRITICAL RESEARCH ANALYSIS FOR THINKING SESSION**

**Current Topic:** {topic}
**Iteration:** {iteration_count}
**Total Sources Found:** {len(citations)}

**Research Summary:**
- Sources by type: {', '.join([f'{k}: {v}' for k, v in source_breakdown.items()])}
- Sources with abstracts: {content_metrics.get('sources_with_abstracts', 0)}/{len(citations)}
- Sources with full content: {content_metrics.get('sources_with_full_content', 0)}/{len(citations)}
- Average citation count: {content_metrics.get('avg_citation_count', 0):.1f}

**Deep Research History Context:**
- Total research sessions in history: {thinking_context['research_context']['total_research_sessions']}
- Total concepts indexed: {thinking_context['research_context']['total_concepts_indexed']}
- Previous sessions for this topic: {len(thinking_context['research_context']['sessions'])}
- Related topics found: {len(thinking_context['research_context']['related_topics'])}
- Recent research trends: {len(thinking_context['research_context']['recent_research_trends'])}

**Previous Research Insights:**
{chr(10).join([f"- {insight['insight']}" for insight in thinking_context['insights'][:3]])}

**Research Gaps Identified:**
{chr(10).join([f"- {gap}" for gap in thinking_context['research_gaps']])}

**Research Recommendations:**
{chr(10).join([f"- {rec}" for rec in thinking_context['recommendations']])}

**Key Concepts from Current Research:**
{', '.join(list(thinking_context['research_context']['topic_data'].get('concepts', set()))[:10])}

**Related Topics:**
{chr(10).join([f"- {rt['topic']} (overlap: {rt['overlap_score']:.2f})" for rt in thinking_context['research_context']['related_topics'][:3]])}

**CRITICAL THINKING TASK:**
Conduct a comprehensive critical analysis of the research findings. Focus on:

1. **CRITICAL ISSUES & PROBLEMS:**
   - What fundamental problems exist in current understanding?
   - What methodological flaws are present in the research?
   - What assumptions are being made that could be wrong?
   - What contradictions or conflicts exist in the literature?

2. **LOOPHOLES & WEAKNESSES:**
   - What gaps in logic or reasoning exist?
   - What evidence is missing or insufficient?
   - What alternative explanations are being ignored?
   - What biases or limitations are present?

3. **RESEARCH GAPS & MISSING PIECES:**
   - What questions remain unanswered?
   - What areas are under-researched or overlooked?
   - What connections between fields are missing?
   - What future research directions are needed?

4. **CONTROVERSIES & DEBATES:**
   - What are the main points of contention?
   - What competing theories or viewpoints exist?
   - What evidence supports or contradicts different positions?
   - What are the implications of these disagreements?

5. **PRACTICAL IMPLICATIONS:**
   - What are the real-world consequences of these findings?
   - What risks or dangers might be involved?
   - What opportunities or benefits could arise?
   - What policy or practical changes might be needed?

6. **FUTURE DIRECTIONS & RECOMMENDATIONS:**
   - What should be the next steps in research?
   - What new methodologies or approaches are needed?
   - What interdisciplinary connections should be explored?
   - What critical questions should be prioritized?

Provide structured, critical thinking with clear reasoning, identify specific issues and loopholes, and offer actionable insights for advancing understanding of this topic.
"""
        
        # Conduct thinking process
        thinking_steps = []
        current_thought = 1
        
        while current_thought <= thinking_depth:
            # Create thinking data
            thinking_data = {
                "thought": f"Analyzing research iteration {iteration_count} for topic '{topic}' with historical context",
                "nextThoughtNeeded": current_thought < thinking_depth,
                "thoughtNumber": current_thought,
                "totalThoughts": thinking_depth,
                "isHypothesis": current_thought == thinking_depth - 1,  # Second to last thought
                "isVerification": current_thought == thinking_depth,    # Last thought
                "returnFullHistory": True
            }
            
            # Process thought
            try:
                result = thinking_engine.process_thought(thinking_data)
                thinking_steps.append(result)
                
                # Extract next thinking direction from the thought
                if current_thought < thinking_depth:
                    # Generate next thought based on current analysis and historical context
                    next_thought = self._generate_next_thought_with_history(
                        thinking_data, research_result, thinking_context, current_thought
                    )
                    thinking_data["thought"] = next_thought
                
                current_thought += 1
                
            except Exception as e:
                logger.error(f"Error in thinking step {current_thought}: {e}")
                break
        
        return {
            "thinking_steps": thinking_steps,
            "total_steps": len(thinking_steps),
            "context_used": thinking_context,
            "research_integration": True,
            "historical_context_integrated": True
        }
    
    def _generate_next_thought_with_history(self, current_thought_data: Dict[str, Any], 
                                          research_result: Dict[str, Any], 
                                          thinking_context: Dict[str, Any], 
                                          step_number: int) -> str:
        """Generate the next thought based on current analysis and historical context."""
        citations = research_result.get('citations', [])
        content_metrics = research_result.get('content_metrics', {})
        insights = thinking_context.get('insights', [])
        gaps = thinking_context.get('research_gaps', [])
        
        # Extract topic from thinking context
        topic = thinking_context.get('research_context', {}).get('topic', 'the research topic')
        
        if step_number == 1:
            return f"CRITICAL ANALYSIS INITIATION: Examining {len(citations)} sources for topic '{topic}'. Content quality assessment: {content_metrics.get('abstract_coverage', 0):.1%} have abstracts, {content_metrics.get('full_content_coverage', 0):.1%} have full content. Historical context reveals {len(insights)} previous insights and {len(gaps)} identified gaps. Beginning systematic identification of issues, loopholes, and critical problems."
        
        elif step_number == 2:
            return f"ISSUE IDENTIFICATION PHASE: Analyzing source diversity across {len(set(c.get('source', 'unknown') for c in citations))} different source types. Examining methodological flaws, contradictory findings, and fundamental assumptions that may be problematic. Historical gaps analysis shows {len(gaps)} areas requiring critical attention. Identifying specific loopholes in current research approaches."
        
        elif step_number == 3:
            return f"LOOPHOLE ANALYSIS: Investigating {len(thinking_context['research_context']['related_topics'])} related topics for cross-field insights and missing connections. Examining evidence gaps, alternative explanations being ignored, and potential biases in current research. Building comprehensive understanding of controversies and competing viewpoints."
        
        elif step_number == 4:
            return f"CONTROVERSY MAPPING: Identifying specific contradictions and conflicts in current findings compared to historical research patterns. Analyzing competing theories, methodological disagreements, and evidence that supports or contradicts different positions. Examining practical implications and real-world consequences."
        
        elif step_number == 5:
            return f"HYPOTHESIS GENERATION & CRITICAL RECOMMENDATIONS: Synthesizing findings to generate critical hypotheses for further investigation. Identifying specific research directions that address the most pressing issues and loopholes. Formulating actionable recommendations for advancing understanding and addressing identified problems."
        
        else:
            return f"FINAL CRITICAL SYNTHESIS: Verifying findings and determining next research directions with full historical context integration. Prioritizing critical questions, identifying interdisciplinary connections, and formulating comprehensive recommendations for addressing the most significant issues and loopholes identified in the research."
    
    def _generate_next_thought(self, current_thought_data: Dict[str, Any], 
                             research_result: Dict[str, Any], 
                             thinking_context: Dict[str, Any], 
                             step_number: int) -> str:
        """Generate the next thought based on current analysis."""
        citations = research_result.get('citations', [])
        content_metrics = research_result.get('content_metrics', {})
        
        if step_number == 1:
            return f"Initial analysis of {len(citations)} sources found. Content quality: {content_metrics.get('abstract_coverage', 0):.1%} have abstracts, {content_metrics.get('full_content_coverage', 0):.1%} have full content."
        
        elif step_number == 2:
            return f"Examining source diversity and coverage. Found {len(set(c.get('source', 'unknown') for c in citations))} different source types."
        
        elif step_number == 3:
            return f"Analyzing concept overlap with {len(thinking_context.get('related_topics', []))} related topics in research database."
        
        elif step_number == 4:
            return f"Identifying research gaps and contradictions in current findings."
        
        elif step_number == 5:
            return f"Generating hypotheses for further investigation based on analysis."
        
        else:
            return f"Verifying findings and determining next research directions."
    
    def _generate_research_directions(self, research_result: Dict[str, Any], 
                                    current_topic: str, 
                                    citations: List[Dict[str, Any]]) -> List[str]:
        """Generate new research directions based on current findings."""
        directions = []
        
        # Extract concepts from citations
        all_concepts = []
        for citation in citations:
            concepts = citation.get('key_concepts', [])
            if isinstance(concepts, list):
                all_concepts.extend(concepts)
        
        # Find most common concepts
        concept_counts = {}
        for concept in all_concepts:
            concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        # Get top concepts (filter out common words and short concepts)
        filtered_concepts = []
        for concept, count in concept_counts.items():
            if (concept and len(concept) > 3 and 
                concept.lower() not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'been', 'they', 'their'] and
                not concept.isdigit()):
                filtered_concepts.append((concept, count))
        
        # Sort by frequency and get top concepts
        top_concepts = sorted(filtered_concepts, key=lambda x: x[1], reverse=True)[:5]
        
        # Generate research directions based on concepts
        for concept, count in top_concepts:
            if concept and len(concept) > 3:  # Filter out short concepts
                # Create specific research directions
                directions.append(f"Recent developments in {concept}")
                directions.append(f"{concept} limitations and challenges")
                directions.append(f"Future applications of {concept}")
        
        # Add cross-topic directions
        related_topics = self.topic_manager.get_related_topics(current_topic)
        for related in related_topics[:2]:  # Limit to 2 related topics
            directions.append(f"Comparison between {current_topic} and {related['topic']}")
        
        # Add gap analysis directions
        content_metrics = research_result.get('content_metrics', {})
        if content_metrics.get('abstract_coverage', 0) < 0.8:
            directions.append(f"Comprehensive literature review for {current_topic}")
        
        if content_metrics.get('avg_citation_count', 0) < 10:
            directions.append(f"Highly cited research in {current_topic}")
        
        # Add specific LLM-related directions if the topic is about LLMs
        if 'llm' in current_topic.lower() or 'language model' in current_topic.lower():
            directions.extend([
                "LLM reasoning capabilities and limitations",
                "Novelty generation in large language models",
                "Cognitive architecture of language models",
                "LLM consciousness and self-awareness",
                "Ethical implications of LLM thinking"
            ])
        
        # Clean and deduplicate directions
        cleaned_directions = []
        seen_directions = set()
        
        for direction in directions:
            # Clean the direction
            direction = direction.strip()
            if (direction and 
                len(direction) > 10 and 
                len(direction) < 100 and  # Prevent overly long directions
                direction not in seen_directions and
                not direction.startswith("page applications") and  # Filter out corrupted directions
                not "page applications" in direction):  # Additional filter
                
                seen_directions.add(direction)
                cleaned_directions.append(direction)
        
        # Return top 5 unique, clean directions
        return cleaned_directions[:5]
    
    async def conduct_research_session(self, topic: str, research_depth: int = 3, 
                                     thinking_depth: int = 5, auto_iterate: bool = True, 
                                     max_iterations: int = 10) -> Dict[str, Any]:
        """Conduct a comprehensive research session with knowledge base integration."""
        
        # Create session ID
        self.current_session_id = self._create_session_id(topic)
        logger.info(f"Starting research session {self.current_session_id} for topic: {topic}")
        
        # Check if we have existing research for this topic using topic manager
        existing_research = self.topic_manager.get_research_topic(topic)
        if existing_research:
            logger.info(f"Found existing research for topic: {topic}")
            # Use existing research as starting point
            session_data = {
                'session_id': self.current_session_id,
                'topic': topic,
                'start_time': datetime.now().isoformat(),
                'iterations': [],
                'total_sources': existing_research['summary']['total_citations'],
                'knowledge_graph': {
                    'entities': [],
                    'relationships': [],
                    'triples': []
                },
                'citations': [],
                'concepts': existing_research['concepts'],
                'research_directions': [],
                'thinking_process': [],
                'reused_existing': True
            }
            
            # Add citations from previous sessions
            for session in existing_research['sessions']:
                session_data['citations'].extend(session.get('citations', []))
        else:
            # Initialize new session
            session_data = {
                'session_id': self.current_session_id,
                'topic': topic,
                'start_time': datetime.now().isoformat(),
                'iterations': [],
                'total_sources': 0,
                'knowledge_graph': {
                    'entities': [],
                    'relationships': [],
                    'triples': []
                },
                'citations': [],
                'concepts': [],
                'research_directions': [],
                'thinking_process': [],
                'reused_existing': False
            }
        
        # Get related research from topic manager
        related_research = self.topic_manager.get_related_topics(topic)
        if related_research:
            session_data['related_research'] = related_research
            logger.info(f"Found {len(related_research)} related research topics")
        
        # Initialize thinking engine
        from ..services.thinking_tool_service import ThinkingToolEngine
        thinking_engine = ThinkingToolEngine()
        
        # Conduct research iterations with proper loop control
        iteration_count = 0
        original_topic = topic
        consecutive_no_new_directions = 0
        max_consecutive_no_directions = 3  # Stop after 3 consecutive iterations without new directions
        
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"Starting iteration {iteration_count}/{max_iterations} for topic: {topic}")
            
            # Check if we need to search for new information
            need_new_research = self._should_search_new_info(session_data, iteration_count)
            
            if need_new_research:
                # Conduct new research with visited URL tracking
                research_result = await self._conduct_research_with_tracking(topic, research_depth)
                
                logger.info(f"Research result keys: {list(research_result.keys())}")
                logger.info(f"Research result citations count: {len(research_result.get('citations', []))}")
                logger.info(f"Research result success: {research_result.get('success', False)}")
                
                # Process and integrate new research
                processed_citations = self._process_new_citations(research_result.get('citations', []))
                logger.info(f"Processed citations count: {len(processed_citations)}")
                
                session_data['citations'].extend(processed_citations)
                session_data['total_sources'] += len(processed_citations)
                
                # Update session_data for metrics calculations
                self.session_data = session_data
                
                # Update knowledge graph
                for citation in processed_citations:
                    self._add_to_knowledge_graph(citation)
                
                # Extract concepts
                new_concepts = self._extract_concepts_from_citations(processed_citations)
                session_data['concepts'].extend(new_concepts)
                session_data['concepts'] = list(set(session_data['concepts']))  # Remove duplicates
                
                logger.info(f"Session data citations count: {len(session_data['citations'])}")
                logger.info(f"Session data concepts count: {len(session_data['concepts'])}")
            else:
                # Use existing knowledge for thinking
                logger.info("Using existing knowledge for thinking process")
                # Update session_data for metrics calculations
                self.session_data = session_data
                research_result = {
                    'citations': session_data['citations'],
                    'source_breakdown': self._get_source_breakdown(),
                    'content_metrics': self._calculate_content_metrics()
                }
            
            # Conduct thinking process with research topic context
            thinking_result = await self._conduct_thinking_session(
                thinking_engine, research_result, topic, thinking_depth, iteration_count
            )
            
            # Record iteration
            iteration_data = {
                'iteration_number': iteration_count,
                'research_result': research_result,
                'thinking_result': thinking_result,
                'timestamp': datetime.now().isoformat()
            }
            session_data['iterations'].append(iteration_data)
            
            # Generate new research directions if auto-iterating and not at max iterations
            if auto_iterate and iteration_count < max_iterations:
                new_directions = self._generate_research_directions(
                    research_result, topic, session_data['citations']
                )
                
                # Filter out corrupted or repetitive directions
                clean_directions = []
                for direction in new_directions:
                    if (direction and 
                        len(direction) < 100 and 
                        not direction.startswith("page applications") and
                        not "page applications" in direction and
                        not self._is_repetitive_direction(direction, session_data)):
                        clean_directions.append(direction)
                
                if clean_directions:
                    # Use the first clean direction
                    new_topic = clean_directions[0]
                    session_data['research_directions'].append(new_topic)
                    topic = new_topic  # Update topic for next iteration
                    consecutive_no_new_directions = 0  # Reset counter
                    logger.info(f"Moving to new research direction: {topic}")
                else:
                    consecutive_no_new_directions += 1
                    logger.info(f"No new research directions found (consecutive: {consecutive_no_new_directions})")
                    
                    # Stop if we've had too many consecutive iterations without new directions
                    if consecutive_no_new_directions >= max_consecutive_no_directions:
                        logger.info(f"Stopping after {consecutive_no_new_directions} consecutive iterations without new directions")
                        break
                    
                    # Try to use a different approach or return to original topic
                    if consecutive_no_new_directions == 1:
                        # Try related topics
                        related_topics = self.topic_manager.get_related_topics(original_topic)
                        if related_topics:
                            topic = related_topics[0]['topic']
                            logger.info(f"Trying related topic: {topic}")
                        else:
                            # Return to original topic with different focus
                            topic = f"Advanced analysis of {original_topic}"
                            logger.info(f"Returning to original topic with advanced focus: {topic}")
                    else:
                        # Just continue with current topic for thinking
                        logger.info("Continuing with current topic for deeper thinking")
            else:
                # Not auto-iterating or reached max iterations
                logger.info(f"Stopping: auto_iterate={auto_iterate}, iteration_count={iteration_count}, max_iterations={max_iterations}")
                break
        
        # Finalize session
        session_data['end_time'] = datetime.now().isoformat()
        session_data['total_iterations'] = iteration_count
        
        # Update knowledge graph summary
        kg_summary = self._get_knowledge_graph_summary()
        session_data['knowledge_graph'].update(kg_summary)
        
        # Save to research topic manager (JSON file)
        self.topic_manager.add_research_topic(topic, session_data)
        
        # Generate final analysis
        final_analysis = await self._generate_final_analysis(session_data)
        session_data['final_analysis'] = final_analysis
        
        # Add success status
        session_data['status'] = 'completed'
        
        logger.info(f"Research session {self.current_session_id} completed with {iteration_count} iterations")
        
        return session_data
    
    def _should_search_new_info(self, session_data: Dict[str, Any], iteration_count: int) -> bool:
        """Determine if we need to search for new information."""
        # Always search on first iteration
        if iteration_count == 1:
            return True
        
        # Check if we have enough content
        citations = session_data.get('citations', [])
        if len(citations) < 5:
            return True
        
        # Check content quality
        abstracts_found = sum(1 for c in citations if c.get('abstract') and len(c.get('abstract', '')) > 50)
        if abstracts_found < len(citations) * 0.7:  # Less than 70% have abstracts
            return True
        
        # Check if we have recent research
        recent_iterations = session_data.get('iterations', [])[-3:]  # Last 3 iterations
        if not recent_iterations:
            return True
        
        # If we have good content and recent research, focus on thinking
        return False
    
    async def _conduct_research_with_tracking(self, topic: str, research_depth: int) -> Dict[str, Any]:
        """Conduct research with visited URL tracking and record in deep research tracker."""
        from ..tools.deep_research import UnifiedDeepResearchEngine
        
        # Initialize research engine
        research_engine = UnifiedDeepResearchEngine(max_depth=research_depth, max_refs_per_source=3)
        
        # Override the search methods to use visited URL tracking
        original_search_methods = {
            'wikipedia': research_engine._search_wikipedia,
            'arxiv': research_engine._search_arxiv,
            'semantic_scholar': research_engine._search_semantic_scholar,
            'openalex': research_engine._search_openalex,
            'pubmed': research_engine._search_pubmed
        }
        
        # Create tracked search methods
        async def tracked_search_wikipedia(query: str):
            citations = await original_search_methods['wikipedia'](query)
            return self._filter_visited_citations(citations)
        
        async def tracked_search_arxiv(query: str):
            citations = await original_search_methods['arxiv'](query)
            return self._filter_visited_citations(citations)
        
        async def tracked_search_semantic_scholar(query: str):
            citations = await original_search_methods['semantic_scholar'](query)
            return self._filter_visited_citations(citations)
        
        async def tracked_search_openalex(query: str):
            citations = await original_search_methods['openalex'](query)
            return self._filter_visited_citations(citations)
        
        async def tracked_search_pubmed(query: str):
            citations = await original_search_methods['pubmed'](query)
            return self._filter_visited_citations(citations)
        
        # Replace methods temporarily
        research_engine._search_wikipedia = tracked_search_wikipedia
        research_engine._search_arxiv = tracked_search_arxiv
        research_engine._search_semantic_scholar = tracked_search_semantic_scholar
        research_engine._search_openalex = tracked_search_openalex
        research_engine._search_pubmed = tracked_search_pubmed
        
        # Conduct research
        result = await research_engine.unified_deep_research(topic)
        
        # Record the deep research call in the tracker
        session_id = self.deep_research_tracker.record_deep_research_call(
            topic=topic,
            research_data=result,
            source_tool="researchers_wet_dream"
        )
        
        logger.info(f"Recorded deep research call with session ID: {session_id}")
        
        # Mark URLs as visited
        citations = result.get('citations', [])
        for citation in citations:
            if isinstance(citation, dict) and citation.get('url'):
                self._mark_url_visited(citation['url'])
        
        return result
    
    def _filter_visited_citations(self, citations: List[Any]) -> List[Any]:
        """Filter out citations from already visited URLs."""
        filtered = []
        for citation in citations:
            if isinstance(citation, dict) and citation.get('url'):
                if not self._is_url_visited(citation['url']):
                    filtered.append(citation)
            else:
                filtered.append(citation)
        return filtered
    
    def _process_new_citations(self, citations: List[Any]) -> List[Dict[str, Any]]:
        """Process new citations and cache their content."""
        processed = []
        for citation in citations:
            if isinstance(citation, dict):
                # Cache content if available
                if citation.get('abstract'):
                    self._cache_content(citation['url'], {
                        'abstract': citation['abstract'],
                        'title': citation.get('title', ''),
                        'source': citation.get('source', '')
                    })
                
                if citation.get('full_content'):
                    self._cache_content(citation['url'], {
                        'full_content': citation['full_content'],
                        'title': citation.get('title', ''),
                        'source': citation.get('source', '')
                    })
                
                processed.append(citation)
        return processed
    
    def _extract_concepts_from_citations(self, citations: List[Dict[str, Any]]) -> List[str]:
        """Extract concepts from citations."""
        concepts = []
        for citation in citations:
            key_concepts = citation.get('key_concepts', [])
            if isinstance(key_concepts, list):
                concepts.extend(key_concepts)
        return list(set(concepts))  # Remove duplicates
    
    def _is_repetitive_direction(self, direction: str, session_data: Dict[str, Any]) -> bool:
        """Check if a research direction is repetitive."""
        existing_directions = session_data.get('research_directions', [])
        return direction in existing_directions
    
    def _create_session_id(self, topic: str) -> str:
        """Create a unique session ID for research."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
        return f"rwd_{timestamp}_{topic_hash}"
    
    def _get_existing_research(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get existing research data for a topic."""
        return self.knowledge_base.get_research_data(topic)
    
    def _get_related_research(self, topic: str) -> List[Dict[str, Any]]:
        """Get related research from knowledge base."""
        return self.knowledge_base.get_related_research(topic)
    
    def _save_research_data(self, topic: str, research_data: Dict[str, Any]) -> None:
        """Save research data to knowledge base."""
        research_data['session_id'] = self.current_session_id
        self.knowledge_base.add_research_data(topic, research_data)
    
    def _mark_url_visited(self, url: str) -> None:
        """Mark URL as visited."""
        self.visited_urls.add(url)
    
    def _is_url_visited(self, url: str) -> bool:
        """Check if URL has been visited in current session or knowledge base."""
        return url in self.visited_urls or self.knowledge_base.is_url_visited(url)
    
    def _cache_content(self, url: str, content_data: Dict[str, Any]) -> None:
        """Cache content from a URL."""
        self.knowledge_base.add_url_content(url, content_data)
    
    async def _fetch_and_cache_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch content from URL and cache it."""
        # Check if already cached
        cached_content = self.knowledge_base.get_url_content(url)
        if cached_content:
            return cached_content['content']
        
        try:
            # Use content fetcher to get content
            from ..services.content_fetcher import ContentFetcher
            fetcher = ContentFetcher()
            
            content, prefix = await fetcher.fetch_url(url)
            
            # Cache the content
            content_data = {
                'content': content,
                'prefix': prefix,
                'url': url,
                'fetched_at': datetime.now().isoformat()
            }
            
            self.knowledge_base.add_url_content(url, content_data)
            return content_data
            
        except Exception as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return None
    
    async def _enhance_citation_with_content(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance citation with fetched content if not already present."""
        if not citation.get('abstract') or not citation.get('full_content'):
            url = citation.get('url')
            if url:
                content_data = await self._fetch_and_cache_content(url)
                if content_data:
                    if not citation.get('abstract') and content_data.get('content'):
                        # Extract abstract from content
                        content = content_data['content']
                        # Take first few paragraphs as abstract
                        paragraphs = content.split('\n\n')
                        abstract = '\n\n'.join(paragraphs[:2])[:500]  # Limit to 500 chars
                        citation['abstract'] = abstract
                    
                    if not citation.get('full_content') and content_data.get('content'):
                        citation['full_content'] = content_data['content']
        
        return citation
    
    async def _generate_final_analysis(self, session_data: Dict[str, Any]) -> str:
        """Generate comprehensive final analysis of the research session with critical insights."""
        topic = session_data.get('topic', 'Unknown Topic')
        total_iterations = session_data.get('total_iterations', 0)
        total_sources = session_data.get('total_sources', 0)
        citations = session_data.get('citations', [])
        
        # Calculate content metrics
        abstracts_found = sum(1 for c in citations if c.get('abstract') and len(c.get('abstract', '')) > 50)
        full_content_found = sum(1 for c in citations if c.get('full_content') and len(c.get('full_content', '')) > 100)
        
        # Extract unique concepts
        all_concepts = []
        for citation in citations:
            concepts = citation.get('key_concepts', [])
            if isinstance(concepts, list):
                all_concepts.extend(concepts)
        unique_concepts = list(set(all_concepts))
        
        # Get knowledge graph summary
        kg_summary = session_data.get('knowledge_graph', {})
        
        # Get related research
        related_research = session_data.get('related_research', [])
        
        # Analyze critical issues and gaps
        critical_issues = self._identify_critical_issues(citations, session_data)
        research_gaps = self._identify_research_gaps(citations, session_data)
        controversies = self._identify_controversies(citations, session_data)
        practical_implications = self._analyze_practical_implications(citations, session_data)
        
        analysis = f"""
🎯 **RESEARCHER'S WET DREAM - CRITICAL ANALYSIS REPORT**

📊 **Session Overview:**
• **Topic:** {topic}
• **Total Iterations:** {total_iterations}
• **Total Sources Analyzed:** {total_sources}
• **Unique Concepts Identified:** {len(unique_concepts)}
• **Knowledge Graph Entities/Relationships/Triples:** {kg_summary.get('total_entities', 0)}/{kg_summary.get('total_relationships', 0)}/{kg_summary.get('total_triples', 0)}

📝 **Content Quality Analysis:**
• **Sources with Abstracts:** {abstracts_found}/{total_sources} ({(abstracts_found/total_sources*100) if total_sources > 0 else 0:.1f}%)
• **Sources with Full Content:** {full_content_found}/{total_sources} ({(full_content_found/total_sources*100) if total_sources > 0 else 0:.1f}%)
• **Average Confidence:** {kg_summary.get('avg_confidence', 0):.3f}
• **Semantic Richness:** {kg_summary.get('semantic_richness', 0):.3f}
• **Knowledge Coverage:** {', '.join([f'{k}: {v:.1%}' for k, v in kg_summary.get('knowledge_coverage', {}).items()])}

🔗 **RELATIONSHIP TYPES FOUND:**
"""
        
        relationship_types = kg_summary.get('relationship_diversity', {})
        for rel_type, count in relationship_types.items():
            analysis += f"• {rel_type}: {count} instances\n"
        
        if related_research:
            analysis += f"\n📚 **Related Research Found:**\n"
            for related in related_research[:3]:  # Show top 3
                analysis += f"• {related['topic']} (overlap: {related['overlap_score']:.2f})\n"
        
        if unique_concepts:
            analysis += f"\n🧠 **Key Concepts Identified:**\n"
            for concept in unique_concepts[:15]:  # Show top 15
                analysis += f"• {concept}\n"
        
        # Add critical analysis sections
        analysis += f"""

🚨 **CRITICAL ISSUES & PROBLEMS IDENTIFIED:**
"""
        for i, issue in enumerate(critical_issues, 1):
            analysis += f"{i}. {issue}\n"
        
        analysis += f"""

🔍 **RESEARCH GAPS & MISSING PIECES:**
"""
        for i, gap in enumerate(research_gaps, 1):
            analysis += f"{i}. {gap}\n"
        
        analysis += f"""

⚔️ **CONTROVERSIES & DEBATES:**
"""
        for i, controversy in enumerate(controversies, 1):
            analysis += f"{i}. {controversy}\n"
        
        analysis += f"""

💡 **PRACTICAL IMPLICATIONS:**
"""
        for i, implication in enumerate(practical_implications, 1):
            analysis += f"{i}. {implication}\n"
        
        analysis += f"""

🎯 **CRITICAL RECOMMENDATIONS:**
"""
        recommendations = self._generate_critical_recommendations(citations, session_data, critical_issues, research_gaps)
        for i, rec in enumerate(recommendations, 1):
            analysis += f"{i}. {rec}\n"
        
        analysis += f"""

⚠️ **LOOPHOLES & WEAKNESSES:**
"""
        loopholes = self._identify_loopholes(citations, session_data)
        for i, loophole in enumerate(loopholes, 1):
            analysis += f"{i}. {loophole}\n"
        
        # Add comprehensive research content for LLM analysis
        analysis += f"""

📚 **COMPLETE RESEARCH CONTENT FOR LLM ANALYSIS:**
"""
        
        # Group citations by source type for better organization
        source_groups = {}
        for citation in citations:
            source = citation.get('source', 'unknown')
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(citation)
        
        # Display detailed content for each source type
        for source_type, source_citations in source_groups.items():
            analysis += f"\n**{source_type.upper()} SOURCES ({len(source_citations)}):**\n"
            
            for i, citation in enumerate(source_citations, 1):
                analysis += f"\n**SOURCE {i}: {citation.get('title', 'No Title')}**\n"
                analysis += f"**Source Type:** {citation.get('source', 'Unknown')}\n"
                analysis += f"**URL:** {citation.get('url', 'No URL')}\n"
                analysis += f"**Date:** {citation.get('date', 'Unknown')}\n"
                analysis += f"**Citation Count:** {citation.get('citation_count', 0)}\n"
                analysis += f"**Depth:** {citation.get('depth', 0)}\n"
                
                # Add authors if available
                authors = citation.get('authors', [])
                if authors:
                    analysis += f"**Authors:** {', '.join(authors[:5])}{'...' if len(authors) > 5 else ''}\n"
                
                # Add venue if available
                venue = citation.get('venue', '')
                if venue:
                    analysis += f"**Venue:** {venue}\n"
                
                # Add DOI if available
                doi = citation.get('doi', '')
                if doi:
                    analysis += f"**DOI:** {doi}\n"
                
                # Add abstract with full content
                abstract = citation.get('abstract', '')
                if abstract:
                    analysis += f"\n**ABSTRACT:**\n{abstract}\n"
                else:
                    analysis += f"\n**ABSTRACT:** No abstract available\n"
                
                # Add full content if available
                full_content = citation.get('full_content', '')
                if full_content and len(full_content) > len(abstract):
                    # Truncate if too long, but keep substantial content
                    if len(full_content) > 2000:
                        content_preview = full_content[:2000] + "\n\n[Content truncated for brevity - full content available in source]"
                    else:
                        content_preview = full_content
                    analysis += f"\n**FULL CONTENT:**\n{content_preview}\n"
                elif not abstract:
                    analysis += f"\n**FULL CONTENT:** No content available\n"
                
                # Add key concepts
                key_concepts = citation.get('key_concepts', [])
                if key_concepts:
                    analysis += f"\n**KEY CONCEPTS:** {', '.join(key_concepts[:10])}\n"
                
                # Add references if available
                references = citation.get('references', [])
                if references:
                    analysis += f"\n**REFERENCES:**\n"
                    for j, ref in enumerate(references[:5], 1):
                        if isinstance(ref, dict):
                            ref_title = ref.get('title', 'Unknown Reference')
                        else:
                            ref_title = str(ref)
                        analysis += f"  {j}. {ref_title}\n"
                    if len(references) > 5:
                        analysis += f"  ... and {len(references) - 5} more references\n"
                
                analysis += f"\n---\n"
        
        # Add research directions analysis (only if they're not corrupted)
        research_directions = session_data.get('research_directions', [])
        if research_directions:
            # Filter out corrupted directions
            clean_directions = []
            for direction in research_directions:
                if (direction and 
                    len(direction) < 100 and 
                    not direction.startswith("page applications") and
                    not "page applications" in direction):
                    clean_directions.append(direction)
            
            if clean_directions:
                analysis += f"\n**🔍 RESEARCH DIRECTIONS EXPLORED:**\n"
                for i, direction in enumerate(clean_directions[:5], 1):
                    analysis += f"{i}. {direction}\n"
        
        # Add thinking process summary
        thinking_process = session_data.get('thinking_process', [])
        if thinking_process:
            analysis += f"\n**🧠 THINKING PROCESS SUMMARY:**\n"
            for i, thought in enumerate(thinking_process[:5], 1):
                analysis += f"{i}. {thought[:200]}{'...' if len(thought) > 200 else ''}\n"
        
        # Add knowledge graph insights
        kg_summary = session_data.get('knowledge_graph', {})
        if kg_summary.get('total_entities', 0) > 0:
            analysis += f"\n**🧠 KNOWLEDGE GRAPH INSIGHTS:**\n"
            analysis += f"• Total entities: {kg_summary.get('total_entities', 0)}\n"
            analysis += f"• Total relationships: {kg_summary.get('total_relationships', 0)}\n"
            analysis += f"• Total triples: {kg_summary.get('total_triples', 0)}\n"
            analysis += f"• Average confidence: {kg_summary.get('avg_confidence', 0):.3f}\n"
            analysis += f"• Semantic richness: {kg_summary.get('semantic_richness', 0):.3f}\n"
        
        # Add comprehensive summary for LLM
        analysis += f"""

🧠 **COMPREHENSIVE SUMMARY FOR LLM ANALYSIS:**

**RESEARCH TOPIC:** {topic}
**TOTAL SOURCES ANALYZED:** {len(citations)}
**RESEARCH DEPTH:** {session_data.get('research_depth', 'Unknown')}
**THINKING DEPTH:** {session_data.get('thinking_depth', 'Unknown')}
**TOTAL ITERATIONS:** {session_data.get('total_iterations', 0)}

**KEY FINDINGS:**
• **Critical Issues:** {len(critical_issues)} major problems identified
• **Research Gaps:** {len(research_gaps)} significant gaps found
• **Controversies:** {len(controversies)} areas of debate identified
• **Practical Implications:** {len(practical_implications)} real-world impacts
• **Recommendations:** {len(recommendations)} actionable next steps

**CONTENT QUALITY:**
• **Abstracts Available:** {abstracts_found}/{len(citations)} ({abstracts_found/len(citations)*100:.1f}%)
• **Full Content Available:** {full_content_found}/{len(citations)} ({full_content_found/len(citations)*100:.1f}%)
• **Unique Concepts:** {len(unique_concepts)} key concepts identified
• **Source Diversity:** {len(source_groups)} different source types

**RESEARCH SCOPE:**
• **Wikipedia Sources:** {source_groups.get('wikipedia', [])}
• **arXiv Papers:** {source_groups.get('arxiv', [])}
• **Semantic Scholar:** {source_groups.get('semantic_scholar', [])}
• **OpenAlex Works:** {source_groups.get('openalex', [])}
• **PubMed Articles:** {source_groups.get('pubmed', [])}

**ANALYSIS READY FOR LLM PROCESSING:**
The above research content provides comprehensive coverage of the topic with detailed abstracts, full content where available, and complete metadata for each source. This enables thorough analysis, synthesis, and critical evaluation of the research findings.
"""
        
        # Add session metadata
        analysis += f"""

📋 **DETAILED SESSION METADATA:**
• **Session ID:** {session_data.get('session_id', 'Unknown')}
• **Start Time:** {session_data.get('start_time', 'Unknown')}
• **End Time:** {session_data.get('end_time', 'Unknown')}
• **Total Iterations:** {session_data.get('total_iterations', 0)}
• **Research Depth:** {session_data.get('research_depth', 'Unknown')}
• **Thinking Depth:** {session_data.get('thinking_depth', 'Unknown')}
• **Auto Iteration:** {session_data.get('auto_iterate', False)}
• **Reused Existing Research:** {session_data.get('reused_existing', False)}
• **Status:** {session_data.get('status', 'Unknown')}

**SOURCE BREAKDOWN:**
"""
        source_breakdown = self._get_source_breakdown()
        for source, count in source_breakdown.items():
            analysis += f"• {source}: {count} sources\n"
        
        analysis += f"""

**CONTENT METRICS DETAILS:**
"""
        content_metrics = self._calculate_content_metrics()
        for key, value in content_metrics.items():
            if isinstance(value, float):
                analysis += f"• {key}: {value:.3f}\n"
            else:
                analysis += f"• {key}: {value}\n"
        
        analysis += f"""

*🔴 Researcher's Wet Dream completed - Comprehensive critical analysis with complete research content for LLM processing*
        """
        
        return analysis.strip()

    def _add_to_knowledge_graph(self, citation):
        """Add citation to Microsoft-style knowledge graph with rich semantic relationships."""
        # Create entity for the citation
        entity_data = {
            "title": citation.get('title', ''),
            "url": citation.get('url', ''),
            "source": citation.get('source', ''),
            "abstract": citation.get('abstract', ''),
            "full_content": citation.get('full_content', ''),
            "authors": citation.get('authors', []),
            "date": citation.get('date', ''),
            "venue": citation.get('venue', ''),
            "citation_count": citation.get('citation_count', 0),
            "key_concepts": citation.get('key_concepts', []),
            "depth": citation.get('depth', 0),
            "paper_id": citation.get('paper_id', ''),
            "doi": citation.get('doi', ''),
            "type": "research_paper" if citation.get('source') in ["arxiv", "semantic_scholar", "openalex", "pubmed"] else "encyclopedia_article"
        }
        
        entity_id = self._create_entity(entity_data)
        
        # Create relationships for the citation
        semantic_relationships = self._extract_semantic_relationships(entity_data)
        
        for rel_data in semantic_relationships:
            relation_id = self._create_relationship({
                "name": rel_data["type"],
                "type": "semantic",
                "description": rel_data["description"],
                "semantic_meaning": rel_data["type"],
                "confidence_threshold": 0.5
            })
            
            # Create entity for the tail if it doesn't exist
            tail_entity_id = self._get_or_create_entity(rel_data["tail"], "concept")
            
            # Add triple
            self._add_triple(
                entity_id, 
                relation_id, 
                tail_entity_id,
                confidence=rel_data["confidence"],
                source_info={
                    "source": citation.get('source', ''),
                    "url": citation.get('url', ''),
                    "extraction_method": "semantic_analysis"
                }
            )
    
    def _create_entity(self, entity_data: Dict[str, Any]) -> str:
        """Create a new entity in the knowledge graph."""
        entity_id = f"entity_{self.entity_counter}"
        self.entity_counter += 1
        
        # Create entity structure
        entity = {
            "id": entity_id,
            "type": entity_data.get("type", "unknown"),
            "attributes": {
                "title": entity_data.get("title", ""),
                "url": entity_data.get("url", ""),
                "source": entity_data.get("source", ""),
                "abstract": entity_data.get("abstract", ""),
                "full_content": entity_data.get("full_content", ""),
                "authors": entity_data.get("authors", []),
                "venue": entity_data.get("venue", ""),
                "citation_count": entity_data.get("citation_count", 0),
                "paper_id": entity_data.get("paper_id", ""),
                "doi": entity_data.get("doi", ""),
                "content_length": len(entity_data.get("full_content", "")),
                "abstract_length": len(entity_data.get("abstract", ""))
            },
            "temporal_context": {
                "publication_date": entity_data.get("date", ""),
                "last_updated": datetime.now().isoformat()
            },
            "semantic_features": {
                "key_concepts": entity_data.get("key_concepts", []),
                "depth": entity_data.get("depth", 0)
            }
        }
        
        self.knowledge_graph["entities"][entity_id] = entity
        return entity_id
    
    def _create_relationship(self, relationship_data: Dict[str, Any]) -> str:
        """Create a new relationship in the knowledge graph."""
        relationship_id = f"rel_{self.relationship_counter}"
        self.relationship_counter += 1
        
        relationship = {
            "id": relationship_id,
            "name": relationship_data.get("name", ""),
            "type": relationship_data.get("type", "semantic"),
            "description": relationship_data.get("description", ""),
            "semantic_meaning": relationship_data.get("semantic_meaning", ""),
            "confidence_threshold": relationship_data.get("confidence_threshold", 0.5)
        }
        
        self.knowledge_graph["relationships"][relationship_id] = relationship
        return relationship_id
    
    def _get_or_create_entity(self, entity_name: str, entity_type: str) -> str:
        """Get existing entity or create a new one."""
        # Check if entity already exists
        for entity_id, entity in self.knowledge_graph["entities"].items():
            if entity["attributes"].get("title") == entity_name:
                return entity_id
        
        # Create new entity
        entity_data = {
            "title": entity_name,
            "type": entity_type,
            "url": "",
            "source": "concept",
            "abstract": "",
            "full_content": "",
            "authors": [],
            "date": "",
            "venue": "",
            "citation_count": 0,
            "key_concepts": [entity_name],
            "depth": 0,
            "paper_id": "",
            "doi": ""
        }
        
        return self._create_entity(entity_data)
    
    def _add_triple(self, head_entity: str, relation: str, tail_entity: str, 
                   confidence: float = 0.5, source_info: Optional[Dict[str, Any]] = None):
        """Add a triple to the knowledge graph."""
        triple_id = f"triple_{self.triple_counter}"
        self.triple_counter += 1
        
        triple = {
            "id": triple_id,
            "head_entity": head_entity,
            "relation": relation,
            "tail_entity": tail_entity,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "source_info": source_info or {}
        }
        
        self.knowledge_graph["triples"].append(triple)
        self.knowledge_graph["confidence_scores"][triple_id] = confidence
        self.knowledge_graph["provenance_tracking"][triple_id] = source_info or {}
    
    def _extract_semantic_relationships(self, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract semantic relationships from entity data."""
        relationships = []
        
        # Extract concept relationships
        concepts = entity_data.get("key_concepts", [])
        for concept in concepts[:5]:  # Limit to 5 concepts
            relationships.append({
                "type": "discusses",
                "description": f"Entity discusses concept: {concept}",
                "tail": concept,
                "confidence": 0.8
            })
        
        # Extract author relationships
        authors = entity_data.get("authors", [])
        for author in authors[:3]:  # Limit to 3 authors
            relationships.append({
                "type": "authored_by",
                "description": f"Entity authored by: {author}",
                "tail": author,
                "confidence": 0.9
            })
        
        # Extract venue relationships
        venue = entity_data.get("venue", "")
        if venue:
            relationships.append({
                "type": "published_in",
                "description": f"Entity published in: {venue}",
                "tail": venue,
                "confidence": 0.7
            })
        
        return relationships

    def _get_knowledge_graph_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the Microsoft-style knowledge graph."""
        entities = list(self.knowledge_graph["entities"].values())
        triples = self.knowledge_graph["triples"]

        # Calculate advanced metrics
        total_content_length = sum(
            (entity.get("attributes", {}).get("content_length", 0) for entity in entities)
        )
        total_abstract_length = sum(
            (entity.get("attributes", {}).get("abstract_length", 0) for entity in entities)
        )

        # Calculate confidence statistics
        confidence_scores = list(self.knowledge_graph["confidence_scores"].values())
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Calculate temporal span
        dates = [
            entity.get("temporal_context", {}).get("publication_date")
            for entity in entities
            if entity.get("temporal_context", {}).get("publication_date")
        ]
        temporal_span = None
        if dates:
            try:
                temporal_span = min(dates), max(dates)
            except Exception:
                temporal_span = None

        # Calculate source coverage
        source_counts = {}
        for entity in entities:
            source = entity.get("attributes", {}).get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        # Calculate relationship diversity
        relationship_types = {}
        for triple in triples:
            rel_id = triple["relation"]
            if rel_id in self.knowledge_graph["relationships"]:
                rel_type = self.knowledge_graph["relationships"][rel_id].get("name", "unknown")
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

        return {
            "total_entities": len(entities),
            "total_relationships": len(self.knowledge_graph["relationships"]),
            "total_triples": len(triples),
            "avg_confidence": avg_confidence,
            "temporal_span": temporal_span,
            "source_coverage": source_counts,
            "relationship_diversity": relationship_types,
            "total_content_length": total_content_length,
            "total_abstract_length": total_abstract_length,
            "avg_content_per_entity": total_content_length / len(entities) if entities else 0,
            "avg_abstract_per_entity": total_abstract_length / len(entities) if entities else 0,
            "entity_types": self._count_entity_types(entities),
            "semantic_richness": self._calculate_semantic_richness(),
            "knowledge_coverage": self._calculate_knowledge_coverage()
        }
    
    def _count_entity_types(self, entities: List[Dict]) -> Dict[str, int]:
        """Count entities by type."""
        type_counts = {}
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        return type_counts
    
    def _calculate_semantic_richness(self) -> float:
        """Calculate semantic richness of the knowledge graph."""
        total_concepts = 0
        total_relationships = 0
        
        for entity in self.knowledge_graph["entities"].values():
            concepts = entity["semantic_features"].get("key_concepts", [])
            total_concepts += len(concepts)
        
        total_relationships = len(self.knowledge_graph["triples"])
        
        # Richness based on concepts per entity and relationship density
        avg_concepts = total_concepts / len(self.knowledge_graph["entities"]) if self.knowledge_graph["entities"] else 0
        relationship_density = total_relationships / len(self.knowledge_graph["entities"]) if self.knowledge_graph["entities"] else 0
        
        return (avg_concepts * 0.4 + relationship_density * 0.6) / 10  # Normalize to 0-1
    
    def _calculate_knowledge_coverage(self) -> Dict[str, float]:
        """Calculate knowledge coverage across different dimensions."""
        entities = list(self.knowledge_graph["entities"].values())
        
        coverage = {
            "content_coverage": 0.0,
            "temporal_coverage": 0.0,
            "source_coverage": 0.0,
            "concept_coverage": 0.0
        }
        
        if entities:
            # Content coverage
            entities_with_content = len([e for e in entities if e["attributes"].get("content_length", 0) > 0])
            coverage["content_coverage"] = entities_with_content / len(entities)
            
            # Temporal coverage
            entities_with_date = len([e for e in entities if e["temporal_context"]["publication_date"]])
            coverage["temporal_coverage"] = entities_with_date / len(entities)
            
            # Source coverage (diversity of sources)
            unique_sources = len(set(e["attributes"].get("source", "") for e in entities))
            coverage["source_coverage"] = min(unique_sources / 5, 1.0)  # Normalize to 5 sources max
            
            # Concept coverage
            all_concepts = set()
            for entity in entities:
                all_concepts.update(entity["semantic_features"].get("key_concepts", []))
            coverage["concept_coverage"] = min(len(all_concepts) / 100, 1.0)  # Normalize to 100 concepts max
        
        return coverage
    
    def _identify_critical_issues(self, citations: List[Dict[str, Any]], session_data: Dict[str, Any]) -> List[str]:
        """Identify critical issues and problems in the research."""
        issues = []
        
        # Check for methodological issues
        if len(citations) < 5:
            issues.append("Insufficient sample size - limited number of sources analyzed")
        
        # Check source diversity
        sources = set(c.get('source', 'unknown') for c in citations)
        if len(sources) < 3:
            issues.append("Limited source diversity - research may be biased towards specific databases")
        
        # Check for contradictory findings
        titles = [c.get('title', '').lower() for c in citations]
        if len(set(titles)) < len(titles):
            issues.append("Potential duplicate sources identified - may indicate limited research scope")
        
        # Check content quality
        abstracts_found = sum(1 for c in citations if c.get('abstract') and len(c.get('abstract', '')) > 50)
        if abstracts_found < len(citations) * 0.7:
            issues.append("Poor abstract coverage - many sources lack detailed abstracts for analysis")
        
        # Check for recent research
        recent_sources = 0
        for citation in citations:
            date = citation.get('date', '')
            if date and len(date) >= 4:
                try:
                    year = int(date[:4])
                    if year >= 2020:
                        recent_sources += 1
                except ValueError:
                    pass
        
        if recent_sources < len(citations) * 0.3:
            issues.append("Limited recent research - most sources are outdated, may not reflect current state")
        
        # Check citation quality
        low_citation_sources = sum(1 for c in citations if c.get('citation_count', 0) < 10)
        if low_citation_sources > len(citations) * 0.5:
            issues.append("Many low-citation sources - research quality may be questionable")
        
        return issues
    
    def _identify_research_gaps(self, citations: List[Dict[str, Any]], session_data: Dict[str, Any]) -> List[str]:
        """Identify research gaps and missing pieces."""
        gaps = []
        
        # Analyze source coverage gaps
        sources = set(c.get('source', 'unknown') for c in citations)
        if 'wikipedia' not in sources:
            gaps.append("Missing encyclopedia perspective - no Wikipedia sources for foundational context")
        if 'arxiv' not in sources:
            gaps.append("Missing academic paper analysis - no arXiv sources for technical depth")
        if 'semantic_scholar' not in sources:
            gaps.append("Missing citation network analysis - no Semantic Scholar for impact assessment")
        
        # Analyze concept coverage
        all_concepts = []
        for citation in citations:
            concepts = citation.get('key_concepts', [])
            if isinstance(concepts, list):
                all_concepts.extend(concepts)
        
        if len(set(all_concepts)) < 10:
            gaps.append("Limited concept diversity - narrow scope of key concepts identified")
        
        # Analyze temporal gaps
        years = []
        for citation in citations:
            date = citation.get('date', '')
            if date and len(date) >= 4:
                try:
                    year = int(date[:4])
                    years.append(year)
                except ValueError:
                    pass
        
        if years:
            year_range = max(years) - min(years)
            if year_range < 5:
                gaps.append("Limited temporal coverage - research spans only a few years")
        
        # Analyze depth gaps
        depths = [c.get('depth', 0) for c in citations]
        if max(depths) < 2:
            gaps.append("Shallow citation depth - limited exploration of reference networks")
        
        return gaps
    
    def _identify_controversies(self, citations: List[Dict[str, Any]], session_data: Dict[str, Any]) -> List[str]:
        """Identify controversies and debates in the research."""
        controversies = []
        
        # Look for contradictory findings in titles and abstracts
        titles = [c.get('title', '').lower() for c in citations]
        abstracts = [c.get('abstract', '').lower() for c in citations]
        
        # Check for opposing viewpoints in titles
        opposing_terms = [
            ('benefit', 'harm'), ('advantage', 'disadvantage'), ('pro', 'con'),
            ('positive', 'negative'), ('support', 'oppose'), ('agree', 'disagree')
        ]
        
        for term1, term2 in opposing_terms:
            has_term1 = any(term1 in title for title in titles)
            has_term2 = any(term2 in title for title in titles)
            if has_term1 and has_term2:
                controversies.append(f"Contradictory findings on {term1} vs {term2} - opposing viewpoints present")
        
        # Check for methodological disagreements
        if len(set(c.get('source', '') for c in citations)) > 3:
            controversies.append("Multi-source research may reveal methodological disagreements between fields")
        
        # Check for citation conflicts
        high_citation = [c for c in citations if c.get('citation_count', 0) > 100]
        low_citation = [c for c in citations if c.get('citation_count', 0) < 10]
        
        if high_citation and low_citation:
            controversies.append("Citation count disparities suggest potential disagreements in field consensus")
        
        return controversies
    
    def _analyze_practical_implications(self, citations: List[Dict[str, Any]], session_data: Dict[str, Any]) -> List[str]:
        """Analyze practical implications of the research."""
        implications = []
        
        # Check for policy implications
        policy_terms = ['policy', 'regulation', 'law', 'government', 'public', 'society']
        has_policy_implications = any(
            any(term in c.get('title', '').lower() or term in c.get('abstract', '').lower() 
                for term in policy_terms)
            for c in citations
        )
        
        if has_policy_implications:
            implications.append("Research has significant policy implications requiring government attention")
        
        # Check for industry applications
        industry_terms = ['industry', 'business', 'commercial', 'market', 'economic', 'financial']
        has_industry_implications = any(
            any(term in c.get('title', '').lower() or term in c.get('abstract', '').lower() 
                for term in industry_terms)
            for c in citations
        )
        
        if has_industry_implications:
            implications.append("Research has commercial applications with economic implications")
        
        # Check for ethical implications
        ethical_terms = ['ethical', 'moral', 'rights', 'privacy', 'security', 'safety', 'risk']
        has_ethical_implications = any(
            any(term in c.get('title', '').lower() or term in c.get('abstract', '').lower() 
                for term in ethical_terms)
            for c in citations
        )
        
        if has_ethical_implications:
            implications.append("Research raises ethical concerns requiring careful consideration")
        
        # Check for technological implications
        tech_terms = ['technology', 'innovation', 'development', 'advancement', 'breakthrough']
        has_tech_implications = any(
            any(term in c.get('title', '').lower() or term in c.get('abstract', '').lower() 
                for term in tech_terms)
            for c in citations
        )
        
        if has_tech_implications:
            implications.append("Research has technological implications for future development")
        
        return implications
    
    def _generate_critical_recommendations(self, citations: List[Dict[str, Any]], session_data: Dict[str, Any], 
                                         critical_issues: List[str], research_gaps: List[str]) -> List[str]:
        """Generate critical recommendations based on analysis."""
        recommendations = []
        
        # Address critical issues
        if "Insufficient sample size" in str(critical_issues):
            recommendations.append("Expand research scope with more diverse sources and deeper citation analysis")
        
        if "Limited source diversity" in str(critical_issues):
            recommendations.append("Include additional research databases to reduce source bias")
        
        if "Poor abstract coverage" in str(critical_issues):
            recommendations.append("Focus on sources with comprehensive abstracts for better analysis")
        
        if "Limited recent research" in str(critical_issues):
            recommendations.append("Prioritize recent publications to capture current state of knowledge")
        
        # Address research gaps
        if "Missing encyclopedia perspective" in str(research_gaps):
            recommendations.append("Include Wikipedia and other encyclopedia sources for foundational context")
        
        if "Missing academic paper analysis" in str(research_gaps):
            recommendations.append("Incorporate more academic papers for technical depth and rigor")
        
        if "Limited concept diversity" in str(research_gaps):
            recommendations.append("Explore broader concept space to identify interdisciplinary connections")
        
        # General recommendations
        recommendations.append("Conduct systematic review of contradictory findings to resolve conflicts")
        recommendations.append("Develop interdisciplinary research approach to address knowledge gaps")
        recommendations.append("Establish research priorities based on practical implications and societal impact")
        recommendations.append("Create comprehensive knowledge synthesis framework for future research")
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def _identify_loopholes(self, citations: List[Dict[str, Any]], session_data: Dict[str, Any]) -> List[str]:
        """Identify loopholes and weaknesses in the research."""
        loopholes = []
        
        # Check for logical gaps
        if len(citations) < 3:
            loopholes.append("Insufficient evidence base - conclusions may not be well-supported")
        
        # Check for alternative explanations
        abstracts = [c.get('abstract', '') for c in citations]
        alternative_terms = ['however', 'but', 'although', 'despite', 'nevertheless', 'alternative']
        has_alternatives = any(
            any(term in abstract.lower() for term in alternative_terms)
            for abstract in abstracts
        )
        
        if not has_alternatives:
            loopholes.append("Limited consideration of alternative explanations or counterarguments")
        
        # Check for bias indicators
        sources = [c.get('source', '') for c in citations]
        if len(set(sources)) == 1:
            loopholes.append("Single-source bias - all research from same database may introduce bias")
        
        # Check for missing context
        if not any('context' in c.get('abstract', '').lower() or 'background' in c.get('abstract', '').lower() 
                  for c in citations):
            loopholes.append("Missing contextual information - research may lack proper background context")
        
        # Check for methodological weaknesses
        if not any('method' in c.get('abstract', '').lower() or 'methodology' in c.get('abstract', '').lower() 
                  for c in citations):
            loopholes.append("Limited methodological discussion - research approaches may not be well-justified")
        
        # Check for validation gaps
        if not any('validate' in c.get('abstract', '').lower() or 'verify' in c.get('abstract', '').lower() 
                  for c in citations):
            loopholes.append("Missing validation approaches - findings may lack proper verification")
        
        return loopholes


class ResearchersWetDreamService(ToolService):
    """Researcher's Wet Dream service providing advanced autonomous research capabilities."""
    
    def __init__(self):
        super().__init__("researchers_wet_dream")
        self.engine = ResearchersWetDreamEngine()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for researcher's wet dream service."""
        return {
            "researchers_wet_dream": RichToolDescription(
                description=(
                    "🎯 **RESEARCHER'S WET DREAM** - Advanced Autonomous Research Tool\n\n"
                    "This is the ultimate research tool that combines deep research capabilities with "
                    "intelligent thinking processes for comprehensive, self-iterating research sessions.\n\n"
                    "**Core Capabilities:**\n"
                    "• **Multi-Source Deep Research:** Wikipedia, arXiv, Semantic Scholar, OpenAlex, PubMed\n"
                    "• **Intelligent Thinking Integration:** Hypothesis generation, verification, gap analysis\n"
                    "• **Self-Iteration:** Automatically identifies research gaps and explores new directions\n"
                    "• **Citation Network Analysis:** DFS traversal through academic citations\n"
                    "• **Dynamic Research Planning:** Adapts research strategy based on findings\n\n"
                    "**Research Process:**\n"
                    "1. **Initial Planning:** Think about research approach and key areas\n"
                    "2. **Deep Research:** Conduct comprehensive multi-source research\n"
                    "3. **Analysis:** Analyze findings and identify patterns\n"
                    "4. **Hypothesis Generation:** Generate hypotheses about gaps and contradictions\n"
                    "5. **Verification:** Verify findings and identify next research directions\n"
                    "6. **Iteration:** Repeat process with refined focus areas\n\n"
                    "**Advanced Features:**\n"
                    "• Autonomous research direction adjustment\n"
                    "• Cross-source validation and contradiction detection\n"
                    "• Comprehensive knowledge synthesis\n"
                    "• Multi-level citation analysis\n"
                    "• Dynamic hypothesis testing\n\n"
                    "**Use Cases:**\n"
                    "• Academic research and literature reviews\n"
                    "• Market research and competitive analysis\n"
                    "• Scientific investigation and hypothesis testing\n"
                    "• Comprehensive topic exploration\n"
                    "• Research gap identification\n"
                    "• Multi-perspective analysis\n\n"
                    "**Parameters:**\n"
                    "• topic: Research topic or question\n"
                    "• research_depth: Maximum citation depth (1-5)\n"
                    "• thinking_depth: Maximum thinking steps per iteration (1-10)\n"
                    "• auto_iterate: Enable automatic iteration (default: True)\n"
                    "• max_iterations: Maximum research iterations (1-15)\n"
                ),
                use_when=(
                    "Use for comprehensive research that requires deep analysis, multiple iterations, "
                    "and autonomous exploration of research directions. Ideal for academic research, "
                    "market analysis, scientific investigation, or any topic requiring thorough "
                    "multi-source analysis with intelligent synthesis."
                ),
                side_effects=(
                    "Makes extensive API calls to multiple research databases, performs deep citation "
                    "analysis, conducts multiple research iterations, and generates comprehensive reports. "
                    "May take significant time for complex topics."
                )
            )
        }
    
    def register_tools(self, mcp):
        """Register researcher's wet dream tools with the MCP server."""
        self.logger.info("Registering researcher's wet dream tools...")
        
        @mcp.tool(description=self.get_tool_descriptions()["researchers_wet_dream"].model_dump_json())
        async def researchers_wet_dream(
            topic: str,
            research_depth: int = 3,
            thinking_depth: int = 5,
            auto_iterate: bool = True,
            max_iterations: int = 10
        ) -> List[TextContent]:
            # Log complete input parameters
            input_data = {
                "topic": topic,
                "research_depth": research_depth,
                "thinking_depth": thinking_depth,
                "auto_iterate": auto_iterate,
                "max_iterations": max_iterations
            }
            logger.info(f"researchers_wet_dream tool called with complete input: {json.dumps(input_data, indent=2)}")
            
            try:
                logger.info(f"Starting Researcher's Wet Dream for topic: {topic}")
                
                # Initialize the research engine
                engine = ResearchersWetDreamEngine()
                
                # Conduct the research session with proper parameters
                result = await engine.conduct_research_session(
                    topic=topic,
                    research_depth=research_depth,
                    thinking_depth=thinking_depth,
                    auto_iterate=auto_iterate,
                    max_iterations=max_iterations
                )
                
                # Extract the final analysis
                session_data = result.get('session_data', result)
                final_analysis = session_data.get('final_analysis', 'Research completed but no analysis generated.')
                
                # Log complete output
                logger.info(f"researchers_wet_dream tool completed with complete output: {final_analysis}")
                return [TextContent(type="text", text=final_analysis.strip())]
                
            except Exception as e:
                error_msg = f"Error conducting research: {str(e)}"
                logger.error(f"researchers_wet_dream tool failed with complete error: {error_msg}")
                logger.error(f"Full exception details: {e}")
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=error_msg
                    )
                )