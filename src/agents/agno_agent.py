from textwrap import dedent
from agno.agent import Agent
import os
from agno.models.meta import Llama
from agno.models.huggingface import HuggingFace
import agno.memory.v2 as mem
from agno.playground import Playground, serve_playground_app
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools
# from agents.instructions.tools_spec import tools_spec
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from tools.ecommerce import ecommerce
from mcptools import TelegramMCPConnector


import logging
logger = logging.getLogger()
from dotenv import load_dotenv
load_dotenv(override=True)

from agno.models.openrouter import OpenRouter
ossmodel=OpenRouter(id="meta-llama/llama-3.3-70b-instruct",
                    max_tokens=8000,
                    api_key=os.getenv('OPENROUTER_API_KEY'))

ossmodel2 = HuggingFace(
                    # id= "deepseek-ai/DeepSeek-R1-0528",
                    #  id="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
                       id="meta-llama/Llama-4-Scout-17B-16E",
                        # id="meta-llama/Llama-3.3-70B-Instruct",
                        # id="meta-llama/Llama-2-7b",
                       max_tokens=8000, 
                       temperature=0.7)

memory_manager = mem.MemoryManager(
    model=ossmodel,
    memory_capture_instructions=dedent("""
        Capture the:
        - Item names
        - Item prices
        - Item description
    """)
)

memory = mem.Memory(
    db=SqliteMemoryDb(
        table_name="memories", 
        db_file="data/memories.db"  
    ),
    model=ossmodel,
    summarizer=mem.SessionSummarizer(
        model=ossmodel,
        system_message="Retains information about the usefulness and prices of items"
    ),
    memory_manager=memory_manager,
)


def make_agent() -> Agent:

    try:
        return Agent(
                name="Limitus AI Agent",
                model=ossmodel,
                markdown=True,
                tools=[
                    ecommerce,
                    ReasoningTools(add_instructions=True),
                    ThinkingTools(add_instructions=True)
                ],
                show_tool_calls=True,
                add_state_in_messages=True,
                session_state={'items': {}},
                storage=SqliteAgentStorage(table_name="session_state", 
                                           db_file="data/session_state.db"),  # for session state
                debug_mode=False,
                add_datetime_to_instructions=True,

                instructions=[
                    """
                    You are a sales specialist, able to analyze a user's needs and decide the best items for his specified purpose.

                    # Core requirements:
                    - Make sure to review the tools definitions to understand how to use them, and the data they return
                    - Connect to the website and retrieve the list of items.
                    - Understand the user's needs and find the best tools adapted to his issue or endeavor
                    - Present the user with all the items first even if you must recommend the most appropriate ones, and then present your choices.
                    - Analyze the user query to determine the important aspects related to the items in the inventory to help make a choice, 
                        in particular the intended activity, location, occasion (holiday, office dinner etc). 
                    - If the user asks for a specific item, you must add it to the list of choices you have prepared.
                    - If the user says he doesn't want an item, you must remove it from your list of choices if you picked it. 
                    - Ask for more information if needed

                    # IMPORTANT
                        * Use the right number of appropriate items without overbuying 
                        * You must think of all the possible uses of an item, or what they are related to.  
                        For instance, a pedal is part of a bike and is relevant for someone who wants to bike.  
                        * Ask for permission to checkout the items.
                    """,
                    """
                    Present the user with a final output in markdown, with the purchased items, prices, and purchase proof if you retrieved it
                    """
                ],

                enable_agentic_memory=True,  # update memory during runs
                enable_user_memories=True,  # Agent stores user facts/preferences
                enable_session_summaries=True,  # Agent stores session summaries
                add_session_summary_references=True,  # Add session summary references to responses
                add_history_to_messages=True,  # Include chat history in model context
                read_chat_history=True,
                num_history_responses=10,  # Number of past runs to include in context
                expected_output=dedent(f"""Typical Answer 
                    here are the choices I propose:
                    - item1, price, description
                    - item2, price, description
                    Total: 120$
                    Should I order those articles? I will use your credit card number.  
                    
                    [After the payment:]
                    Show the <Confirmation>
                    """),
                memory=memory, # user memories (of past events)
                stream=True,
                telemetry=False
        )
    except Exception as e:
        logger.error(f'Error when retrieving the agent {e}')
        return

from dotenv import load_dotenv
load_dotenv(override=True)
limitus_agent = make_agent()
app = Playground(agents=[limitus_agent]).get_app(use_async=False)

if __name__ == "__main__":
    
    # cd agent-ui && npm run dev to start localhost:3000
    serve_playground_app("agno_agent:app", reload=True, port=7777) 