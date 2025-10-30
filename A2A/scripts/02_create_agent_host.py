# About: This script creates an agent host server that hosts a Data Analyser Agent created in the previous script.
# Dependancy: 01_create_foundry_agents.py (to create the agents first)
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/azure-ai-foundry-agent?pivots=programming-language-python#creating-and-managing-persistent-agents
# Ref: https://a2a-protocol.org/latest/tutorials/python/5-start-server/
# Ref: https://github.com/a2aproject/a2a-samples/blob/main/notebooks/a2a_quickstart.ipynb
# Note: initialize_agent() must be called in the same event loop as the server is started!
# Note: use localhost for local testing instead of 0.0.0.0

import os
import asyncio
from random import randint
from typing import Annotated

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework import ChatAgent
from pydantic import Field

from a2a.client import ClientConfig, ClientFactory, create_text_message_object
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TransportProtocol,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils.message import (
    get_message_text,
    new_agent_parts_message,
    new_agent_text_message,
)

import uvicorn

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Replace with your created persistent agents IDs created in A03_Create_Multiple_Foundry_Agent_Persistent.py, could be set in environment variables too
data_analyser_agent_id = 'asst_cdSnwo36bPU3Fe65XmlOrVqP' 

# Implement AgentExecutor interface
class DataAnalyserAgentExecutor(AgentExecutor):

    # Tools for the agents
    @staticmethod
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
        print(f'data: {data}')
        return data

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.agent = None # Will be initialized in async method below - initialize_agent()

    async def initialize_agent(self):
        credential = AzureCliCredential()

        project_client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        )

        # Get required agents created previously (in A03_Create_Multiple_Foundry_Agent_Persistent.py)
        data_analyser_foundry_agent = await project_client.agents.get_agent(agent_id=self.agent_id)            
        print('Foundry agent retrieved successfully.')
    
        # Create chat agents for each foundry agent with appropriate tool registration
        data_analyser_chat_agent = ChatAgent(
            chat_client=AzureAIAgentClient(
                project_client=project_client,
                agent_id=self.agent_id
            ),                
            instructions=data_analyser_foundry_agent.instructions, # From existing agent or can be overridden here
            tools=[self.get_data],
            name=data_analyser_foundry_agent.name,
            description=data_analyser_foundry_agent.description
        )

        self.agent = data_analyser_chat_agent
        print('Agent initialized successfully.')      

    # Implement execute and cancel methods
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print(f'Executing agent with message: {context.get_user_input()}')
        
        result = await self.agent.run(context.get_user_input())        
        print(f'Agent returned result: {result}')
        # print(f'type of result: {type(result)}')
        
        await event_queue.enqueue_event(new_agent_text_message(result.text))

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Request the agent to cancel an ongoing task.

        The agent should attempt to stop the task identified by the task_id
        in the context and publish a `TaskStatusUpdateEvent` with state
        `TaskState.canceled` to the `event_queue`.

        Args:
            context: The request context containing the task ID to cancel.
            event_queue: The queue to publish the cancellation status update to.
        """
        pass


if __name__ == '__main__':

    agent_skill_1 = AgentSkill(
        id='get_data',
        name='Get Data',
        description='Get the data (temperature, pressure, flow rate) for a given pump in JSON format.',
        tags=['data', 'sensor', 'pipeline'],
        examples=[
            "Get data for pump ID P123",                
            "What are the current values for pressure, temperature, and flow rate for pump P456"]
        )

    agent_card = AgentCard(
    name='Data Analyser Agent',
    url='http://localhost:9999',
    description='Analyze incoming pipeline sensor data (pressure, temperature, flow rate).',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[agent_skill_1]
    )
    
    agent_executor=DataAnalyserAgentExecutor(agent_id=data_analyser_agent_id)

    # Define an async function to initialize the agent and start the server  
    async def start_server():  
        # asyncio.run(agent_executor.initialize_agent())
        # Initialize the agent (must happen in the same event loop)  
        await agent_executor.initialize_agent()  

        request_handler = DefaultRequestHandler(agent_executor=agent_executor,
                                                task_store=InMemoryTaskStore()
                                                )
        
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler
            )
        
        # uvicorn.run(server.build(), host='0.0.0.0', port=9999)
        # uvicorn.run(server.build(), host='localhost', port=9999, loop='none')
        # Run the server using uvicorn  
        config = uvicorn.Config(server.build(), host='localhost', port=9999, loop='asyncio')  
        server_instance = uvicorn.Server(config)  
        await server_instance.serve()

    # Use asyncio.run() to start the event loop and run the server  
    asyncio.run(start_server())  