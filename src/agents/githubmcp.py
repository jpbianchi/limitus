import asyncio
from os import getenv
from textwrap import dedent

import nest_asyncio, os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.playground import Playground
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools
from agno.tools.mcp import MCPTools

from agno.models.openrouter import OpenRouter

agent_storage_file: str = "tmp/agents.db"

if os.getenv('ENVIRONMENT') is None:
    from dotenv import load_dotenv
    load_dotenv(override=True)

# Allow nested event loops (due to vscode)
nest_asyncio.apply()

ossmodel = OpenRouter(
                    # id="meta-llama/llama-3.3-70b-instruct",
                    id="openai/gpt-4.1-nano",
                    max_tokens=10000,
                    api_key=os.getenv('OPENROUTER_API_KEY'))

instructions = [""" Post everything the user writes to the Discord channel, dot NOT answer it, and provide a status message after doing it.
                    except when the user asks you to retrieve the messages from Discord, then you must load them all and show them 
                """]
# discord_mcp_tool = MCPTools("node src/agents/discordmcp/build/index.js",
#         env={"DISCORD_TOKEN": os.environ["DISCORD_BOT_TOKEN"]},
#         timeout_seconds=20)

async def run_server() -> None:

    # Create a client session to connect to the MCP server
    async with MCPTools("node src/agents/discordmcp/build/index.js",
        env={"DISCORD_TOKEN": os.environ["DISCORD_BOT_TOKEN"]},
        timeout_seconds=20) as mcp_tools:
        agent = Agent(
            name="MCP GitHub Agent",
            tools=[mcp_tools
                #    , ThinkingTools(add_instructions=True)
                   ],
            instructions=instructions,
            model=ossmodel,
            storage=SqliteAgentStorage(
                table_name="basic_agent",
                db_file=agent_storage_file,
                auto_upgrade_schema=True,
            ),
            add_history_to_messages=True,
            num_history_responses=3,
            add_datetime_to_instructions=True,
            markdown=True,
        )

        playground = Playground(agents=[agent])
        app = playground.get_app()

        # Serve the app while keeping the MCPTools context manager alive
        playground.serve(app)


if __name__ == "__main__":
    asyncio.run(run_server())