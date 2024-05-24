This repository contains miscellaneous script collections.

- <b>/Azure Functions</b>: This directory has Azure Function App projects.

  - <b>/AzureFunctions/Proj_LLMSQL</b>:

    - This Azure Function project contains Azure Function/s that articulate a response to natural language question on dataset within an Azure SQL Database tables. The function makes use of LangChain SQLDatabaseToolkit backed by gpt-35-turbo-16k (can work with 4k version too) LLM.
      ![](images/GetAnswersFromSQLDB.png)
    - You require Azure OpenAI and Azure SQL Database resources provisioned beforehand.
    - Ensure the database contains tables (with descriptive names) that you would like to ask questions to.
    - This function can be called by any front-end application to render output.
    - To run this Azure Functions project locally
      - [Install necessary prerequsites for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-cli-python?tabs=bash%2Cazure-cli&pivots=python-mode-configuration)
      - Create a local python virtual environment.
      - `pip install -r requirements.txt`
      - Rename _local.settings_template.json_ file to _local.settings.json_ and update the values in this file.
      - Open this repository in VS Code.
      - Open VS Code terminal and navigate to \miscellaneous\Azure Functions\Proj_LLMSQL directory
      - `func start`
      - Open Postman and create a new post request to the URL displayed in the terminal
        - Ensure that the question to the database is included in the request body
        - Request body example: {"question":"Which customers live in Paris?"}
        - Ensure to include function key as x-functions-key in the request header.
    - To deploy to Azure Function App
      - Create Azure Function App (Python 3.9)
      - Open VS Code terminal and navigate to \miscellaneous\Azure Functions\Proj_LLMSQL directory
      - `az login`
      - `az account set --subscription [Your Subscription ID]`
      - `func azure functionapp publish [Your function app name]`
      - Update application settings.

  - <b>/AzureFunctions/GPT4V_Custom_Skill</b>:
    - This Azure Function project contains function that accepts image as input (base64-encoded string format), passes it to GPT4-Vision endpoint and returns a text description based on the configuration parameters (system message, temperature, max response, etc.). The http trigger function is built to be called as Azure AI Search custom skill.
      ![](images/GPT4VCustomSkillFlow.png)
    - You require Azure OpenAI service with GPT4 Vision deployment, existing/new Azure AI Search service provisioned.
    - You will need to create additional AI Search artefacts to consume this functionality: Data source, Skillset, Indexer.
    - Please refer to information given on [passing images to AI Search custom skills](https://learn.microsoft.com/en-us/azure/search/cognitive-search-concept-image-scenarios#passing-images-to-custom-skills)
    - Please review the public documentation to learn more about the [GPT-4 Turbo with Vision](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/gpt-with-vision?tabs=rest%2Csystem-assigned%2Cresource)
    - The provided Azure function code is tested for Python 3.10
    - Steps to run locally and deploy to Azure are same, listed in previous function section.

<br>

- <b>/SynapseML</b>: This directory contains Synapse ML project artefacts.

  - <b>/SynapseML/ChatCompletion</b>:

    - This is collection of artefacts to demonstrate the ChatCompletion using Azure OpenAI gpt-35-turbo (0613) on a spark dataframe in Synapse.
    - The code uses SynapseML library.
    - Setup instructions for SynapseML library and Spark MS SQL Connector have been given in the respective notebooks.
    - The sample dataset is a subset of [OpinRank](https://archive.ics.uci.edu/ml/machine-learning-databases/00205/) dataset (Hotel and car reviews) which is included in this repo.
    - You need to upload the provided dataset into your Synapse workspace (or a storage account connected to the workspace).
    - Ensure that Azure OpenAI service is provisioned and gpt-35-turbo (0613) model deployment is done beforehand.
    - Ensure you have a Linked Service created for an Azure Key Vault where the secrets have to be stored (AZSQLUSR, AZSQLPWD, OPENAISERVICENAME,OPENAIAPIKEY). Alternatively, you can provide them in code directly (not recommended).
    - Import both notebooks into your Synapse workspace.
      - First notebook imports provided dataset into an Azure SQL table.
      - Second notebook reads data from Azure SQL table, applies custom LLM prompt to each record of the dataframe's nominated column using ChatCompletion model.
    - **Input** dataset after import to Azure SQL server table, after successful run of the first notebook.  
       ![](images/AzureSQLInputDataset.png)
      _(Query run in SQL Server Management Studio)_
    - ChatCompletion **System Message**
      ```
      You are the AI analyst and lead the change management team in hospitality industry.
      ```
    - ChatCompletion **Prompt**

      ```You are provided with review comment submitted by the guests after their stay at the hotel.
      Perform a thorough analysis of the comments written by our guests.

      If comment has a positive sentiment, identify what we need to be keep doing.
      If comment has a negative sentiment, identify what we need to improve.
      For neutral sentiment comment, say "N/A"

      Format your findings as per structure below:
      {
          "sentiment":"positive" / "negative" / "neutral",
          "identified_action": "",
          "action_type": "continue" / "improve" / "N/A"
      }

      Only return one finding per review comment.

      Provided review comments:
      ```

    - **Output** dataset created with SynapseML, saved into Azure SQL Server table after successful run of the second notebook.
      ![](images/AzureSQLLLMOutput.png)
      _(Query run in SQL Server Management Studio)_
    - The dataset / LLM prompt can be adjusted as per your requirement once you get this solution working.
    - The LLM prompt produces output in the JSON format. The T-SQL SELECT query to parse the output is also included in this repo.
