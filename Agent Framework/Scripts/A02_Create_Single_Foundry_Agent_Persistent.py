# About: Create a persistent Foundry agents with tool use capability (Note: The code below deletes the agent after use, comment out deletion code to keep the agent)
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/azure-ai-foundry-agent?pivots=programming-language-python#creating-and-managing-persistent-agents 

import os
import asyncio
from random import randint
from typing import Annotated

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework import ChatAgent
from pydantic import Field

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Tools for the agents
def get_data(
    pump_id: Annotated[str, Field(description="The ID of the pump to get data for.")],
) -> dict:
    print(f'get_data called with pump_id: {pump_id}')
    """Get the data (temperature, pressure, flow rate) for a given pump in JSON format."""
    pressure = randint(10, 100)  # PSI
    temperature = randint(60, 80)  # °C
    flow_rate = randint(20, 100)  # LPM
    timestamp =   datetime.now().isoformat() #'2025-01-01T00:00:00Z'

    data =  { 
        "pump_id": pump_id,
        "pressure": str(pressure) + ' PSI',
        "temperature": str(temperature) + ' °C',
        "flow_rate": str(flow_rate) + ' LPM',
        "timestamp": timestamp
    }
    # print(f'data: {data}')
    return data

async def main():
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        ) as project_client,
    ):
        # Create a persistent agent
        created_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Data Analyser Agent",
            instructions='''Analyze incoming pipeline sensor data (pressure, temperature, flow rate). 
            Identify any anomalies or deviations from normal operating ranges. 
            Normal ranges: Pressure (20-80 PSI), Temperature (65-75 °C), Flow Rate (40-90 LPM).
            Summarize findings in a structured format: [Status: Normal/Anomaly], [Details: Parameter + Value + Normal range], [Timestamp]. 
            Pass results to the Risk Assessor Agent.''',
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        print(f'created_agent.id: {created_agent.id}')

        # To get the instructions of the created agent (The agent id should be of an existing agent)
        foundry_agent = await project_client.agents.get_agent(agent_id=created_agent.id)
        # print(f'foundry_agent.instructions: {foundry_agent.instructions}')        

        try:
            # Use the agent
            async with ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=foundry_agent.id
                ),                
                instructions=foundry_agent.instructions, # From existing agent or can be overridden here
                name=foundry_agent.name,
                tools=get_data
            ) as agent:
                result = await agent.run("Analyse data for pump ID P456")
                print(result.text)
        finally:
            # Clean up the agent
            await project_client.agents.delete_agent(created_agent.id)
            print(f'Agent deleted: {created_agent.id}')

asyncio.run(main())