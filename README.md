<p align="center">
  <img src="data/logos/great_logo.png" width="600px"/>
</p>

## Limitus Agents

#### Description
I created an agent that can purchase items on a ecommerce website (with a limited number of items).
The items are selected after analysing the user's question or description of what he intends to do.
The agent replies to any question non related to the items as a Llama 3.3 70B model (also used by the agent).
The agent can also read the last post in a Discord server `JPB server` and proces it as it it were installed 

Warning: 
- sometimes the agent releases the text box after several seconds, so one must wait.  
It shouldn't happen but I've caught the agent pulling items from its memory, in which case specify it must check the website.  Or start a new chat, which will generate a new session.
- During the inventory reading, the browser may warn about the password being hacked (it's a unique password for everyone since it's a demo site).
Please close the pop up.
- CLOSE THE SECOND CHROME WINDOW???

#### Install the dependencies with UV
[install uv](https://docs.astral.sh/uv/getting-started/installation/)

Steps to install the agents
- run `uv sync` to create the .venv
-  `source .venv/bin/activate`
-  `cd src/agents/discordmcp`
-  `npm isntall`
-  `npm run build`
-  `cd ../../..`
-  
To create the Agent UI ([link](https://docs.agno.com/agent-ui/introduction)):
-  `npx create-agent-ui@latest`
-  `cd agent-ui`
-  `npm run dev` (starts agent frontend Agno at localhost:3000)
However, this part can be skipped by using the link provided when the endpoint 
starts (begins with https://app.agno.com/playground?endpoint=....)

To start the agent endpoint @ localhost:7777

GIVE A SCRIPT, LOAD ENV FILE

- make session_state work


#### Demo & Video


