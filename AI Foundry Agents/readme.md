# About

The below scripts demonstrate various tool calling scenarios from Azure AI Foundry Agents. The scripts create and run the agents.

- **openapi_tool.py**: Call OpenApi as tool with anonymous authentication
- **logicapp_tool.py**: Call Azure LogicApp tool using credential-based authentication
- **openapi_tool_wrap.py**: Call a simulated OpenAPI (Azure LogicApps endpoint) with SAS authentication.

Please note, these examples use automatic function calling through azure-ai-agents and azure-ai-projects Python SDK. Running the agents in Azure AI Foundry will not run the tool calls configured as part of above examples.

The _requirements.txt_ and _env_ template files are included.
