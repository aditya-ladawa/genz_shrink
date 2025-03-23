import os 
import re
import json
import ast

# typing_extensions
from typing_extensions import Union, Optional, List

# fastapi
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Response, Request, Query, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse

# postgres
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.store.postgres.aio import PoolConfig

# pydantic models
from api.pydm import *

# sql ops
from api.sql_ops import *

# sql alchemy
from sqlalchemy.exc import SQLAlchemyError

# jwt
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, DecodeError
from jwt import decode

# starlette
from starlette.middleware.base import BaseHTTPMiddleware

# datetime
from datetime import datetime, timedelta

# supabase
from supabase import create_client, Client

# lifespan
from contextlib import asynccontextmanager

# dotenv
from dotenv import load_dotenv

# chat handlers
from api.chat_handle import *

# redis ops
from api.redis_ops import *

# langchain
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage


# realtime stt
from RealtimeSTT import AudioToTextRecorder

load_dotenv()

# environment variables
DB_URI_CHECKPOINTER = os.environ.get('POSTGRES_CHECKPOINTER')
DB_URI_STORE = os.environ.get('POSTGRES_STORE')
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
ALGORITHM = os.environ.get('ALGORITHM')
# url: str = os.environ.get("SUPABASE_URL")
# key: str = os.environ.get("SUPABASE_KEY")
# supabase: Client = create_client(url, key)


# required variables
connection_kwargs = {"autocommit": True, "prepare_threshold": 0}
store_pool_config = PoolConfig(min_size=5,max_size=20)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print('\nStarted SQL db\n')

    await initialize_redis()
    print('\nStarted Redis db\n')

    # Initialize Postgres Checkpointer
    async with AsyncConnectionPool(conninfo=DB_URI_CHECKPOINTER, max_size=20, kwargs=connection_kwargs) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        print('\nInitialized Postgres Checkpointer\n')

        # Initialize Postgres Store
        async with AsyncPostgresStore.from_conn_string(conn_string=DB_URI_STORE, pool_config=store_pool_config) as store:
            await store.setup()
            app.state.store = store
            print('\nInitialized Postgres Store\n')

            # Initialize the graph
            app.state.graph = create_react_agent(
                llm, 
                [generate_contextual_meme, save_memory], 
                prompt=prepare_model_inputs, 
                store=store, 
                checkpointer=checkpointer,
                state_schema=State
            )
            print('\nInitialized Graph\n')

            # Yield control to the app
            yield

            # Cleanup Postgres Store
            del app.state.store
            print('\nCleaned up Postgres Store\n')

        # Cleanup Postgres Checkpointer
        del app.state.checkpointer
        print('\nCleaned up Postgres Checkpointer\n')

        # Cleanup Graph
        del app.state.graph
        print('\nCleaned up Graph\n')


app = FastAPI(docs_url="/docs", openapi_url="/openapi.json", debug=True, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routes
async def get_psql_checkpointer():
    return app.state.checkpointer

async def get_psql_store():
    return app.state.store

def get_authenticated_user(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
        }

    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except DecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed token")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@app.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, store=Depends(get_psql_store)):
    # Check if user already exists
    existing_user = await get_user_by_email(user.email.lower())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered. Please log in.",
        )

    # Validate password strength
    if not validate_password_strength(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 8 characters, including an uppercase letter, a number, and a special character.",
        )

    try:
        # Create new user
        new_user = await create_user(
            firstName=user.firstName.strip(),
            lastName=user.lastName.strip(),
            age=user.age,
            email=user.email.strip().lower(),
            raw_password=user.password
        )

        # Store user data
        signed_up_user_id = new_user.user_id
        signed_up_user_name = f"{new_user.firstName} {new_user.lastName}"
        signed_up_user_email = new_user.email


        await store.aput(
            namespace=('users'),
            key=signed_up_user_id,
            value={'name': signed_up_user_name, 'email': signed_up_user_email}
        )

        return JSONResponse(
            content={
                "message": f"User {signed_up_user_name} successfully registered.",
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during signup. Please try again later. {e}",
        )


@app.post("/login", status_code=200)
async def login(user: UserLogin, response: Response):
    try:
        db_user = await get_user_by_email(user.email.strip().lower())
        if db_user is None or not verify_password(user.password, db_user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        token = generate_jwt_token(user_id=db_user.user_id, email=db_user.email)

        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=False,  # Set to True if using HTTPS
            samesite='Strict',
            path="/",  # Ensure the cookie is accessible across all routes
        )

        return {
            "message": "Login successful",
            "data": {
                "session": {
                    "access_token": token,
                    "token_type": "bearer"
                }
            }
        }

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.post("/logout")
async def logout(response: Response):
    try:
        response.set_cookie(
            key="auth_token",
            value="", 
            expires="Thu, 01 Jan 1994 00:00:00 GMT",
            max_age=0, 
            httponly=True,
            secure=False,
            samesite="Strict",
            path="/",
        )
        return {"message": "Logout successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during logout: {str(e)}")


@app.get('/get_auth_user')
async def get_active_user(current_user: dict = Depends(get_authenticated_user)):
    return {'user': current_user}


@app.post('/label_chat')
async def label_new_chat(request: LabelChatRequest, current_user: dict = Depends(get_authenticated_user)):
    try:
        user_id = current_user.get("user_id")
        
        # Get the label from LLM chain
        label = assign_chat_topic_chain.invoke(request.message)
       
        # Create and store the conversation
        result = await label_conversation(
            user_id=user_id,
            llm_response_label=label,
        )

        return {
            "message": "Conversation labeled and stored successfully.",
            "conversation_id": result["conversation_id"],  # Ensure this key is correct
            "label": result["label"],
            "conversation_data": result["conversation_data"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error labeling chat: {str(e)}")


@app.get('/chat/{conversation_id}')
async def get_conversation_messages(conversation_id: str, current_user: dict = Depends(get_authenticated_user)):
    user_id = current_user.get("user_id")

    # Handle the case where conversation_id is "new"
    if conversation_id == "new":
        return {
            "conversation_id": "new",
            "messages": [],  # No messages for a new conversation
            "fetched_conversation": None  # No conversation to fetch
        }

    # Fetch the conversation for existing conversation IDs
    try:
        fetched_conversation = await fetch_conversation(user_id=user_id, conversation_id=conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get the state of the conversation graph asynchronously
    config = {"configurable": {"user_id": current_user.get("user_id"), "thread_id": conversation_id}}
    try:
        the_graph = await app.state.graph.aget_state(config=config, subgraphs=True)
        all_messages = the_graph.values.get('messages', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversation state: {str(e)}")

    # Process messages into a structured format
    processed_messages = []
    for msg in all_messages:
        if isinstance(msg, HumanMessage):
            processed_messages.append({
                "id": str(uuid.uuid4()),  # Generate a unique ID for the frontend
                "type": "HumanMessage",
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            })
        elif isinstance(msg, AIMessage):
            processed_messages.append({
                "id": str(uuid.uuid4()),
                "type": "AIMessage",
                "content": msg.content if msg.content is not None else '',
                "timestamp": datetime.now().isoformat()
            })
        elif isinstance(msg, ToolMessage):
            # Parse ToolMessage content (meme URLs)
            try:
                # Convert ToolMessage content to a structured format
                content = eval(msg.content)  # Convert string representation to actual objects
                meme_urls = []
                if isinstance(content, list):
                    meme_urls = [item.url for item in content if hasattr(item, 'url')]
                elif hasattr(content, 'url'):
                    meme_urls = [content.url]

                processed_messages.append({
                    "id": str(uuid.uuid4()),
                    "type": "ToolMessage",
                    "content": meme_urls,  # List of meme URLs
                    "name": msg.name,  # Tool name (e.g., 'generate_contextual_meme')
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Error parsing ToolMessage: {e}")
                continue  # Skip invalid ToolMessages

    return {
        "conversation_id": conversation_id,
        "messages": processed_messages,
        'fetched_conversation': fetched_conversation
    }



@app.get('/fetch_conversations')
async def fetch_conversations(current_user: dict = Depends(get_authenticated_user)):
    user_id = current_user.get("user_id")
    user_email = current_user.get("email")

    if not user_id or not user_email:
        raise HTTPException(status_code=400, detail="Invalid user details.")

    conversations = await fetch_user_conversations(user_id)

    if not conversations:
        return {"message": "No conversations found.", "conversations": []}

    return {"conversations": conversations}


async def get_authenticated_user_websocket(websocket: WebSocket):
    token = websocket.cookies.get("auth_token")

    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token has expired")

        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
        }

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.websocket("/llm_chat/{conversation_id}")
async def websocket_llm_chat(
    conversation_id: str,
    websocket: WebSocket,
    current_user: dict = Depends(get_authenticated_user_websocket),
    checkpointer=Depends(get_psql_checkpointer),
    store: AsyncPostgresStore = Depends(get_psql_store)
):  
    graph = app.state.graph
    await websocket.accept()
    current_conversation_id = conversation_id
    config = None
    recorder = None  # Initialize recorder as None
    recorded_text = None  # Store transcribed text

    try:
        if current_conversation_id == "new":
            # Wait for the first message, which could be text or audio
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "audio":
                # Initialize a new recorder
                recorder = AudioToTextRecorder()
                recorder.start()
                await websocket.send_json({"type": "audio_started", "message": "Recording started."})

                # Wait for stop_audio message
                stop_data = await websocket.receive_text()
                stop_message = json.loads(stop_data)
                if stop_message["type"] == "stop_audio":
                    recorder.stop()
                    recorded_text = recorder.text()
                    recorder.shutdown()
                    await websocket.send_json({
                        "type": "audio_transcription",
                        "content": recorded_text
                    })

            # Now, create a new conversation with the recorded text or initial text
            user_query = recorded_text if recorded_text else message.get("content", "")
            label = assign_chat_topic_chain.invoke(user_query)
            result = await label_conversation(
                user_id=current_user.get("user_id"),
                llm_response_label=label,
            )
            current_conversation_id = result["conversation_id"]
            config = {"configurable": {"user_id": current_user["user_id"], "thread_id": current_conversation_id}}
            
            await websocket.send_json({
                "type": "new_conversation",
                "conversation_id": current_conversation_id,
                "message": "New conversation started."
            })
            
            await process_message(graph, user_query, config, websocket)
        else:
            config = {"configurable": {"user_id": current_user["user_id"], "thread_id": current_conversation_id}}
            await websocket.send_json({"type": "connection_ready", "message": "Connected!"})

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "audio":
                # Initialize a new recorder for each recording session
                recorder = AudioToTextRecorder()
                recorder.start()
                await websocket.send_json({"type": "audio_started", "message": "Recording started."})
            elif message["type"] == "stop_audio":
                if recorder:  # Ensure the recorder exists
                    recorder.stop()
                    recorded_text = recorder.text()
                    await websocket.send_json({
                        "type": "audio_transcription",
                        "content": recorded_text
                    })
                    recorder.shutdown()
                    recorder = None  # Reset the recorder

                    # Pass the transcribed text to the LLM
                    await process_message(graph, recorded_text, config, websocket)
            else:
                await process_message(graph, message["content"], config, websocket)

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        await websocket.close(code=1011, reason="Server error")


async def process_message(graph, query_text: str, config: dict, websocket: WebSocket):
    query = {"messages": [HumanMessage(content=query_text)]}

    async for event in graph.astream(query, stream_mode="values", config=config):
        if "messages" not in event:
            continue
        
        latest_msg = event["messages"][-1]
        
        if isinstance(latest_msg, AIMessage):
            if not latest_msg.content:
                continue

            # Check if the AIMessage has tool_calls
            if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                # Handle tool_calls
                for tool_call in latest_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    # Invoke the tool (e.g., generate_contextual_meme)
                    if tool_name == "generate_contextual_meme":
                        # Simulate tool invocation (replace with actual tool logic)
                        meme_urls = generate_memes(tool_args["conversation_context"], tool_args["num_memes"])

                        # Create a ToolMessage with the results
                        tool_message = ToolMessage(
                            content=" ".join(meme_urls),  # Join URLs with a space
                            tool_call_id=tool_call["id"],  # Match the tool_call_id
                            additional_kwargs={"urls": meme_urls}  # Include the meme URLs as a list
                        )

                        # Send the ToolMessage back to the graph
                        await graph.astream(
                            {"messages": [tool_message]},
                            stream_mode="values",
                            config=config
                        )

                        # Send the meme URLs to the frontend
                        await websocket.send_json({
                            "type": "tool_message",
                            "content": " ".join(meme_urls),
                            "urls": meme_urls
                        })
            else:
                # If no tool_calls, send the AI response to the frontend
                await websocket.send_json({
                    "type": "ai_message",
                    "content": latest_msg.content
                })
        
        elif isinstance(latest_msg, ToolMessage):
            try:
                # Extract URLs and clean them
                meme_urls = re.findall(r"https?://\S+", latest_msg.content)
                cleaned_meme_urls = [url.rstrip("',") for url in meme_urls]  # Remove trailing commas and quotes

                # Send the meme URLs to the frontend
                await websocket.send_json({
                    "type": "tool_message",
                    "content": " ".join(cleaned_meme_urls),
                    "urls": cleaned_meme_urls
                })
            except (ValueError, SyntaxError, KeyError) as e:
                print(f"Error parsing ToolMessage content: {e}")
                await websocket.send_json({"type": "error", "message": "Failed to parse ToolMessage content."})

