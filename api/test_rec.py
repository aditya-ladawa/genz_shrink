import os 

# typing_extensions
from typing_extensions import Union, Optional, TypedDict, Annotated

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

# dotenv
from dotenv import load_dotenv
load_dotenv()

# groq
from langchain_groq import ChatGroq

# STT

from RealtimeSTT import AudioToTextRecorder


llm = ChatGroq(model='llama-3.3-70b-versatile', temperature=0.5)



store = InMemoryStore()
memory = MemorySaver()



config = {"configurable": {"thread_id": "t1", "user_id": "u1"}}
user_id = config.get("configurable", {}).get("user_id")



store.put(('user', user_id, 'data'), key='age', value=23)
store.put(('user', user_id, 'data'), key='full_name', value='Aditya Ladawa')




def save_memory(memory: str, *, config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    '''Save the given memory for the current user.'''
    # This is a **tool** the model can use to save memories to storage
    user_id = config.get("configurable", {}).get("user_id")
    namespace = ("user", user_id, "memories")
    
    # Save the memory under the user's memories namespace
    memory_id = f"memory_{len(store.search(namespace))}"
    store.put(namespace, memory_id, {"data": memory})
    
    return f"Saved memory: {memory}"

def prepare_model_inputs(state, config: RunnableConfig, store: BaseStore):
    # Retrieve user data and memories, then add them to the system message
    # This function is called **every time** the model is prompted. It converts the state to a prompt
    user_id = config.get("configurable", {}).get("user_id")
    
    # Retrieve user data (age and name)
    data_namespace = ("user", user_id, "data")
    age = store.get(data_namespace, key='age')
    full_name = store.get(data_namespace, key='full_name')
    
    # Retrieve user memories
    memories_namespace = ("user", user_id, "memories")
    memories = [m.value["data"] for m in store.search(memories_namespace)]
    memories_msg = ', '.join(memories) if memories else "No memories yet."
    
    # Prepare the system message with user data and memories
    system_msg = (
        "You are MoodMender, a friendly, meme-savvy AI who acts as both a best friend and a non-judgmental 'shrink' for Gen Z users. You won't need memes for every message. You should decide when to provide memes as per the flow of conversation. You should alo reply in concise manner."
        "Your tone is empathetic, relatable, and stigma-free—like a close friend who’s always there to listen and cheer them up. "
        "Use humor, memes, and Gen Z lingo to make conversations engaging. Offer micro-actions (e.g., breathing exercises, funny videos) to help users feel better. "
        "Remember important details shared by the user only when the user explicitly asks for them to be remembered. Not every detail from a conversation needs to be saved, else the memory space will run out."
        "Ask thoughtful, cross-questions to dig deeper into their feelings and experiences, but keep it casual. "
        "Adapt your tone and memes based on the user's mood and preferences. "
        f"The user's full name is {full_name}, and they are {age} years old. Here are the memories related to this user: {memories_msg}"
    )
    
    # Return the structured prompt
    return [{"role": "system", "content": system_msg}] + state["messages"]


graph = create_react_agent(llm, [save_memory], prompt=prepare_model_inputs, store=store, checkpointer=MemorySaver())



recorder = AudioToTextRecorder()
recorder.start()
input("Press Enter to stop recording...\n")  # Wait for user input to stop recording

recorder.stop()
transcribed_text = recorder.text()
print("Transcription: ", transcribed_text, '\n')
recorder.shutdown()


for s in graph.stream({"messages": [("user", transcribed_text)]}, config=config, stream_mode='values'):
  print(s['messages'][-1].content)

