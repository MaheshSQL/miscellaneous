# Part 1 - Create a Logic App with HTTP Trigger within the same resource group as your Azure AI Project in Azure Portal
# Part 2 - Create an Agent with LogicApp tool call capabilities
# Part 3 - LogicApp to call FunctionApp using OpenAPI spec and JWT authentication

# References: 
# https://learn.microsoft.com/en-gb/azure/ai-foundry/agents/how-to/tools/logic-apps?pivots=portal
# https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_tools/sample_agents_logic_apps.py
# https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_tools/utils/user_logic_apps.py

# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    This sample demonstrates how to use agents with Logic Apps to execute the task of getting current weather

PREREQUISITES:
    1) Create a Logic App within the same resource group as your Azure AI Project in Azure Portal
    2) To configure your Logic App to to get weather information, you must include an HTTP request trigger that is
    configured to accept JSON with 'city'. The guide to creating a Logic App Workflow
    can be found here:
    https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/agents-logic-apps#create-logic-apps-workflows-for-function-calling

USAGE:
    python logicapp_openapi_tool.py

    Before running the sample:

    pip install azure-ai-projects azure-ai-agents azure-identity azure-mgmt-logic

    Set this environment variables with your own values:
    1) PROJECT_ENDPOINT - The Azure AI Project endpoint, as found in the Overview
                          page of your Azure AI Foundry portal.
    2) MODEL_DEPLOYMENT_NAME - The deployment name of the AI model, as found under the "Name" column in
       the "Models + endpoints" tab in your Azure AI Foundry project.

    Replace the following values in the sample with your own values:
    1) <LOGIC_APP_NAME> - The name of the Logic App you created.
    2) <TRIGGER_NAME> - The name of the trigger in the Logic App you created (the default name for HTTP
        triggers in the Azure Portal is "When_a_HTTP_request_is_received").
    
"""


import os
import sys
from typing import Set

from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ToolSet, FunctionTool
from azure.identity import DefaultAzureCredential

# Example user function
current_path = os.path.dirname(__file__)
root_path = os.path.abspath(os.path.join(current_path, os.pardir, os.pardir))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Import AzureLogicAppTool and the function factory from user_logic_apps
# NOTE: These functions should be available locally when running agent so the SDK can execute them automatically, otherwise you will have to manually call these functions
from utils.user_logic_apps import AzureLogicAppTool, create_get_weather_function


from dotenv import load_dotenv

load_dotenv()

# Create the agents client
project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# [START register_logic_app]
# Extract subscription and resource group from the project scope
subscription_id = os.environ["SUBSCRIPTION_ID"]
resource_group = os.environ["RESOURCE_GROUP_NAME"]

# Logic App details
logic_app_name = os.environ["LOGIC_APP_NAME"]
trigger_name = os.environ["LOGIC_APP_TRIGGER_NAME"]

# Create and initialize AzureLogicAppTool utility
logic_app_tool = AzureLogicAppTool(subscription_id, resource_group)
logic_app_tool.register_logic_app(logic_app_name, trigger_name)
print(f"Registered logic app '{logic_app_name}' with trigger '{trigger_name}'.")

# Create the specialized "send_email_via_logic_app" function for your agent tools
get_weather_func = create_get_weather_function(logic_app_tool, logic_app_name)

# Prepare the function tools for the agent
functions_to_use: Set = {    
    get_weather_func,  # This references the AzureLogicAppTool instance via closure
}
# [END register_logic_app]

with project_client:
    
    agents_client = project_client.agents
    
    functions = FunctionTool(functions=functions_to_use)
    toolset = ToolSet()
    toolset.add(functions)

    # Enables tool calls to be executed automatically during runs.create_and_process or runs.stream. 
    # If this is not set, functions must be called manually.
    agents_client.enable_auto_function_calls(toolset)

    # Create / update an agent
    agent_id = 'asst_kARD6pMAN5yLqOAeCGzQp6l5' # Leave blank for first run, or specify an existing agent ID to update it

    # Check if the agent already exists
    agent = None
    if agent_id:
        print(f"Checking if agent with ID {agent_id} exists.")
        agent = agents_client.get_agent(agent_id)

    if agent:
        print(f"Agent with ID {agent_id} already exists. Updating existing agent.")
        agent = agents_client.update_agent(
            agent_id = agent_id, # Specify a unique agent ID,
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="WeatherInfoAgent",
            instructions="You are a specialized agent for providing weather information with help of tools available to you",
            toolset=toolset
        )
        print(f"Updated agent, ID: {agent.id}")

    else:

        print(f"Creating new agent")
        agent = agents_client.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="WeatherInfoAgent",
            instructions="You are a specialized agent for providing weather information with help of tools available to you",
            toolset=toolset,
        )
        print(f"Created agent, ID: {agent.id}")

    # Create a thread for communication
    thread = agents_client.threads.create()
    print(f"Created thread, ID: {thread.id}")

    # Create a message in the thread
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content="Hello, what's the weather in Perth?",
    )
    print(f"Created message, ID: {message.id}")

    # Create and process an agent run in the thread
    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # # Delete the agent when done
    # agents_client.delete_agent(agent.id)
    # print("Deleted agent")

    # Fetch and log all messages
    messages = agents_client.messages.list(thread_id=thread.id)
    for msg in messages:
        if msg.text_messages:
            last_text = msg.text_messages[-1]
            print(f"{msg.role}: {last_text.text.value}")
            # print(msg.text_messages)