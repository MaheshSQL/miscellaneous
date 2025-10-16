# About: Create a persistent Foundry agents with tool use capability
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

async def main():
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        ) as project_client,
    ):
        
        # Note: You can also list existing agents here to get their IDs, then delete them if needed before creating new ones
        # e.g. project_client.agents.list_agents()

        # Create a persistent agent
        data_analyser_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Data Analyser Agent",
            instructions='''Analyze incoming pipeline sensor data (pressure, temperature, flow rate). 
            Identify any anomalies or deviations from normal operating ranges. 
            Normal ranges: Pressure (20-80 PSI), Temperature (65-75 °C), Flow Rate (40-90 LPM).
            Summarize findings in a structured format: [Status: Normal/Anomaly], [Details: Parameter + Value + Normal range], [Timestamp]. 
            Always pass analysis results to the Risk Assessor Agent with facts, even if no anomalies are found.
            Do not make up facts, be concise and to the point.''',
            description='An agent that analyzes incoming sensor data for anomalies and deviations from normal operating ranges.',            
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent
        risk_assessor_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Risk Assessor Agent",
            instructions='''Review analysis report from Data Analyser Agent. 
            Assess severity based on thresholds (e.g., normal / minor, moderate, critical). 
            Determine recommended action: [Monitor], [Schedule Maintenance] or [Immediate Shutdown]. 
            Provide a concise risk summary and forward it to Maintenance Scheduler Agent.
            Do not make up facts, be concise and to the point.''',
            description='An agent that assesses risk based on data analysis and recommends actions.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent with Human Approval
        risk_assessor_agent_v2 = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Risk Assessor Agent V2",
            instructions='''Review analysis report from Data Analyser Agent. 
            Assess severity based on thresholds (e.g., normal / minor, moderate, critical). 
            Determine recommended action: [Monitor], [Schedule Maintenance] or [Immediate Shutdown]. 
            Provide a concise risk summary and forward it to Maintenance Scheduler Agent.
            [Schedule Maintenance] and [Immediate Shutdown] action recommendations requires you to obtain human approval which will be checked by next workflow step.
            Do not make up facts, be concise and to the point.''',
            description='An agent that assesses risk based on data analysis and recommends actions, initiates human approval for critical actions.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent
        maintenance_scheduler_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Maintenance Scheduler Agent",
            instructions='''Based on the risk summary from Risk Assessor Agent, create a maintenance plan. 
            If action is [Schedule Maintenance] and assign crew - Team A or Team B. 
            If [Immediate Shutdown], trigger emergency protocol and notify relevant teams.
            If [Monitor], do nothing but log the recommendation.
            Confirm the scheduled action and output a final status report.
            Do not make up facts, be concise and to the point.''',
            description='An agent that schedules maintenance or triggers shutdown based on risk assessment.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent with Human Approval
        maintenance_scheduler_agent_v2 = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Maintenance Scheduler Agent V2",
            instructions='''Based on the risk summary from Risk Assessor Agent, create a maintenance plan. 
            If action is [Schedule Maintenance] and assign crew - Team A or Team B. 
            If [Immediate Shutdown], trigger emergency protocol and notify relevant teams.
            If [Monitor], do nothing but log the recommendation.
            Confirm the scheduled action and output a final status report.
            [Schedule Maintenance] and [Immediate Shutdown] actions require human approval result [APPROVED]. Do nothing when approval result is [REJECTED] or when waiting on approval result.
            You can retrieve human approval status. Say [PENDING] if approval is required but not yet granted.
            Do not make up facts, be concise and to the point.''',
            description='An agent that schedules maintenance or triggers shutdown based on risk assessment, checks human approval for critical actions.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # Create a persistent agent
        triage_agent = await project_client.agents.create_agent(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            name="Triage Agent",
            instructions='''You determine which agent to use based on the user's query and subsequent agent outputs. ALWAYS handoff to another agent.
            Do not make up facts, be concise and to the point.''',
            description='An agent that Routes messages to the appropriate specialist agent.',
            temperature=0.0,
            # tools=get_data # Tool registration not yet supported in create_agent API. Specify tools when using the agent (ChatAgent) as below.
        )

        # print(f'data_analyser_agent.id: {data_analyser_agent.id}')
        # print(f'risk_assessor_agent.id: {risk_assessor_agent.id}')
        print(f'risk_assessor_agent_v2.id: {risk_assessor_agent_v2.id}') # New agent with human approval        
        # print(f'maintenance_scheduler_agent.id: {maintenance_scheduler_agent.id}')
        print(f'maintenance_scheduler_agent_v2.id: {maintenance_scheduler_agent_v2.id}') # New agent with human approval
        # print(f'triage_agent.id: {triage_agent.id}')

asyncio.run(main())