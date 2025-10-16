# About: Create a sequential workflow of persistent Foundry agents with tool use capability and human approval step (for critical actions), pause and resume after approval
# The workflow will save state when human approval is pending, when external approval is granted run the workflow again, it will resume from last checkpoint and the last agent will check for approval status and complete the workflow
# Dependancy: A03_Create_Multiple_Foundry_Agent_Persistent.py (to create the agents first)
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/sequential?pivots=programming-language-python
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/checkpoints?pivots=programming-language-python
# Ref: https://github.com/microsoft/agent-framework/tree/2397795c1dba1f9b6c6f2aaa1c490f362598bb9a/python/samples/getting_started/workflows
# Learning: The agent to resume from should not be the last agent in the workflow as it will not run again when resuming from checkpoint, so we save state up to the second last agent (Risk Assessor Agent) in this case

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
from agent_framework import WorkflowBuilder, WorkflowViz, InMemoryCheckpointStorage, FileCheckpointStorage, WorkflowCheckpoint, Message
import json
from dataclasses import asdict

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Replace with your created persistent agents IDs created in A03_Create_Multiple_Foundry_Agent_Persistent.py, could be set in environment variables too
data_analyser_agent_id = 'asst_cdSnwo36bPU3Fe65XmlOrVqP' 
risk_assessor_agent_v2_id = 'asst_Mk7LMQ5VvupjerO71fjAOnFG'
maintenance_scheduler_agent_v2_id = 'asst_2e7UPyg6AwBQ3jDHgy4AIloJ'

# Simulated external system for human approval results
approval_json_file = '../approval_db.json'

# Example structure of the JSON file (approval_db.json)
# approval_json_db = { 
#     # Example entry for reference
#     "pump123": {
#         "action": "Schedule Maintenance",
#         "equipment_id": "pump123",
#         "equipment_type": "pump",
#         "status": "pending"
#         "created_on": "2024-01-01T00:00:00Z"
#     }
# }

workflow_checkpoint_file_path = '../' # Directory to save checkpoint files when using FileCheckpointStorage
workflow_checkpoint_json = '../workflow_checkpoint.json'


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
    remove_workflow_checkpoint_file() # Remove checkpoint file as workflow ends here
    return randint(9000, 9999)  # Simulated maintenance request number

def send_shutdown_equipment_notification(
    equipment_id: Annotated[str, Field(description="The ID of the equipment to shut down.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> int:    
    """Send notification for shutting down the given equipment and notifying relevant teams, returns notification ID."""    
    print(f"Shutdown protocol triggered for {equipment_type} with ID {equipment_id}. Relevant teams notified.")
    remove_workflow_checkpoint_file() # Remove checkpoint file as workflow ends here
    return randint(100, 500)  # Simulated notification ID

def send_approval_rejection_notification(
    action: Annotated[str, Field(description="The action that was rejected (e.g., Schedule Maintenance, Immediate Shutdown).")],
    equipment_id: Annotated[str, Field(description="The ID of the equipment involved.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> None:
    """Send notification that the requested action was rejected by human approver."""
    print(f"Notification: Action '{action}' for {equipment_type} with ID {equipment_id} was rejected by human approver, no action taken.")
    remove_workflow_checkpoint_file() # Remove checkpoint file as workflow ends here

def request_human_approval(
    action: Annotated[str, Field(description="The action requiring approval (e.g., Schedule Maintenance, Immediate Shutdown).")],
    equipment_id: Annotated[str, Field(description="The ID of the equipment involved.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> None:
    """Request human approval for critical actions via external system."""
    print(f"Human approval requested for action '{action}' on {equipment_type} with ID {equipment_id}.")
    
    # In a real implementation, this function would interact with an external system to get human approval.
    # Here, we simulate by writing a pending approval entry to a JSON file.    
    approval_json_file_data = { 
        equipment_id: {
            "action": action,
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "status": "[PENDING]",
            "created_on": datetime.now().isoformat() #'2024-01-01T00:00:00Z'
        }
    }

    # Write to JSON file (simulating external system interaction)
    with open(approval_json_file, 'w') as f:
        json.dump(approval_json_file_data, f, indent=4)
    print(f"Approval request for {equipment_id} written to {approval_json_file}. Please update the status to [APPROVED] or [REJECTED] in the file to simulate human response.")

def get_human_approval_status(
        equipment_id: Annotated[str, Field(description="The ID of the equipment involved.")],
) -> str:
    """Check the human approval status from the external JSON file when the workflow is resumed"""
    try:
        with open(approval_json_file, 'r') as f:
            approval_data = json.load(f)
            if equipment_id in approval_data:
                status = approval_data[equipment_id].get("status", "[PENDING]")
                print(f"Approval status for {equipment_id}: {status}")
                return status
            else:
                print(f"No approval request found for equipment ID {equipment_id}.")
                return "[PENDING]"
    except FileNotFoundError:
        print(f"Approval file {approval_json_file} not found.")
        return "[PENDING]"

def remove_workflow_checkpoint_file():
    """Utility function to remove existing workflow checkpoint file to start a new workflow run."""
    if os.path.exists(workflow_checkpoint_json):
        os.remove(workflow_checkpoint_json)
        print(f"Existing workflow checkpoint file {workflow_checkpoint_json} removed.")
    else:
        print(f"No existing workflow checkpoint file {workflow_checkpoint_json} found.")

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
        risk_assessor_foundry_agent = await project_client.agents.get_agent(agent_id=risk_assessor_agent_v2_id)
        maintenance_scheduler_foundry_agent = await project_client.agents.get_agent(agent_id=maintenance_scheduler_agent_v2_id)
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
                tools=[request_human_approval],
                name=risk_assessor_foundry_agent.name,
                description=risk_assessor_foundry_agent.description
            ) 

            maintenance_scheduler_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=maintenance_scheduler_foundry_agent.id
                ),
                instructions=maintenance_scheduler_foundry_agent.instructions, # From existing agent or can be overridden here
                tools=[get_human_approval_status, schedule_maintenance, send_shutdown_equipment_notification, send_approval_rejection_notification], # Tools for human approval and actions
                name=maintenance_scheduler_foundry_agent.name,
                description=maintenance_scheduler_foundry_agent.description
            )

            print("Chat agents created successfully.")

            checkpoint_storage = InMemoryCheckpointStorage()
            # checkpoint_storage = FileCheckpointStorage(storage_path=workflow_checkpoint_file_path)
            print("Checkpoint storage initialized.")

            # Build the sequential workflow (data analyser -> risk assessor -> maintenance scheduler)
            workflow = SequentialBuilder().participants([data_analyser_chat_agent, risk_assessor_chat_agent, maintenance_scheduler_chat_agent]).with_checkpointing(checkpoint_storage).build()
            print("Sequential workflow built successfully.")

            # # Visualize the workflow - Uncomment if needed
            # viz = WorkflowViz(workflow)
            # # Mermaid diagram
            # print(viz.to_mermaid())
            # # DiGraph string
            # print(viz.to_digraph())

            # Check if workflow checkpoint file exists to resume from last checkpoint (Delete the file to start a new workflow run)
            if os.path.exists(workflow_checkpoint_json):                
                with open(workflow_checkpoint_json, 'r') as f:
                    checkpoint_data = json.load(f)
                    from_checkpoint = WorkflowCheckpoint.from_dict(checkpoint_data) # Resume from a given checkpoint
                    await checkpoint_storage.save_checkpoint(from_checkpoint) # Hydrate the checkpoint storage with the checkpoint data
                print("Checkpoint data loaded into checkpoint storage.")


            print("===== Running Workflow =====")

            # Run the workflow
            # completion: WorkflowCompletedEvent | None = None
            completion = None
            if os.path.exists(workflow_checkpoint_json): # Resume from last checkpoint
                print("Checkpoint found, resuming workflow from last checkpoint.") 
                events = workflow.run_stream_from_checkpoint(checkpoint_id = from_checkpoint.checkpoint_id,
                                                            #  responses = {f"request_id_{randint(100,999)}": "Rerun workflow"}
                                                             )

                # print(f'workflow._runner._ctx._messages: {workflow._runner._ctx._messages}')
            else: # Start a new workflow run
                print("No checkpoint found, starting a new workflow run.")                
                events = workflow.run_stream("Analyse data for pump ID P456")
            
            async for event in events:
                
                # print(f'event: {event}')

                # (Documentation incorrect)
                # if isinstance(event, WorkflowCompletedEvent):
                #     completion = event

                if isinstance(event, WorkflowOutputEvent):
                    completion = event
                    # print(f'event: {event}')

            approval_pending = False # Flag to indicate if human approval is pending (required) in this case we would have saved the workflow state to resume later
            if completion:
                print("----- Final output -----")
                messages: list[ChatMessage] | Any = completion.data
                for i, msg in enumerate(messages, start=1):
                    name = msg.author_name or ("assistant" if msg.role == Role.ASSISTANT else "user")
                    if msg.text and "[PENDING]" in msg.text:
                        approval_pending = True
                    print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")

            print("===== Workflow Completed =====")

            # Get and display checkpoints
            print("===== Checkpoints =====")
            checkpoints = await checkpoint_storage.list_checkpoints()            

            # for ckp in checkpoints:
            #     print(f"Checkpoint data: {ckp}")

            # Save workflow state up to Risk Assessor Agent when approval is pending / required, the last Agent (Maintenance Scheduler) will keep checking for approval status when the workflow is resumed
            if checkpoints and approval_pending:
                print("Approval is pending, saving workflow state.")

                for ckp in reversed(checkpoints):
                    # Save state up to the Risk Assessor Agent so it resumes from there
                    if ckp.messages and ckp.messages.get('Risk Assessor Agent V2') is not None:
                        last_checkpoint = ckp
                        break
                # print(f"Last checkpoint: {last_checkpoint}")

                with open(workflow_checkpoint_json, 'w') as f:                    
                    json.dump(asdict(last_checkpoint), f, indent=4)
                print(f"Workflow state saved to {workflow_checkpoint_json}")
            else:
                print("Workflow state save not required.")

        except Exception as e:
            print(f'Error occurred: {e}')            

asyncio.run(main())