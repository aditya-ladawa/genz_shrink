from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing_extensions import List, Optional, Union, TypedDict, Literal, Dict, Literal, Annotated
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import trim_messages
from langchain.schema import SystemMessage, HumanMessage, AIMessage


class LabelConvo(TypedDict):
  label: str

def assign_chat_topic(llm):

    template = """
        "You are an expert in assigning concise topics to conversations.  "
        "You should assign a relevant topic in 5 words or less. "
        "Here is the initial input message:\n\n"
        f"{msg}\n\n"
        "What is the best topic for this conversation? Provide only the topic without any extra text."
    """

    structured_output_llm = llm.with_structured_output(LabelConvo)

    prompt_template = ChatPromptTemplate.from_template(template=template)

    assign_chat_topic_chain = prompt_template | structured_output_llm | (lambda x: x["label"])

    return assign_chat_topic_chain