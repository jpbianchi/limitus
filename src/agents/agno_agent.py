from textwrap import dedent
import os
import asyncio
import nest_asyncio
from agno.agent import Agent
from agno.models.meta import Llama
from agno.models.huggingface import HuggingFace
import agno.memory.v2 as mem
from agno.playground import Playground, serve_playground_app
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools
from agno.tools.mcp import MCPTools
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.models.openrouter import OpenRouter
from tools.ecommerce import ecommerce

if os.getenv('ENVIRONMENT') is None:
    from dotenv import load_dotenv
    load_dotenv(override=True)

# Allow nested event loops (due to vscode)
nest_asyncio.apply()

ossmodel = OpenRouter(
                    # id="meta-llama/llama-3.3-70b-instruct",     # not good for MCP
                    # id="deepseek/deepseek-r1-distill-llama-70b", # ok for MCP
                    # id="deepseek/deepseek-r1-distill-qwen-32b", # not good for MCP
                    # id="deepseek/deepseek-r1-0528:free",          # not good for MCP
                    id="deepseek/deepseek-r1",  # ok for MCP
                    # id="qwen/qwen3-235b-a22b",   # ok for MCP
                    # id="openai/gpt-4.1-nano",
                    max_tokens=10000,
                    api_key=os.getenv('OPENROUTER_API_KEY')) 

# HuggingFace models all failed for some reason
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

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

instructions = [    # For 'non GPT4' models, I had to 'help' the model for MCP by giving the tools to use
                    dedent("""                
                        - If the user asks to post something on the discord server, do it on the general channel and do NOT process the message
                        - To send a message, use the MCP tool send-message(channel=general, message=<message>)
                        - If the user asks to read posts from the discord server, do it on the general channel and DO process the message just like any message entered by the user
                        - To read n messages, use the MCP tool read-messages(channel=general, limit=n)
                        - It is very important you respect these two messages format for Discord or someone is going to get hurt badly!
                    """),
                    dedent("""
                    You are a sales specialist, able to analyze a user's needs and recommend the best items for his specified purpose.
                    The user may give you his request directly or in a post on discord.  

                    # Core requirements:
                    - If a user asks you to retrieve his instructions on discord, read the last post on Discord and treat is as if it was given directly.
                    - Otherwise, process his request without caring about Discord and use the ecommerce tools
                    - Review the tools descriptions to understand how to use them, and the data they return
                    - At the beginning of a conversation, ALWAYS connect to the website using the tool and retrieve the list of items.
                    - Understand the user's needs and find the best items adapted to his issue or endeavor
                    - Present the user with all the items you recommend, with the price, and the description on the next line

                    - Understand the user message to determine the relevant aspects to recommend items from the inventory, 
                        in particular the intended activity, location, occasion (holiday, office dinner etc). 

                    - If the question is not about the items in the website, just reply normally, without using tools.

                    # STEPS:
                    - retrieve the items list from the website (never from the web) and show them to the user
                    - understand the user question to find out which items correspond to his wishes (e.g. running shoes if he likes to run)
                    - If the user asks for a specific item, you must add it to the list of choices you have prepared.
                    - If the user says he doesn't want an item, you must remove it from your list of recommendations. 
                    - Automatically order the recommended items without asking the user.
                    - Present the user with the proof of purchase if the website returned it.
                    - Then post a summary of the purchase on the 'general' discord channel using the MCP tool if it's available

                    # IMPORTANT
                        * You can ONLY mention items that were retrieved from the website, not some item you found on the web
                        * NEVER retrieve items from your memory - ALWAYS use the tools provided
                        * Always show the price of every item 
                        * For your recommendation, you must think of all the possible uses of an item.  
                        * For the order, use the default names, zip code etc.
                    """)
                ]

expected_output = f"""Typical Answer 
                    here are the choices I recommend:
                    - item1, price: 
                      description \n
                    - item2, price: 
                      description \n
                    Total: 120$
                    Should I order those articles? I will use your credit card number.  
                    
                    [After the payment:]
                    \n
                    Show the <Confirmation>
                    """
                    

# many mcp servers at https://github.com/modelcontextprotocol/servers
discord_mcp_tool = MCPTools(
        "node src/agents/discordmcp/build/index.js",
        # create a bot on discord, get the token, then allow the bot to manage a server
        env={"DISCORD_TOKEN": os.environ["DISCORD_BOT_TOKEN"]},
        timeout_seconds=20)

async def make_agent() -> Agent:
    try:
        async with MCPTools("node src/agents/discordmcp/build/index.js", 
                            env={"DISCORD_TOKEN": os.environ["DISCORD_BOT_TOKEN"]}, 
                            timeout_seconds=30) as mcp_tools:
            agent1 = Agent(
                name="Limitus AI Agent",
                model=ossmodel,
                markdown=True,
                tools=[
                    ecommerce,
                    mcp_tools,
                    ReasoningTools(add_instructions=True),
                    # ThinkingTools(add_instructions=True)
                ],
                show_tool_calls=False,

                debug_mode=False,
                add_datetime_to_instructions=True,

                instructions=instructions,
                expected_output=expected_output,
                add_state_in_messages=True,
                session_state={'items': {}},
                storage=SqliteAgentStorage(table_name="session_state", 
                                           db_file="data/session_state.db",
                                           auto_upgrade_schema=True,),  # for session state
                enable_agentic_memory=True,  # update memory after each run
                enable_user_memories=True,  # user facts/preferences are saved
                enable_session_summaries=True,  # session summaries are saved
                add_session_summary_references=False,  # add session summary references to responses
                add_history_to_messages=True,  # include chat history in model context
                read_chat_history=True,
                num_history_responses=5,  # Number of past runs to include in context
                memory=memory,   # user memories (of past events)
                stream=True,
                telemetry=False
            )

            playground = Playground(agents=[agent1])
            app = playground.get_app()
            playground.serve(app)

    except Exception as e:
        logger.error(f'Error when retrieving the agent {e}')
        return

# limitus_agent = make_agent()
# # # agents = [asyncio.run(make_agent())]  if several agents
# app = Playground(agents=[limitus_agent]).get_app(use_async=False)

if __name__ == "__main__":
    asyncio.run(make_agent())
    
    # cd agent-ui && npm run dev to start localhost:3000
    # serve_playground_app("agno_agent:app", reload=True, port=7777)
