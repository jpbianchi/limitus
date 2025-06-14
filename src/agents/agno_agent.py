from textwrap import dedent
from agno.agent import Agent
from agno.storage.json import JsonStorage
from agno.models.meta import Llama
from agno.models.huggingface import HuggingFace
import agno.memory.v2 as mem
from agno.playground import Playground, serve_playground_app
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools
# from agents.instructions.tools_spec import tools_spec
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agents.tools.ecommerce import ecommerce
from logging import logger
from agents.tools.hooks import hook

ossmodel = HuggingFace(id="Llama-4-Maverick-17B-128E-Instruct-FP8",
                       max_tokens=4096,
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
                session_state={'items': {}}
                storage=SqliteAgentStorage(table_name="session_state", dir_path="tmp/agno_sessions_json"),  # for session state
                debug_mode=False,
                add_datetime_to_instructions=True,

                instructions=[
                    """
                    Connect to the website and retrieve the list of items.
                    """,
                    dedent("""
                    You are a sales specialist, able to analyze a user's needs and decide the best items for his specified purpose.

                    # Core requirements:
                    - Make sure to review the tools definitions to understand how to use them, and the data they return
                    - Understand the user's needs and find the best tools adapted to his issue or endeavor
                    - Present the user with all the options even if you must recommend the most appropriate ones

                    # IMPORTANT
                        * Use the right items without overbuying 
                    """),
                    """
                    Present the user with a final output, with the items boughts, prices, and purchase proof if you retrieved it
                    """
                ],
                memory=mem.Memory(memory), # user memories (of past events)
                enable_agentic_memory=True,  # update memory during runs
                enable_user_memories=True,  # Agent stores user facts/preferences
                enable_session_summaries=True,  # Agent stores session summaries
                add_session_summary_references=True,  # Add session summary references to responses
                add_history_to_messages=True,  # Include chat history in model context
                read_chat_history=True,
                num_history_responses=10,  # Number of past runs to include in context
                # expected_output=dedent(f"""Typical Answer  """),
                
                markdown=True,
                stream=True,
                telemetry=False
        )
    except Exception as e:
        logger.error(f'Error when retrieving the agent {e}')
        return


limitus_agent = make_agent()
app = Playground(agents=[limitus_agent]).get_app()

if __name__ == "__main__":
    # cd agent-ui && npm run dev   to start localhost:3000
    serve_playground_app("agents.agno_agent:app", reload=True, port=7777)