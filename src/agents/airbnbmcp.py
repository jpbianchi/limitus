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

async def run_agent(message: str) -> None:
    async with MCPTools(
        # "npx -y @openbnb/mcp-server-airbnb --ignore-robots-txt",
        "",
        "node src/agents/discordmcp/build/index.js",
        env={"DISCORD_TOKEN": os.environ["DISCORD_BOT_TOKEN"]},
        timeout_seconds=20
    ) as mcp_tools:
        agent = Agent(
            model=ossmodel,
            tools=[mcp_tools],
            markdown=True,
        )

        response_stream = await agent.arun(message, stream=True)
        await apprint_run_response(response_stream, markdown=True)


if __name__ == "__main__":
    asyncio.run(
        run_agent(
            # "What listings are available in San Francisco for 2 people for 3 nights from 1 to 4 August 2025?"
            "Say 'hello' to the discord channel"
        )
    )