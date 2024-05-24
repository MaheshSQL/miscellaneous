import os
import json
import logging

from openai import AzureOpenAI
from azure.functions import HttpRequest, HttpResponse

import base64
import mimetypes  


def main(req: HttpRequest) -> HttpResponse:

    function_name = 'RunPromptOnImage'

    llm_output = None
    finish_reason = None

    logging.info(f'Python HTTP trigger function {function_name} has started processing a request.')    

    # Extract text from request payload
    req_body = req.get_body().decode('utf-8')
    # logging.info(f'req_body:{req_body}')
    request = json.loads(req_body)
    # logging.info(f'request:{request}')

    for value in request['values']:
    # if len(request['values']) > 0:

        base64String = value["data"]["image"]["data"]
        # print(f'base64String:{base64String}')    

        content_type = value["data"]["content_type"]
        logging.info(f'content_type:{content_type}')

        logging.info('Calling get_image_description() started')
        llm_output, finish_reason = get_image_description(base64String, content_type)
        logging.info('Calling get_image_description() completed')

        if finish_reason != 'stop':
            llm_output = f'finish_reason:{finish_reason}'
            logging.info(f'finish_reason != "stop", llm_output:{llm_output}')


    # Create the response object
    response_body = {
        "values": [
            {
                "recordId": request['values'][0]['recordId'],
                "data": {
                    "description": llm_output
                },
                "errors": None,
                "warnings": None
            }
        ]
    }

    # logging.info(response_body)

    # Serialize the response object to JSON and return it
    response = HttpResponse(json.dumps(response_body))
    response.headers['Content-Type'] = 'application/json'
    
    logging.info(f'Python HTTP trigger function {function_name} has completed processing a request.')

    return response

    

def get_image_description(base64_encoded_data, mime_type = 'image/png'):

    llm_output = None
    finish_reason = None

    api_base = os.getenv('AZURE_OPENAI_BASE')
    api_key = os.getenv('AZURE_OPENAI_KEY')
    deployment_name = os.getenv('AZURE_OPENAI_GPT4V_DEPLOYMENT_NAME')
    api_version = os.getenv('AZURE_OPENAI_GPT4V_API_VERSION')

    temperature = os.getenv("AZURE_OPENAI_TEMPERATURE")
    top_p = os.getenv("AZURE_OPENAI_TOP_P")
    max_tokens = os.getenv("AZURE_OPENAI_MAX_TOKENS")
    system_message = os.getenv("AZURE_OPENAI_SYSTEM_MESSAGE")

    # print(f'max_tokens:{max_tokens}, type(max_tokens):{type(max_tokens)}')

    base_url=f"{api_base}/openai/deployments/{deployment_name}/extensions"    
    # print(f'base_url:{base_url}')

    client = AzureOpenAI(
    api_key=api_key,  
    api_version=api_version,
    base_url=base_url
    )

    image_url_base64 = f"data:{mime_type};base64,{base64_encoded_data}"

    response = client.chat.completions.create(
    model= deployment_name, 
    messages=[
        { "role": "system", "content": system_message },
        { "role": "user", "content": [  
            { 
                "type": "text", 
                "text": "Describe this picture:" 
            },
            { 
                "type": "image_url",
                "image_url": {
                    "url": image_url_base64
                    # "url": "https://learn.microsoft.com/azure/ai-services/computer-vision/media/quickstarts/presentation.png"
                }
            }
        ] } 
    ],
    
    max_tokens= int(max_tokens),
    top_p= float(top_p),
    temperature= float(temperature)
    )
    
    # print(f'response:{response}')       

    if response and len(response.choices) > 0 and response.choices[0].message:

        # print(f'response.choices[0].message.content: {response.choices[0].message.content}')
        llm_output = response.choices[0].message.content

        # print(f'response.choices[0].finish_reason=: {response.choices[0].finish_reason}')  
        finish_reason = response.choices[0].finish_reason

        # print(f'type(llm_output):{type(llm_output)}')
        # print(f'type(finish_reason):{type(finish_reason)}')

    return llm_output, finish_reason