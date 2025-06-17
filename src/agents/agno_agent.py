from textwrap import dedent
import os
import random
import asyncio
import nest_asyncio
import string
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
from tools.ecommerce import EcommerceToolkit
from agno.utils.log import logger

if os.getenv('ENVIRONMENT') is None:
    from dotenv import load_dotenv
    load_dotenv(override=True)


def random_id():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(6))


# Allow nested event loops (due to vscode)
nest_asyncio.apply()

ossmodel = OpenRouter(
                    # id="meta-llama/llama-3.3-70b-instruct",     # not good for MCP
                    id="deepseek/deepseek-r1-distill-llama-70b", # ok for MCP
                    # id="deepseek/deepseek-r1-distill-qwen-32b", # not good for MCP
                    # id="deepseek/deepseek-r1-0528:free",          # not good for MCP
                    # id="deepseek/deepseek-r1",  # ok for MCP
                    # id="qwen/qwen3-235b-a22b",   # ok for MCP
                    # id="openai/gpt-4.1-nano",
                    max_tokens=10000,
                    api_key=os.getenv('OPENROUTER_API_KEY')) 

# HuggingFace models failed one way or another (prob because of tools)
ossmodel2 = HuggingFace(
                      # id= "deepseek-ai/DeepSeek-R1-0528",
                      #  id="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
                      id="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
                    #    id="meta-llama/Llama-4-Scout-17B-16E",
                        # id="meta-llama/Llama-3.3-70B-Instruct",
                        # id="meta-llama/Llama-2-7b",
                       max_tokens=8000, 
                       temperature=0.7)

# I could have used the session_state to save the items
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
        system_message="Retains information about the items in the inventory"
    ),
    memory_manager=memory_manager,
)

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

# this post is better laid out but proves difficult for a small model
instructions2 = [
    """
    # ROLE & OBJECTIVE
    You are an AI shopping assistant for an online store. 
    Your job is to quickly fulfill user requests for items, either given directly or found in their recent Discord posts, and immediately purchase two matching items for them.

    # GENERAL BEHAVIOR
    - Always use markdown formatting in your answers.
    - Never mention or recommend items not found in the inventory.
    - Never ask for a credit card number; payment is handled automatically.
    - Always display the price and description of every item you purchase.

    # TOOL INSTRUCTION COMPLIANCE
    - Many tools may return special 'instructions' in their output.
    - Whenever a tool returns instructions, you MUST carefully read and strictly obey them.
    - These instructions may affect the next steps you take, what information you provide, or how you interact with the user or other tools.
    - If a tool's instructions conflict with your default workflow, always follow the tool's instructions.

    # DISCORD INTEGRATION
    - If the user asks you to check instructions or requests on Discord, do the following:
        1. Use the MCP tool 'read-messages' to read the last 3 posts from the 'general' channel.
        2. Check if any of these posts contain a request for items or shopping instructions.
        3. If a request is found, output it to show the user you have successfully retrieved it.
        4. Then treat the instruction found on discord as if directly given by the user and process it immediately using the tools.
        5. If no relevant request is found, inform the user and ask for clarification or a direct request.

    # STEP-BY-STEP WORKFLOW

    1. **Retrieve Inventory**
       - Always start with using 'retrieve_items_in_inventory' to get the latest list of available items.

    2. **Understand User Needs**
       - If the user asked for Discord instructions, use the most recent relevant request from Discord in the last 3 posts.
       - Otherwise, use the user's direct message.
       - Analyze the request for their intended activity, purpose, location, or occasion (e.g., beach, office, holiday).
       - Do NOT make recommendations at this stage.  
       - Recommendations can only be done after calling the retrieve_items_in_inventory tool.
       
    3. **Select and Purchase Items**
       - Use the retrieve_items_in_inventory tool to retrieve the inventory, and then ick at most two items from the inventory that best match the user's request.
       - Show those items to the user before sending them to the cart.
       - Explain in one sentence why those items fit user's needs.
       - Do not ask for permission from the user, instead add these items to the cart using 'put_items_in_cart'.

    4. **Present Purchase Confirmation**
       - After checkout, display the purchase confirmation and the items bought.

    # IMPORTANT RULES
    - Do not ask the user for a credit card number, this is a demo that doesn't need it.
    - If the website window closes after a purchase, you must log in again for any further actions.
    - For orders, use default names and postal code unless the user provides their own.
    - Always use the tools as described; do not simulate their behavior.
    
    # MEMORY USAGE
    - Use memories from previous interactions to personalize recommendations, but always prioritize new information from the current conversation.
    - !!!After a purchase is complete, forget everything except the inventory in case the user wants to place a new order.!!!

    # IF USER REQUEST IS NOT ABOUT SHOPPING
    - If the user's question is not related to shopping or the inventory, respond helpfully without using any tools.

    # END OF INSTRUCTIONS
    """
]

# this prompt goes to the core requirements and steps, and works better
instructions = [# For 'non GPT4' models, I had to 'help' the model for MCP by showing the tools to use
                    """                
                        - If the user asks to post something on the discord server, do it on the general channel and do NOT process the message
                        - To send a message, use the MCP tool send-message(channel=general, message=<message>)
                        - If the user asks to read posts from the discord server, do it on the general channel and DO process the messages just like any message entered by the user
                        - To read n messages, use the MCP tool read-messages(channel=general, limit=n)
                        - It is very important you respect these two messages format for Discord or someone is going to get hurt badly!
                    """,
                    """
                    You are a sales specialist, able to analyze a user's needs and decide the best items for his specified purpose.

                    # STEPS:
                    - If the user mentions Discord, you must read the last message on the 'general' channel and use it as the query you must answer.
                    - Save the query in your memory, just like you would for an instruction given directly.
                    - Examine the query to determine the important aspects related to the items in the inventory to recommend 2 items, 
                        in particular the intended activity, location, occasion (holiday, office dinner etc). 
                    - Retrieve the list of items in the inventory using the tools and recommend 2 items to satisfy the user.
                    - Put the recommended items in the cart without asking for permission, this is a just demo without real purchases.
                    - NEVER mention a credit card since this is a demo and it's not needed.
                    - Do not wait for the user after you've generated recommendations, instead display the items for the user to see and put the items straight into the cart.  
                    - When you receive a payment confirmation, your job is done.

                    # IMPORTANT
                        * You must think of all the possible uses of an item or what they are related to. 
                        For instance, a pedal is part of a bike and is relevant for someone who wants to bike. 
                        * Read and obey the 'instructions' in the data returned by the tools

                    """,
                    """
                    Present the user with a final output in markdown, with the purchased items, prices, and purchase proof if you retrieved it
                    """
                ]


expected_output = """Typical Answer 
                    here are the choices I recommend:
                    - item1, price: 
                      description \n
                    - item2, price: 
                      description \n
                    Total: 120$
                    Should I order those articles? I will use your credit card number.  
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
                use_json_mode=False,
                user_id=random_id(),    # avoid using memory from previous session
                session_id=random_id(), # avoid using memory from previous user
                tools=[
                    EcommerceToolkit(),
                    mcp_tools,
                    # ReasoningTools(add_instructions=True),
                    ThinkingTools(add_instructions=True)
                ],
                show_tool_calls=True,

                debug_mode=True,
                add_datetime_to_instructions=True,

                instructions=instructions,
                expected_output=expected_output,
                add_state_in_messages=True,
                session_state={'items': {}},
                storage=SqliteAgentStorage(table_name="session_state", 
                                           db_file="data/session_state.db",
                                           auto_upgrade_schema=True,),  # for session state (not used here)
                memory=memory,   # user memories (of past events)
                # Enable the agent to manage memories of the user
                enable_agentic_memory=True,
                # # If True, the agent creates/updates user memories at the end of runs
                enable_user_memories=True, 
                # If True, the agent adds a reference to the user memories in the response
                add_memory_references=True,
                # # If True, the agent creates/updates session summaries at the end of runs
                enable_session_summaries=False,
                # If True, the agent adds a reference to the session summaries in the response
                add_session_summary_references=True,
                read_chat_history=True,
                num_history_responses=10,  # Number of past runs to include in context
                stream=False,
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

