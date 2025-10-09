# About: Create a sequential workflow of persistent Foundry agents with tool use capability
# Dependancy: A03_Create_Multiple_Foundry_Agent_Persistent.py (to create the agents first)
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/sequential?pivots=programming-language-python
# Ref: https://github.com/microsoft/agent-framework/tree/2397795c1dba1f9b6c6f2aaa1c490f362598bb9a/python/samples/getting_started/workflows

import os
import asyncio
from random import randint
from typing import Annotated

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework import ChatAgent
from pydantic import Field

from agent_framework import SequentialBuilder
from agent_framework import ChatMessage, Role, WorkflowStatusEvent, WorkflowOutputEvent # WorkflowCompletedEvent
from typing import Any
from agent_framework import WorkflowBuilder, WorkflowViz

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Replace with your created persistent agents IDs created in A03_Create_Multiple_Foundry_Agent_Persistent.py, could be set in environment variables too
data_analyser_agent_id = 'asst_cdSnwo36bPU3Fe65XmlOrVqP' 
risk_assessor_agent_id = 'asst_RptktIPCkBwRaYpcCXZ1S42V'
maintenance_scheduler_agent_id = 'asst_zmG9m4LW8ZuFtxFtz2DJCytw'

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
    print(f'data: {data}')
    return data

def schedule_maintenance(
    equipment_id: Annotated[str, Field(description="The ID of the equipment to schedule maintenance for.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> int:    
    """Scheduling maintenance for the given equipment, returns maintenance request number."""
    # In a real implementation, this function would interact with a maintenance scheduling system.
    print(f"Maintenance scheduled for {equipment_type} with ID {equipment_id}.")
    return randint(9000, 9999)  # Simulated maintenance request number

def send_shutdown_equipment_notification(
    equipment_id: Annotated[str, Field(description="The ID of the equipment to shut down.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> int:    
    """Send notification for shutting down the given equipment and notifying relevant teams, returns notification ID."""    
    print(f"Shutdown protocol triggered for {equipment_type} with ID {equipment_id}. Relevant teams notified.")
    return randint(100, 500)  # Simulated notification ID


async def main():
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        ) as project_client,
    ):        

        # Get required agents created previously (in A03_Create_Multiple_Foundry_Agent_Persistent.py)
        data_analyser_foundry_agent = await project_client.agents.get_agent(agent_id=data_analyser_agent_id)
        risk_assessor_foundry_agent = await project_client.agents.get_agent(agent_id=risk_assessor_agent_id)
        maintenance_scheduler_foundry_agent = await project_client.agents.get_agent(agent_id=maintenance_scheduler_agent_id)
        print("Foundry agents retrieved successfully.")

        try:
            # Create chat agents for each foundry agent with appropriate tool registration
            data_analyser_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=data_analyser_foundry_agent.id
                ),                
                instructions=data_analyser_foundry_agent.instructions, # From existing agent or can be overridden here
                tools=[get_data],
                name=data_analyser_foundry_agent.name,
                description=data_analyser_foundry_agent.description
            ) 

            # # Test the data analyser agent
            # result = await data_analyser_chat_agent.run("Analyse data for pump ID P456")
            # print(result.text)

            risk_assessor_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=risk_assessor_foundry_agent.id,                    
                ),                
                instructions=risk_assessor_foundry_agent.instructions, # From existing agent or can be overridden here
                # tools=None,
                name=risk_assessor_foundry_agent.name,
                description=risk_assessor_foundry_agent.description
            ) 

            maintenance_scheduler_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=maintenance_scheduler_foundry_agent.id
                ),
                instructions=maintenance_scheduler_foundry_agent.instructions, # From existing agent or can be overridden here
                tools=[schedule_maintenance, send_shutdown_equipment_notification],
                name=maintenance_scheduler_foundry_agent.name,
                description=maintenance_scheduler_foundry_agent.description
            )

            print("Chat agents created successfully.")

            # Build the sequential workflow (data analyser -> risk assessor -> maintenance scheduler)
            workflow = SequentialBuilder().participants([data_analyser_chat_agent, risk_assessor_chat_agent, maintenance_scheduler_chat_agent]).build()
            print("Sequential workflow built successfully.")

            # # Visualize the workflow - Uncomment if needed
            # viz = WorkflowViz(workflow)
            # # Mermaid diagram
            # print(viz.to_mermaid())
            # # DiGraph string
            # print(viz.to_digraph())


            print("===== Running Workflow =====")

            # Run the workflow
            # completion: WorkflowCompletedEvent | None = None
            completion = None
            events = workflow.run_stream("Analyse data for pump ID P456")
            
            async for event in events:
                
                # print(f'event: {event}')

                # (Documentation incorrect)
                # if isinstance(event, WorkflowCompletedEvent):
                #     completion = event

                if isinstance(event, WorkflowOutputEvent):
                    completion = event
                    # print(f'event: {event}')

            if completion:
                print("----- Final output -----")
                messages: list[ChatMessage] | Any = completion.data
                for i, msg in enumerate(messages, start=1):
                    name = msg.author_name or ("assistant" if msg.role == Role.ASSISTANT else "user")
                    print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")

            print("===== Workflow Completed =====")

        except Exception as e:
            print(f'Error occurred: {e}')            

asyncio.run(main())