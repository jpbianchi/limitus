"""🏠 MCP Airbnb Agent - Search for Airbnb listings!

This example shows how to create an agent that uses MCP and Gemini 2.5 Pro to search for Airbnb listings.

Run: `pip install google-genai mcp agno` to install the dependencies
"""

import os
import asyncio
import nest_asyncio
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.mcp import MCPTools
from agno.utils.pprint import apprint_run_response
from agno.playground import Playground, serve_playground_app
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools
from agno.models.openrouter import OpenRouter
from tools.ecommerce import ecommerce

import logging

if os.getenv('ENVIRONMENT') is None:
    from dotenv import load_dotenv
    load_dotenv(override=True)

# Allow nested event loops (due to vscode)
nest_asyncio.apply()

logger = logging.getLogger()

ossmodel = OpenRouter(
                    # id="meta-llama/llama-3.3-70b-instruct",
                    id="openai/gpt-4.1-nano",
                    max_tokens=10000,
                    api_key=os.getenv('OPENROUTER_API_KEY'))

instructions = [""" Post everything the user writes to the Discord channel, dot NOT answer it, and provide a status message after doing it """]
expected_output = """ a status message about the post to Discord"""

discord_mcp_tool = MCPTools(
        # "npx -y @openbnb/mcp-server-airbnb --ignore-robots-txt",
        # "",
        "node src/agents/discordmcp/build/index.js",
        env={"DISCORD_TOKEN": os.environ["DISCORD_BOT_TOKEN"]},
        timeout_seconds=20)

async def make_agent(message: str = "") -> None:
   async with discord_mcp_tool as mcp_tool:
        agent = Agent(
            name="MCP discord",
            model=ossmodel,
            tools=[
                mcp_tool
                #    , ThinkingTools(add_instructions=True)
                ],
            instructions=instructions,
            markdown=True,

            show_tool_calls=False,

        )
            # playground = Playground(agents=[agent])
            # app = playground.get_app()
            # playground.serve(app)
                
        response_stream = await agent.arun(message, stream=True)
        await apprint_run_response(response_stream, markdown=True)


# limitus_agent = await make_agent()
# # # agents = [asyncio.run(make_agent())]  if several agents
# app = Playground(agents=[limitus_agent]).get_app(use_async=False)

if __name__ == "__main__":
    # serve_playground_app("airbnbmcp:app", reload=True, port=7777)
    # asyncio.run(make_agent())
    asyncio.run(
        make_agent(
            # "What listings are available in San Francisco for 2 people for 3 nights from 1 to 4 August 2025?"
            "Say 'hello2' to the discord channel"
        )
    )
    # async def xx():        
    #     await serve_playground_app("airbnbmcp:app", reload=True, port=7777) 
    # asyncio.run(xx())