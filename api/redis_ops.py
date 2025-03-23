import uuid
from datetime import datetime
import redis.asyncio as redis
import json
from typing import Optional, Dict

redis_client = None  # Global Redis client for shared use

async def initialize_redis():
    """
    Initialize the Redis connection.
    """
    global redis_client
    if not redis_client:
        redis_client = redis.Redis.from_url(
            "redis://localhost:6379", decode_responses=True,
        )
        print("Redis connection initialized.")


async def close_redis_connection():
    """
    Gracefully close the Redis connection.
    """
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None
        print("Redis connection closed.")


async def add_conversation(user_id: str, email: str, name: str, description: str, topic: str):
    """
    Add a conversation to the Redis database with the specified structure.
    """
    user_key = f"user:{user_id}"
    conversation_id = str(uuid.uuid4())  # Unique conversation ID
    timestamp = datetime.now().isoformat()

    # Ensure the user exists with their email
    await redis_client.hset(user_key, mapping={"user_email": email})

    # Structure for the conversation
    conversation_data = {
        "name": name,
        "description": description,
        "timestamp": timestamp,
        "topic": topic,
    }

    # Add the conversation under 'user:{user_id}:conversations'
    conversations_key = f"{user_key}:conversations"
    await redis_client.hset(conversations_key, conversation_id, json.dumps(conversation_data))

    return {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "conversation_data": conversation_data,
    }


async def fetch_user_conversations(user_id: str) -> list:
    """
    Fetch all conversations for a user.
    """
    user_conversations_key = f"user:{user_id}:conversations"
    conversations_data = await redis_client.hgetall(user_conversations_key)

    if not conversations_data:
        return []

    conversations = []
    for conversation_id, conversation_json in conversations_data.items():
        try:
            conversation = json.loads(conversation_json)
            conversation["id"] = conversation_id
            # Format the timestamp
            if 'timestamp' in conversation:
                timestamp = datetime.fromisoformat(conversation['timestamp'])
                conversation['created_at'] = timestamp.strftime('%Y-%m-%d %H:%M')
                del conversation['timestamp']
            conversations.append(conversation)
        except json.JSONDecodeError:
            continue  # Skip invalid JSON

    return conversations


async def fetch_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Fetch a specific conversation by ID.
    """
    user_conversations_key = f"user:{user_id}:conversations"
    conversation_json = await redis_client.hget(user_conversations_key, conversation_id)
    
    if conversation_json is None:
        raise ValueError(f"Conversation with ID {conversation_id} not found for user {user_id}.")

    try:
        conversation = json.loads(conversation_json)
        conversation["id"] = conversation_id

        if 'timestamp' in conversation:
            timestamp = datetime.fromisoformat(conversation['timestamp'])
            conversation['created_at'] = timestamp.strftime('%Y-%m-%d %H:%M')
            del conversation['timestamp']
        
        return conversation

    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding conversation data: {str(e)}")


async def delete_conversation(user_id: str, conversation_id: str):
    """
    Delete a conversation from Redis.
    """
    user_conversations_key = f"user:{user_id}:conversations"
    await redis_client.hdel(user_conversations_key, conversation_id)
    return {"message": f"Conversation {conversation_id} deleted successfully."}


async def label_conversation(user_id: str, llm_response_label:str) -> Dict:
    """
    Label a new conversation based on the first message and store it in Redis.
    """
    # Generate a unique conversation ID
    conversation_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    label = llm_response_label

    # Store the conversation in Redis
    conversation_data = {
        "name": f"Conversation {conversation_id}",
        "timestamp": timestamp,
        "topic": label,
    }

    user_key = f"user:{user_id}"
    conversations_key = f"{user_key}:conversations"
    await redis_client.hset(conversations_key, conversation_id, json.dumps(conversation_data))

    return {
        "conversation_id": conversation_id,
        "label": label,
        "conversation_data": conversation_data,
    }