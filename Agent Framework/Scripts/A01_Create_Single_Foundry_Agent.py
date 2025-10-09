# About: Create non-persistent Foundry agents with tool use capability
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/azure-ai-foundry-agent?pivots=programming-language-python#explicit-configuration 

import os
import asyncio
from random import randint
from typing import Annotated

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Tools for the agents
def get_data(
    pump_id: Annotated[str, Field(description="The ID of the pump to get data for.")],
) -> str:
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
        AzureAIAgentClient(
            project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
            model_deployment_name=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            async_credential=credential,
            agent_name="Data Analyser Agent"
        ).create_agent(
            instructions='''"Analyze incoming pipeline sensor data (pressure, temperature, flow rate). 
            Identify any anomalies or deviations from normal operating ranges. 
            Normal ranges: Pressure (20-80 PSI), Temperature (65-75 °C), Flow Rate (40-90 LPM).
            Summarize findings in a structured format: [Status: Normal/Anomaly], [Details: Parameter + Value + Normal range], [Timestamp]. 
            Pass results to the Risk Assessor Agent."''',
            tools=get_data
        ) as agent,
    ):
        result = await agent.run("Analyse data for pump ID P456")
        print(result.text)

asyncio.run(main())