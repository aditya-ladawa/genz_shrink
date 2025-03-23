# llm chains
from .llm_chains import *

import os 
import aiohttp
import random
from urllib.parse import urlencode

# typing_extensions
from typing_extensions import Union, Optional, TypedDict, Annotated, List

# checkpointer and store
from langgraph.prebuilt import InjectedStore, InjectedState
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt.chat_agent_executor import AgentState


# langgraph
from langgraph.prebuilt import create_react_agent


# langchain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_core.tools import InjectedToolArg
from langchain_core.tools import tool
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

# token_counter
from .token_counter import tiktoken_counter

# llm = ChatGroq(model='llama-3.3-70b-versatile', temperature=0.6)
llm = ChatGroq(model='llama-3.2-90b-vision-preview', temperature=0.2)


# Environment variables for credentials
IMGFLIP_USERNAME = os.getenv("IMGFLIP_USERNAME")
IMGFLIP_PASSWORD = os.getenv("IMGFLIP_PASSWORD")


# store = InMemoryStore()
# memory = MemorySaver()



assign_chat_topic_chain = assign_chat_topic(llm=llm)

class State(AgentState):
    docs: List[str]

# LLM PRE_GEN
async def save_memory(memory: str, *, config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    '''Save the given memory for the current user and conversation.'''
    try:
        user_id = config.get("configurable", {}).get("user_id")
        conversation_id = config.get("configurable", {}).get("thread_id")  # Assuming thread_id is the conversationId
        if not user_id or not conversation_id:
            return "Error: User ID or Conversation ID not found in config."
        
        # Include conversation_id in the namespace
        namespace = ("user", user_id, "conversation", conversation_id, "memories")
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
        conversation_id = config.get("configurable", {}).get("thread_id")  # Assuming thread_id is the conversationId
        if not user_id or not conversation_id:
            return [{"role": "system", "content": "Error: User ID or Conversation ID not found in config."}] + state["messages"]
        
        data_namespace = ("user", user_id, "data")
        age = await store.aget(data_namespace, key='age')
        full_name = await store.aget(data_namespace, key='full_name')
        
        # Include conversation_id in the namespace for memories
        memories_namespace = ("user", user_id, "conversation", conversation_id, "memories")
        memories = [m.value["data"] for m in await store.asearch(memories_namespace)]
        memories_msg = ', '.join(memories) if memories else "No memories yet."
        
        system_msg = (f"""
            Act as MoodMender: Gen Z’s hybrid best friend/therapist. Keep it 💯—empathetic, stigma-free, and relentlessly relatable. Prioritize vibes over formalities.

            Drop hilarious, hyper-creative memes based on the flow of conversation (even for random meme requests—think wildly relatable and witty concepts). Max creativity and incredible humor, zero cringe.

            Offer micro-actions when needed(e.g., “Scream into a pillow, then breathe peace,” “Take a dance break,” etc.).

            You have two tools: 
            1. meme_tool - for generating memes.
            2. save_memory - for remembering user-shared info (use only when explicitly requested or when you think the information given by user is important; memory space is precious).

            Casually sprinkle deep-ish questions (“Wait, why do you think that situation triggered you?”).

            Adapt your tone/memes to their mood—sassy, wholesome, or unhinged, depending on their energy.

            Use meme generation thoughtfully and purposefully. For instance, generate memes to cheer up the user or add humor to the conversation. But don't try to overwhelm the user with memes.

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
    prompt = f"""
        Generate {box_count} meme captions for the '{meme_name}' template. Keep them short and punchy. More meme captions needed then shorter captions the better.

        Ensure captions build up towards a hilariously witty punchline. Each caption should flow naturally into the next, creating progression and comedic payoff.

        If the meme template involves different charachter dialogues, make sure it feels like a natural, funny exchange rather than disjointed phrases. No need to mention charachter names in meme captions.

        Context: {context}

        Return ONLY the captions, each on a new line. No extra explanations or formatting.
    """

    print(context)
    
    response = await llm.ainvoke(prompt)
    return [line.strip() for line in response.content.split("\n") if line.strip()][:box_count]

@tool
async def generate_contextual_meme(
    state: Annotated[dict, InjectedState],
    num_memes: int = 2
) -> List[GeneratedMeme]:
    """Generate memes based on conversation context and random templates."""
    templates = await fetch_meme_templates()
    if not templates:
        return [GeneratedMeme(url="Error: No templates available", template_name="")]
    
    selected_templates = random.sample(templates, min(1, num_memes))
    
    results = []

    class ConversationContext(TypedDict):
        conversation_context: str

    context_gen_prompt = '''
    You will generate conversation context.
    The conversation_context should be derived from the most recent messages and crafted into a humorous, cohesive plot. This plot will serve as the foundation for generating meme captions, ensuring the memes are contextually relevant and funny. You will only focus on creating this humorous narrative rather than generating captions directly. It should at atleast 5 but at most 12 words.

    Examples of how the conversation_context might look like: 'data scientist fallen in love', 'toxic realtionship', 'leg day vs. other days', 'being always perectly wrong', etc.
    '''
    structured_output_llm = llm.with_structured_output(ConversationContext)

    trimmed_recent_msgs = trim_messages(
        messages=state['messages'][-9:],
        max_tokens=5984,
        strategy="last",
        token_counter=tiktoken_counter,
        include_system=True,
        allow_partial=False,
    )

    humour_plot = await structured_output_llm.ainvoke((f'''{context_gen_prompt}\n{trimmed_recent_msgs}'''))

    for template in selected_templates:
        captions = await generate_captions(
            llm,
            meme_name=template.name,
            box_count=template.box_count,
            context=humour_plot
        )
        
        meme_result = await create_meme(template, captions)
        results.append(meme_result)
    
    return results



# # LangChain tool export
# meme_tool = StructuredTool.from_function(
#     coroutine=generate_contextual_meme,
#     name="generate_contextual_meme",
#     description="Generates memes based on conversation context using random templates",
# )

# graph = create_react_agent(
#     llm, 
#     [meme_tool, save_memory], 
#     prompt=prepare_model_inputs, 
#     store=store, 
#     checkpointer=checkpointer
# )