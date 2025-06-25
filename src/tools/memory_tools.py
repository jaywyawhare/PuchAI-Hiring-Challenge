"""
Memory-related tools for MCP server.
"""
from typing import List, Optional, Dict, Any
from mcp.types import TextContent
from ..services.memory_service import MemoryService
from ..models.base import RichToolDescription
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def register_memory_tools(mcp):
    """Register memory-related tools with the MCP server."""
    
    memory_service = MemoryService()
    
    async def auto_store_conversation(user_id: str, text: str, role: str = "user") -> bool:
        """Automatically store a conversation turn."""
        try:
            metadata = {
                "role": role,
                "conversation_id": f"{user_id}_{datetime.utcnow().date().isoformat()}"
            }
            return await memory_service.store_memory(user_id, text, metadata)
        except Exception as e:
            logger.error(f"Failed to auto-store conversation: {e}")
            return False
    
    async def get_relevant_context(user_id: str, current_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant context from past conversations."""
        try:
            return await memory_service.search_memories(user_id, current_text, limit)
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []
    
    # Create rich descriptions for tools
    store_memory_desc = RichToolDescription(
        description="Store a new memory in the conversation history",
        use_when="By default you should store all conversation history",
        side_effects="Stores the memory in the vector database"
    )
    
    search_memories_desc = RichToolDescription(
        description="Search through conversation history for relevant memories",
        use_when="When you need to recall previous conversations or context, which should be done before every response",
        side_effects="Searches the vector database for relevant memories"
    )
    
    recent_memories_desc = RichToolDescription(
        description="Get recent conversation memories",
        use_when="When you need to see the most recent conversation context",
        side_effects="Retrieves recent memories from the database"
    )
    
    clear_memories_desc = RichToolDescription(
        description="Clear all memories for a user",
        use_when="When a user requests to clear their conversation history",
        side_effects="Deletes all stored memories for the specified user"
    )

    @mcp.tool(description=store_memory_desc.model_dump_json())
    async def store_memory(
        text: str,
        user_id: str,
        metadata: Optional[dict] = None
    ) -> List[TextContent]:
        """
        Store a new memory in the conversation history.
        
        Args:
            text: The text content to remember
            user_id: ID of the user this memory belongs to
            metadata: Optional additional metadata about the memory
            
        Returns:
            Status message indicating if the memory was stored successfully
        """
        try:
            # Auto-store the conversation
            success = await auto_store_conversation(user_id, text)
            
            if success:
                return [TextContent(
                    type="text",
                    text="✅ Memory stored successfully"
                )]
            else:
                return [TextContent(
                    type="text",
                    text="❌ Failed to store memory"
                )]
                
        except Exception as e:
            logger.error(f"Error in store_memory: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error storing memory: {str(e)}"
            )]
    
    @mcp.tool(description=search_memories_desc.model_dump_json())
    async def search_memories(
        query: str,
        user_id: str,
        limit: int = 5
    ) -> List[TextContent]:
        """
        Search through conversation history for relevant memories.
        
        Args:
            query: Search query to find relevant memories
            user_id: ID of the user whose memories to search
            limit: Maximum number of memories to return
            
        Returns:
            List of relevant memories with similarity scores
        """
        try:
            memories = await memory_service.search_memories(user_id, query, limit)
            
            if not memories:
                return [TextContent(
                    type="text",
                    text=f"🔍 No relevant memories found for query: '{query}'"
                )]
            
            response_parts = [
                f"🔍 **Found {len(memories)} relevant memories:**\n"
            ]
            
            for i, memory in enumerate(memories, 1):
                similarity = memory.get("similarity_score", 0) * 100
                response_parts.append(
                    f"{i}. [{memory['timestamp']}] (Match: {similarity:.1f}%)\n"
                    f"   {memory['text']}\n"
                )
            
            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            logger.error(f"Error in search_memories: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error searching memories: {str(e)}"
            )]
    
    @mcp.tool(description=recent_memories_desc.model_dump_json())
    async def get_recent_memories(
        user_id: str,
        limit: int = 5
    ) -> List[TextContent]:
        """
        Get the most recent conversation memories.
        
        Args:
            user_id: ID of the user whose memories to retrieve
            limit: Maximum number of memories to return
            
        Returns:
            List of recent memories in chronological order
        """
        try:
            memories = await memory_service.get_recent_memories(user_id, limit)
            
            if not memories:
                return [TextContent(
                    type="text",
                    text="📝 No recent memories found"
                )]
            
            response_parts = [
                f"📝 **Last {len(memories)} memories:**\n"
            ]
            
            for i, memory in enumerate(memories, 1):
                response_parts.append(
                    f"{i}. [{memory['timestamp']}]\n"
                    f"   {memory['text']}\n"
                )
            
            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_recent_memories: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error retrieving recent memories: {str(e)}"
            )]
    
    @mcp.tool(description=clear_memories_desc.model_dump_json())
    async def clear_memories(user_id: str) -> List[TextContent]:
        """
        Clear all memories for a user.
        
        Args:
            user_id: ID of the user whose memories to clear
            
        Returns:
            Status message indicating if the memories were cleared successfully
        """
        try:
            success = await memory_service.clear_user_memories(user_id)
            
            if success:
                return [TextContent(
                    type="text",
                    text="🗑️ All memories cleared successfully"
                )]
            else:
                return [TextContent(
                    type="text",
                    text="❌ Failed to clear memories"
                )]
                
        except Exception as e:
            logger.error(f"Error in clear_memories: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error clearing memories: {str(e)}"
            )]
