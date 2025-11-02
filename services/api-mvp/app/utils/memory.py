"""
Conversation memory management using mem0.

This module provides persistent conversation storage using the mem0 library,
replacing the previous in-memory approach. Conversations are stored by session ID
and can be retrieved across application restarts.

Key features:
- Persistent storage of user/assistant messages
- Session-based conversation tracking
- Automatic memory initialization
- Search and retrieval of conversation history
- Memory cleanup for expired sessions
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Lazy import to handle optional dependency
_mem0_client = None


def get_mem0_client():
    """
    Get or create the singleton mem0 client.

    Returns:
        Memory client instance or None if mem0 is disabled/unavailable
    """
    global _mem0_client

    if _mem0_client is not None:
        return _mem0_client

    # Check if mem0 is enabled
    mem0_enabled = os.getenv("MEM0_ENABLED", "true").lower() == "true"
    if not mem0_enabled:
        logger.info("mem0 is disabled via MEM0_ENABLED environment variable")
        return None

    try:
        from mem0 import Memory

        # Configure mem0 with persistence
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "conversations",
                    "embedding_model_dims": 384,
                    "path": os.getenv("MEM0_STORAGE_PATH", "/tmp/mem0_storage"),
                },
            }
        }

        _mem0_client = Memory.from_config(config)
        logger.info("mem0 client initialized successfully")
        return _mem0_client

    except ImportError:
        logger.warning("mem0 library not installed. Install with: pip install mem0ai")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize mem0 client: {e}")
        return None


def store_message(
    session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Store a conversation message in mem0.

    Args:
        session_id: Unique session/conversation identifier
        role: Message role ('user' or 'assistant')
        content: Message content
        metadata: Optional additional metadata (focus mode, optimization, etc.)

    Returns:
        True if stored successfully, False otherwise
    """
    client = get_mem0_client()
    if client is None:
        logger.debug("mem0 not available, message not stored")
        return False

    try:
        # Prepare message data
        message_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        # Store in mem0 with session_id as user_id
        client.add(messages=content, user_id=session_id, metadata=message_data)

        logger.debug(f"Stored {role} message for session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store message in mem0: {e}")
        return False


def get_conversation_history(
    session_id: str, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve conversation history for a session.

    Args:
        session_id: Unique session/conversation identifier
        limit: Optional maximum number of messages to retrieve

    Returns:
        List of messages in chronological order
    """
    client = get_mem0_client()
    if client is None:
        logger.debug("mem0 not available, returning empty history")
        return []

    try:
        # Search memories for this session
        memories = client.search(
            query="",  # Empty query to get all memories for user
            user_id=session_id,
            limit=limit or 100,
        )

        # Extract and sort messages by timestamp
        messages = []
        for memory in memories:
            metadata = memory.get("metadata", {})
            if "role" in metadata and "content" in metadata:
                messages.append(
                    {
                        "role": metadata["role"],
                        "content": metadata["content"],
                        "timestamp": metadata.get("timestamp"),
                        "metadata": {
                            k: v
                            for k, v in metadata.items()
                            if k not in ["role", "content", "timestamp"]
                        },
                    }
                )

        # Sort by timestamp
        messages.sort(key=lambda x: x.get("timestamp", ""))

        logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")
        return messages

    except Exception as e:
        logger.error(f"Failed to retrieve conversation history: {e}")
        return []


def search_conversations(
    query: str, session_id: Optional[str] = None, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search conversations by semantic similarity.

    Args:
        query: Search query
        session_id: Optional session ID to limit search scope
        limit: Maximum number of results

    Returns:
        List of relevant conversation snippets
    """
    client = get_mem0_client()
    if client is None:
        logger.debug("mem0 not available, returning empty search results")
        return []

    try:
        memories = client.search(query=query, user_id=session_id, limit=limit)

        results = []
        for memory in memories:
            results.append(
                {
                    "content": memory.get("memory", ""),
                    "metadata": memory.get("metadata", {}),
                    "relevance": memory.get("score", 0.0),
                }
            )

        logger.debug(f"Found {len(results)} relevant conversation snippets")
        return results

    except Exception as e:
        logger.error(f"Failed to search conversations: {e}")
        return []


def delete_session(session_id: str) -> bool:
    """
    Delete all conversation history for a session.

    Args:
        session_id: Session identifier to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    client = get_mem0_client()
    if client is None:
        logger.debug("mem0 not available, session not deleted")
        return False

    try:
        # Get all memories for session
        memories = client.get_all(user_id=session_id)

        # Delete each memory
        for memory in memories:
            memory_id = memory.get("id")
            if memory_id:
                client.delete(memory_id)

        logger.info(f"Deleted session {session_id} with {len(memories)} messages")
        return True

    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        return False


def cleanup_old_sessions(days: int = 30) -> int:
    """
    Clean up sessions older than specified days.

    Args:
        days: Number of days to keep sessions

    Returns:
        Number of sessions cleaned up
    """
    client = get_mem0_client()
    if client is None:
        logger.debug("mem0 not available, no cleanup performed")
        return 0

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        # Get all memories
        all_memories = client.get_all()

        deleted_count = 0
        for memory in all_memories:
            metadata = memory.get("metadata", {})
            timestamp = metadata.get("timestamp", "")

            # Delete if older than cutoff
            if timestamp and timestamp < cutoff_iso:
                memory_id = memory.get("id")
                if memory_id:
                    client.delete(memory_id)
                    deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old conversation messages")
        return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup old sessions: {e}")
        return 0


def get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about stored conversations.

    Returns:
        Dictionary with stats (total messages, sessions, etc.)
    """
    client = get_mem0_client()
    if client is None:
        return {"enabled": False, "total_messages": 0, "unique_sessions": 0}

    try:
        all_memories = client.get_all()

        sessions = set()
        for memory in all_memories:
            metadata = memory.get("metadata", {})
            # Extract session from user_id or metadata
            session = metadata.get("session_id")
            if session:
                sessions.add(session)

        return {
            "enabled": True,
            "total_messages": len(all_memories),
            "unique_sessions": len(sessions),
        }

    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return {"enabled": True, "error": str(e)}
