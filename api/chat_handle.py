# llm chains
from .llm_chains import *

import os 
import aiohttp
import random
from urllib.parse import urlencode

# typing_extensions
from typing_extensions import Union, Optional, TypedDict, Annotated, List

# checkpointer and store
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# langgraph
from langgraph.prebuilt import create_react_agent


# langchain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, trim_messages


# dotenv
from dotenv import load_dotenv
load_dotenv()

# groq
from langchain_groq import ChatGroq

# pydantic
from pydantic import BaseModel, Field

# pydantic models
from .pydm import *

# realtime stt
from RealtimeSTT import AudioToTextRecorder


# llm = ChatGroq(model='llama-3.3-70b-versatile', temperature=0.7)
llm = ChatGroq(model='llama-3.2-90b-vision-preview', temperature=0.7)


# Environment variables for credentials
IMGFLIP_USERNAME = os.getenv("IMGFLIP_USERNAME")
IMGFLIP_PASSWORD = os.getenv("IMGFLIP_PASSWORD")


# store = InMemoryStore()
# memory = MemorySaver()



assign_chat_topic_chain = assign_chat_topic(llm=llm)

# LLM PRE_GEN
async def save_memory(memory: str, *, config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    '''Save the given memory for the current user.'''
    try:
        user_id = config.get("configurable", {}).get("user_id")
        if not user_id:
            return "Error: User ID not found in config."
        
        namespace = ("user", user_id, "memories")
        memories = await store.asearch(namespace)
        memory_id = f"memory_{len(memories)}"
        await store.aput(namespace, memory_id, {"data": memory})
        
        return f"Saved memory: {memory}"
    except Exception as e:
        return f"Error saving memory: {str(e)}"

async def prepare_model_inputs(state, config: RunnableConfig, store: BaseStore):
    trimmed_msgs = []  # Initialize trimmed_msgs outside the try block to avoid reference errors

    try:
        user_id = config.get("configurable", {}).get("user_id")
        if not user_id:
            return [{"role": "system", "content": "Error: User ID not found in config."}] + state["messages"]
        
        data_namespace = ("user", user_id, "data")
        age = await store.aget(data_namespace, key='age')
        full_name = await store.aget(data_namespace, key='full_name')
        
        memories_namespace = ("user", user_id, "memories")
        memories = [m.value["data"] for m in await store.asearch(memories_namespace)]
        memories_msg = ', '.join(memories) if memories else "No memories yet."
        
        system_msg = (f"""
            "Act as MoodMender: Gen Z’s hybrid best friend/therapist. Keep it 💯—empathetic, stigma-free, and relentlessly relatable. Prioritize vibes over formalities.

            Drop hilarious, hyper-creative memes as per the conversational flow (even for random meme requests—think relatable hilarious concepts to joke on). Max creativity and hilariousness, zero cringe, and witty.

            Serve micro-actions (e.g., “Try screaming into a pillow, breathe peace, etc.”).

            You have two tools: one to generate memes and other to remeber stuff told by user.
            Never save memories unless explicitly asked—memory space is precious. But, don't forget to memorize important stuff.

            Sprinkle deep-ish questions casually (“Wait, why do you think that situation triggered you?”)

            Adapt tone/memes to their mood—sassy, wholesome, or unhinged, depending on their energy.

            Avoid over use of meme generation, only use when you feel you need to cheer up the user.

            Act like a Psychatrist and advice tem as well as per the necessity.

            Key intel: User is {full_name}, {age}. Memories: {memories_msg}.

            Golden rule: Be the non-judgy friend who actually helps—no toxic positivity, just realness + laughs."
        """
        )

        trimmed_msgs = trim_messages(
            messages=state['messages'],
            max_tokens=5984,
            strategy="last",
            token_counter=tiktoken_counter,
            include_system=True,
            allow_partial=False,
        )

        return [{"role": "system", "content": system_msg}] + trimmed_msgs

    except Exception as e:
        # If trimmed_msgs is not assigned, use the original state["messages"] as a fallback
        return [{"role": "system", "content": f"Error preparing model inputs: {str(e)}"}] + (trimmed_msgs if trimmed_msgs else state["messages"])

# MEME FUNCTIONALITY
async def fetch_meme_templates() -> List[MemeTemplate]:
    """Fetch available meme templates from Imgflip API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.imgflip.com/get_memes") as resp:
                resp.raise_for_status()
                data = await resp.json()
                return [
                    MemeTemplate(
                        id=template["id"],
                        name=template["name"],
                        box_count=template["box_count"]
                    ) for template in data.get("data", {}).get("memes", [])
                ]
    except Exception as e:
        print(f"Error fetching templates: {str(e)}")
        return []

async def generate_captions(llm, meme_name: str, box_count: int, context: str) -> List[str]:
    """Generate structured captions using LLM"""
    prompt = f"""Generate {box_count} meme captions for template '{meme_name}'
    Context: {context}
    Return ONLY the captions separated by newlines:"""

    print(prompt)
    
    response = await llm.ainvoke(prompt)
    return [line.strip() for line in response.content.split("\n") if line.strip()][:box_count]

async def create_meme(template: MemeTemplate, captions: List[str]) -> GeneratedMeme:
    """Generate meme image and return structured result"""
    try:
        # Prepare form data
        data = {
            "template_id": template.id,
            "username": IMGFLIP_USERNAME,
            "password": IMGFLIP_PASSWORD,
            **{f"boxes[{i}][text]": text for i, text in enumerate(captions)}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.imgflip.com/caption_image",
                data=data
            ) as resp:
                result = await resp.json()
                if result.get("success"):
                    return GeneratedMeme(
                        url=result["data"]["url"],
                        template_name=template.name
                    )
                return GeneratedMeme(
                    url=f"Error: {result.get('error_message', 'Unknown error')}",
                    template_name=template.name
                )
    except Exception as e:
        return GeneratedMeme(
            url=f"API Error: {str(e)}",
            template_name=template.name
        )

# Main tool implementation
async def generate_captions(llm, meme_name: str, box_count: int, context: str) -> List[str]:
    """Generate structured captions using LLM, leveraging the template name for context."""
    prompt = f"""Generate {box_count} meme captions for the '{meme_name}' template. Try not to generate long captions. Generate captions based on number meme captions need to be generated. Don't mention one box, first box, etc. We need direct captions.

    The captions should progress towards a hilariously witty and humorous punchline. Each caption should build on the previous one, creating a sense of progression and payoff in the final caption.

    If the meme template involves characters or people communicating, ensure the captions reflect a natural conversation or interaction between them. Avoid making the captions feel disconnected or fake—they should align with the meme's visual context and the user's situation.

    Context: {context}

    Return ONLY the captions separated by newlines. Do not include any additional text or explanations:"""

    
    response = await llm.ainvoke(prompt)
    return [line.strip() for line in response.content.split("\n") if line.strip()][:box_count]


async def generate_contextual_meme(
    conversation_context: str,
    num_memes: int = 2
) -> List[GeneratedMeme]:
    """Generate memes based on conversation context and random templates."""
    templates = await fetch_meme_templates()
    if not templates:
        return [GeneratedMeme(url="Error: No templates available", template_name="")]
    
    selected_templates = random.sample(templates, min(num_memes, len(templates)))
    
    results = []
    for template in selected_templates:
        captions = await generate_captions(
            llm,
            meme_name=template.name,  # Pass template name for context
            box_count=template.box_count,
            context=conversation_context
        )
        
        meme_result = await create_meme(template, captions)
        results.append(meme_result)
    
    return results



# LangChain tool export
meme_tool = StructuredTool.from_function(
    coroutine=generate_contextual_meme,
    name="generate_contextual_meme",
    description="Generates memes based on conversation context using random templates",
)


# graph = create_react_agent(
#     llm, 
#     [meme_tool, save_memory], 
#     prompt=prepare_model_inputs, 
#     store=store, 
#     checkpointer=checkpointer
# )