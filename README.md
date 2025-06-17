<p align="center">
  <img src="data/logos/great_logo.png" width="600px"/>
</p>

## Limitus Agents

#### Description
I created an agent that can purchase items on a ecommerce website (with a limited number of items).
The items are selected by an agent after analysing the user's question or description of what he intends to do or wants.

The agent replies to any question non related to the items as a `deepseek-r1-distill-llama-70b` accessed through `https://openrouter.ai`.  It was clearly powerful enough to understand the user's question and analyze the items in the inventory to pick the relevant ones.  

It is based on the Agno framework in which I have defined a Toolkit, ie several tools that open the webpage of a mock ecommerce site (no payments, but everything else is identical), retrieve the inventory, selects 2 items relevant to the user's needs, then puts them in the cart, check out and place the order (using the name but no credit card).

The agent can also read the last post from a Discord server `JPB server` using a MCP client, and process it as an instruction like in the previous case.  It communicates through a MCP server, which connects to the bot of a newly created Discord server (I can send an invite to the examiner).  To test this feature, you will need the bot's token which I can't put on github.  

Warning: 
- During the inventory reading, the browser may warn about the password being hacked (it's a unique password for everyone since it's a demo site).  It shouldn't happen with a commercial site where one can pick his password. Please close the pop up manually.


#### Install the dependencies with UV
[install uv](https://docs.astral.sh/uv/getting-started/installation/)

A `.env_template` template has been provided, to be filled with your Openrouter key.  

Steps to install the agents
- run `uv sync` to create the .venv
-  `source .venv/bin/activate`
-  `cd src/agents/discordmcp`
-  `npm install`
-  `npm run build`
-  `cd ../../..`


#### How to run the app

To create the Agent UI endpoint at port 3000, see ([link](https://docs.agno.com/agent-ui/introduction)).

Basically, do the following:
-  `npx create-agent-ui@latest`
-  `cd agent-ui`
-  `npm run dev` (starts agent frontend Agno at [localhost:3000](http://localhost:3000))
  
However, this part can be skipped by using the link provided when the endpoint starts (https://app.agno.com/playground?endpoint=....) but you will need to create a key from Agno.  

Otherwise, to start the agent endpoint, open `localhost:7777` in your browser, and you will get Agno agent frontend.

Use this script `start.agent.sh` to start the endpoint which will load the .env file as well. 


#### Demo & Video
[DEMO1 - purchase from agent frontend](https://drive.google.com/file/d/1AKbAo98LTPrXOp7NN_NDtP__fYHQpfeV/view?usp=sharing)
This demo shows how a user can input a description of what he needs or intends to do, and the Agent will retrieve the inventory from a mock ecommerce website, then select 2 relevant items, then proceed to put them in the cart and pay.  

[DEMO2 - purchase from a Discord post](https://drive.google.com/file/d/1jCMeNowHxcQGu0uniaCxVidzh-NvqHPq/view?usp=sharing)
This is the same except the agent must read a post from a Discord server I created (handled by a bot) so it can retrieve the instructions using a MCP client.

#### Final observations & Improvements

It was not easy to make an agent with a small OSS model such as the distilled Llama 3.3 70B model that I used.
I had to reduce the size of the prompt, simplify it to finally make it work, otherwise it would, at times, forget to call a tool for instance (even it just said that was its next step).  

I tried with HuggingFaceHub, but the models were failing for a reason or another, which is probably due to the use of tools.  I had to use OpenRouter which wraps the models to allows tools use.  But even so, some models can't deal with MCP for some reason (see the comments in the code).

I have implemented a basic purchase sequence (select - put in cart - checkout).  I could have gone back to the inventory page to allow further purchases, but managing such things with Selenium is not quite my thing and didn't seem to be part of the requirements.  

The tools were tested and don't fail.  However, a more powerful LLM seems suitable to handle an agent, especially with long prompts.  
