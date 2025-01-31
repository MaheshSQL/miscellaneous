import os
import sys
from enum import Enum 

from dotenv import load_dotenv 
import json
import html
import base64
import shutil
import fitz  # PyMuPDF, imported as fitz for backward compatibility reasons
import glob

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  

from azure.core.credentials import AzureKeyCredential

from azure.search.documents import SearchClient, IndexDocumentsBatch

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

load_dotenv()

AOAI_ENDPOINT_URL = os.getenv('AOAI_ENDPOINT_URL')
AOAI_DEPLOYMENT_NAME = os.getenv('AOAI_DEPLOYMENT_NAME')
AOAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AOAI_EMBEDDING_DEPLOYMENT_NAME")
AOAI_APIVERSION = os.getenv('AOAI_APIVERSION')

AI_SEARCH_ENDPOINT = os.getenv('AI_SEARCH_ENDPOINT')
AI_SEARCH_KEY = os.getenv('AI_SEARCH_KEY')
AI_SEARCH_INDEX_NAME = os.getenv('AI_SEARCH_INDEX_NAME')

# N/A
DOCUMENTINTELLIGENCE_ENDPOINT = os.getenv('DOCUMENTINTELLIGENCE_ENDPOINT')
DOCUMENTINTELLIGENCE_API_KEY = os.getenv('DOCUMENTINTELLIGENCE_API_KEY')

############################ Variables #######################
file_paths_dict = {
    1: ".\\sample_documents\\AzureOpenAI FAQ.pdf",
    2: ".\\sample_documents\\guide-isolation_of_plant.pdf",
    3: ".\\sample_documents\\traffic-mgmt-for-works-on-roads-cop-march-24.pdf"
}

image_output_directory = '.\\images'
document_extract_directory = '.\\extracts'
chunk_export_directory = '.\\chunks'
# Process N images at a single time
pages_to_summarise = 10
image_res = "high" # auto, low, high
user_id = 'user1@company.com' # Placeholder
AI_Search_batch_size = 900

############################ Classes #########################

class Scenarios(Enum):
    EXTRACT = 1
    UPLOAD = 2
    QUERY = 3
    COMPARE = 4

class SampleDocs(Enum):
    AOAI_FAQ = 1
    ISOLATION_OF_PLANT = 2
    TRAFFIC_MGMT = 3

class ParagraphRoles(Enum):
    """ Enum to define the priority of paragraph roles """
    PAGE_HEADER      = 1
    TITLE           = 2
    SECTION_HEADING  = 3
    OTHER           = 3
    FOOTNOTE        = 5
    PAGE_FOOTER      = 6
    PAGE_NUMBER      = 7

class ContentType(Enum):
    """ Enum to define the types for various content chars returned from FR """
    NOT_PROCESSED           = 0
    TITLE_START             = 1
    TITLE_CHAR              = 2
    TITLE_END               = 3
    SECTIONHEADING_START    = 4
    SECTIONHEADING_CHAR     = 5
    SECTIONHEADING_END      = 6
    TEXT_START              = 7
    TEXT_CHAR               = 8
    TEXT_END                = 9
    TABLE_START             = 10
    TABLE_CHAR              = 11
    TABLE_END               = 12
    

class SystemMessage(Enum):
    EXTRACT_TITLE = 1
    EXTRACT_CONTENT = 2
    PAGE_SUMMARY = 3
    DOCUMENT_SUMMARY = 4

############################ Functions #######################
def print_colorful(text, color_code):  
    return f"\033[{color_code}m{text}\033[0m"  

# Encodes the given text into a URL-safe Base64 encoded string.  
def urlsafe_encode(text):  
    """   
    :param text: The text to encode.  
    :return: URL-safe Base64 encoded string.  
    """  
    # Convert string to bytes  
    data_bytes = text.encode('utf-8')  
    # URL-safe Base64 encode  
    encoded_data = base64.urlsafe_b64encode(data_bytes)  
    # Convert bytes back to string  
    encoded_string = encoded_data.decode('utf-8')  
    return encoded_string  

# Decodes the given URL-safe Base64 encoded string back to the original text.  
def urlsafe_decode(encoded_text):  
    """     
    :param encoded_text: The URL-safe Base64 encoded string to decode.  
    :return: The original decoded text.  
    """  
    # URL-safe Base64 decode  
    decoded_data = base64.urlsafe_b64decode(encoded_text)  
    # Convert bytes back to string  
    decoded_string = decoded_data.decode('utf-8')  
    return decoded_string 

# Get document content using Azure Document Intelligence Service
def analyze_document(path_to_sample_document):

    document_intelligence_client  = DocumentIntelligenceClient(
    endpoint=DOCUMENTINTELLIGENCE_ENDPOINT, credential=AzureKeyCredential(DOCUMENTINTELLIGENCE_API_KEY)
    )

    with open(path_to_sample_document, "rb") as f:
    
        poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout", 
        # analyze_request=f,
         body=f, 
        content_type="application/octet-stream")

    result = poller.result()

    return result

def table_to_html(table):
        """ Function to take an output FR table json structure and convert to HTML """
        table_html = "<table>"
        rows = [sorted([cell for cell in table["cells"] if cell["rowIndex"] == i],
                       key=lambda cell: cell["columnIndex"]) for i in range(table["rowCount"])]
        thead_open_added = False
        thead_closed_added = False 

        for i, row_cells in enumerate(rows):
            is_row_a_header = False
            row_html = "<tr>"
            for cell in row_cells:
                tag = "td"
                if 'kind' in cell:                      
                    if (cell["kind"] == "columnHeader" or cell["kind"] == "rowHeader"):
                        tag = "th"
                    if (cell["kind"] == "columnHeader"):
                        is_row_a_header = True
                cell_spans = ""
                if 'columnSpan' in cell:
                    if cell["columnSpan"] > 1:
                        cell_spans += f" colSpan={cell['columnSpan']}"
                if 'rowSpan' in cell:
                    if cell["rowSpan"] > 1:
                        cell_spans += f" rowSpan={cell['rowSpan']}"
                row_html += f"<{tag}{cell_spans}>{html.escape(cell['content'])}</{tag}>"
            row_html += "</tr>"
            
            # add the opening thead if this is the first row and the first header row encountered
            if is_row_a_header and i == 0 and not thead_open_added:
                row_html = "<thead>" + row_html 
                thead_open_added = True 
                            
            # add the closing thead if we have added an opening thead and if this is not a header row
            if not is_row_a_header and thead_open_added and not thead_closed_added:
                row_html = "</thead>" + row_html                 
                thead_closed_added = True
                
            table_html += row_html
        table_html += "</table>"
        return table_html

def build_document_map_pdf(result, enable_dev_code=False):
        """ Function to build a json structure representing the paragraphs in a document, 
        including metadata such as section heading, title, page number, etc.
        We construct this map from the Content key/value output of FR, because the paragraphs 
        value does not distinguish between a table and a text paragraph"""

        document_map = {
            # 'file_name': myblob_name,            
            'content': result["content"],
            "structure": [],
            "content_type": [],
            "table_index": []
        }
        document_map['content_type'].extend([ContentType.NOT_PROCESSED] * len(result['content']))
        document_map['table_index'].extend([-1] * len(result["content"]))

        # update content_type array where spans are tables
        for index, table in enumerate(result["tables"]):
            # initialize start_char and end_char based on the first span
            start_char = table["spans"][0]["offset"]
            end_char = start_char + table["spans"][0]["length"] - 1
            
            # iterate over the remaining spans
            for span in table["spans"][1:]:
                span_start = span["offset"]
                # update start_char to the minimum offset
                start_char = min(start_char, span_start)
                # update total_length by adding the length of the current span
                end_char += span["length"] -1
            
            # update the content_type array
            document_map['content_type'][start_char] = ContentType.TABLE_START
            for i in range(start_char + 1, end_char):
                document_map['content_type'][i] = ContentType.TABLE_CHAR
            document_map['content_type'][end_char] = ContentType.TABLE_END
            # tag the end point in content of a table with the index of which table this is
            document_map['table_index'][end_char] = index


        # update content_type array where spans are titles, section headings or regular content,
        # BUT skip over the table paragraphs
        for paragraph in result["paragraphs"]:
            start_char = paragraph["spans"][0]["offset"]
            end_char = start_char + paragraph["spans"][0]["length"] - 1

            # if this span has already been identified as a non textual paragraph
            # such as a table, then skip over it
            if document_map['content_type'][start_char] == ContentType.NOT_PROCESSED:
                #if not hasattr(paragraph, 'role'):
                if 'role' not in paragraph:
                    # no assigned role
                    document_map['content_type'][start_char] = ContentType.TEXT_START
                    for i in range(start_char+1, end_char):
                        document_map['content_type'][i] = ContentType.TEXT_CHAR
                    document_map['content_type'][end_char] = ContentType.TEXT_END

                elif paragraph['role'] == 'title':
                    document_map['content_type'][start_char] = ContentType.TITLE_START
                    for i in range(start_char+1, end_char):
                        document_map['content_type'][i] = ContentType.TITLE_CHAR
                    document_map['content_type'][end_char] = ContentType.TITLE_END

                elif paragraph['role'] == 'sectionHeading':
                    document_map['content_type'][start_char] = ContentType.SECTIONHEADING_START
                    for i in range(start_char+1, end_char):
                        document_map['content_type'][i] = ContentType.SECTIONHEADING_CHAR
                    document_map['content_type'][end_char] = ContentType.SECTIONHEADING_END

        # store page number metadata by paragraph object
        page_number_by_paragraph = {}
        for _, paragraph in enumerate(result["paragraphs"]):
            start_char = paragraph["spans"][0]["offset"]
            page_number_by_paragraph[start_char] = paragraph["boundingRegions"][0]["pageNumber"]

        # iterate through the content_type and build the document paragraph catalog of content
        # tagging paragraphs with title and section
        main_title = ''
        current_title = ''
        current_section = ''
        start_position = 0
        page_number = 0
        for index, item in enumerate(document_map['content_type']):

            # collect page number metadata
            page_number = page_number_by_paragraph.get(index, page_number)

            match item:
                case ContentType.TITLE_START | ContentType.SECTIONHEADING_START | ContentType.TEXT_START | ContentType.TABLE_START:
                    start_position = index
                case ContentType.TITLE_END:
                    current_title =  document_map['content'][start_position:index+1]
                    # set the main title from any title elemnts on the first page concatenated
                    if main_title == '':
                        main_title = current_title
                    elif page_number == 1:
                        main_title = main_title + "; " + current_title
                case ContentType.SECTIONHEADING_END:
                    current_section = document_map['content'][start_position:index+1]
                case ContentType.TEXT_END | ContentType.TABLE_END:
                    if item == ContentType.TEXT_END:
                        property_type = 'text'
                        output_text = document_map['content'][start_position:index+1]
                    elif item == ContentType.TABLE_END:
                        # now we have reached the end of the table in the content dictionary,
                        # write out the table text to the output json document map
                        property_type = 'table'
                        table_index = document_map['table_index'][index]
                        table_json = result["tables"][table_index]
                        output_text = table_to_html(table_json)
                    else:
                        property_type = 'unknown'
                    document_map["structure"].append({
                        'offset': start_position,
                        'text': output_text,
                        'type': property_type,
                        'title': main_title,
                        'subtitle': current_title,
                        'section': current_section,
                        'page_number': page_number
                    })

        del document_map['content_type']
        del document_map['table_index']

        if enable_dev_code:
            # Output document map to log container
            json_str = json.dumps(document_map, indent=2)
            print(f'json_str:{json_str}')


        return document_map

# Transform the Document Intelligence response into structured metadata
def get_structured_metadata(analyze_document_result):

    # TO DO

    structured_metadata = None

    return structured_metadata

# Split PDF into images (with custom resolution using zoom parameter)
def pdf_to_images(path_to_sample_document, image_output_directory='./images', zoom_x=1.5, zoom_y=1.5):
    image_path_list = []

    # Create required directories if missing
    os.makedirs(image_output_directory, exist_ok=True)

    file_name = os.path.basename(path_to_sample_document)
    child_directory_path = os.path.join(image_output_directory,file_name)    

    # Check if the child directory exists and delete it if it does
    if os.path.exists(child_directory_path):        
        shutil.rmtree(child_directory_path)
        print(f'[INFO] Previous images child directory removed')

    # Create required directories if missing
    os.makedirs(child_directory_path, exist_ok=True)

    print(f'[INFO] Reading the PDF file')
    doc = fitz.open(path_to_sample_document)

    print(f'[INFO] {doc.page_count} pages found')

    print(f'[INFO] Extracting and saving pages to images')
    for i, page in enumerate(doc):
        image_save_path = f"{os.path.join(child_directory_path, file_name)}_page_{i+1}.png"
        matrix = fitz.Matrix(zoom_x, zoom_y)  # Set the zoom factor for resolution
        pix = page.get_pixmap(matrix=matrix)
        pix.save(image_save_path)
        # print(f'[INFO] Processed page {i+1}')

        image_path_list.append(image_save_path)

    print(f'[INFO] PDF to images completed')
    return image_path_list

# Initialise AOAI client
def initialise_AOAI_client():
    
    # Initialize Azure OpenAI Service client with Entra ID authentication
    # IMP: Please assign the RBAC role 'Cognitive Services Contributor' to the user (Service principal) from Azure portal for your Azure Open AI resource. When using VS code / cmd, redo az login
    token_provider = get_bearer_token_provider(  
        DefaultAzureCredential(),  
        "https://cognitiveservices.azure.com/.default"  
    )  
    
    AOAI_client = AzureOpenAI(  
        azure_endpoint=AOAI_ENDPOINT_URL,  
        azure_ad_token_provider=token_provider,  
        api_version=AOAI_APIVERSION,  # https://github.com/Azure/azure-rest-api-specs/tree/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable
    ) 

    return AOAI_client


# # OCR document using multi-modal LLM
def llm_completion(path_to_image_list_subset, sys_message: SystemMessage, userPrompt = None, detail = "auto"):

    

    system_message_extract_title = '''
    Analyse the sequence of document pages given to you and accurately extract the complete document title from one of the first few pages given to you.

    Return in below JSON format:
    {
            "document_title": "Document title goes here"
    }

    When document title is missing in provided pages set document_title to "[missing]"

    Do not make up facts.
    Do not interpret a section name / subsection name as document title.

    To Avoid Harmful Content\n- You must not generate content that may be harmful to someone physically or emotionally even if a user requests or creates a condition to rationalize that harmful content. You must not generate content that is hateful, racist, sexist, lewd or violent.
    '''

    system_message_extract_content= '''
    Review and understand the provided page layout from top to bottom before generating output.
    Extract the text and provide it in a JSON array format shown below.
    {
        "page_content":[
            {
            "section_name":"section name",
            "parent_section_name: "Parent section name when present somewhere above the section_name on the page, DO NOT not try to calculate / guess it",
            "text: "extracted text, also include text that you could not include in any other section",
            "image_diagram_summary": "image /diagram / chart name followed by up to 10 line summary of image or diagram or figure or chart when present in section, be creative in describing, do not just say image name. Include wording on text that you are able to extract from image /diagram / chart.
                        Also include shapes / colours / flows you see as #tags",
            "contains_image_diagam": "true when image or diagram or figure or chart present, else false",
            "contains_table": "true when table present, else false"
            
            }
        ],
        "page_header": "when present, any text that appears in page header excluding page number",
        "page_footer": "when present, any text that appears in page footer excluding page number",
        "page_number" : "Page number (integer part only) when present and you are 100% confident that it is a page number"
    }

    Remember parent section is usually a section name that appears before current section, it will be or will not be followed by text under it.
    Parent section should have distinguishable style such as bigger / bold font size.
    When text is present directly under a parent section, both section_name and parent_section_name will be same.
    When you only see section names but no parent section above them, then parent_section_name should be "[missing]".
    When you only see text but no section above it, then section_name should be "[missing]".
    When you only see text but no sections above it, then both section_name and parent_section_name should be "[missing]".
    When page_header or page_footer or page_number is not present or unsure, it should be "[missing]".
    When image /diagram / figure / chart is not present or unsure, image_diagram_summary should be "[missing]".

    When table is present, make sure you include its content as HTML representation and Table name into text tag.

    Do not make up facts!
    Do not make up section_name / parent_section_name / text when you don't see it on the page!
    Do not skip numbering prefix to the section_name and parent_section_name, for example "1.1 Overview"!
    Do not interpret the image / diagram / figure / chart name as section_name or parent_section_name!
    Do not skip any text from given page, this includes section names that you did not include!

    To Avoid Harmful Content\n- You must not generate content that may be harmful to someone physically or emotionally even if a user requests or creates a condition to rationalize that harmful content. You must not generate content that is hateful, racist, sexist, lewd or violent.
    '''

    system_message_page_summary = '''
    Analyse the sequence of document pages given to you and accurately summarise them in 2-3 sentences.

    Return in below JSON format:
    {
            "page_summary": "Summary goes here"
    }

    When document content is blank / empty set page_summary to "[missing]"

    Do not make up facts.
    Do not create the summary by replicating the content as is.

    To Avoid Harmful Content\n- You must not generate content that may be harmful to someone physically or emotionally even if a user requests or creates a condition to rationalize that harmful content. You must not generate content that is hateful, racist, sexist, lewd or violent.
    '''

    system_message_document_summary = '''
    Summarise the provided content into a meaningful summary of 4-5 sentences.
    Ensure that you have covered all important information mentioned.

    Return in below JSON format:
    {
            "document_summary": "Summary goes here"
    }

    When document content is blank / empty set document_summary to "[missing]"

    Do not make up facts.
    Do not create the summary by replicating the content as is.

    To Avoid Harmful Content\n- You must not generate content that may be harmful to someone physically or emotionally even if a user requests or creates a condition to rationalize that harmful content. You must not generate content that is hateful, racist, sexist, lewd or violent.
    '''

    system_message = None
    if sys_message == SystemMessage.EXTRACT_TITLE:
        system_message = system_message_extract_title
        # print('system_message set to EXTRACT_TITLE')
    elif sys_message == SystemMessage.EXTRACT_CONTENT:
        system_message = system_message_extract_content
        # print('system_message set to EXTRACT_CONTENT')
    elif sys_message == SystemMessage.PAGE_SUMMARY:
        system_message = system_message_page_summary
        # print('system_message set to PAGE_SUMMARY')
    elif sys_message == SystemMessage.DOCUMENT_SUMMARY:
        system_message = system_message_document_summary
        # print('system_message set to DOCUMENT_SUMMARY')
  
    # To include N images into the same message (1 image for content extraction, > 1 image for title extraction)
    image_content_list = []
    for path_to_image in path_to_image_list_subset:
        
        encoded_image = base64.b64encode(open(path_to_image, 'rb').read()).decode('ascii')

        image_url_item = {
                            "type": "image_url",
                            "image_url": {
                                  "url": "data:image/jpeg;base64," + encoded_image,
                                  "detail": detail
                              }
                        }
                  
        image_content_list.append(image_url_item)


    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_message
                    }
                ]
            }        
        ] 
    
    # Add images to the message when provided, basically allowing same function to be used for LLM completions where images are not required in the input
    if len(image_content_list) > 0:
        image_content_list_message = {
                "role": "user",
                "content": image_content_list
                }
        messages.append(image_content_list_message)
    
    # print(f'messages:{messages}')

    if userPrompt is not None and len(userPrompt) > 0:
        userPrompt_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": userPrompt
                    }
                ]
            }   
        messages.append(userPrompt_message)

    completion = AOAI_client.chat.completions.create(  
    model=AOAI_DEPLOYMENT_NAME, 
    response_format={ "type": "json_object" }, 
    messages=messages,
    max_tokens=4000,  
    temperature=0,  
    top_p=0.95,  
    frequency_penalty=0,  
    presence_penalty=0,
    stop=None,  
    stream=False
    )  
  
    return completion.to_json()

# Input array of text, output list of multiple embeddings
def get_vector(input_text_list):
    
    response = AOAI_client.embeddings.create(input = input_text_list, model=AOAI_EMBEDDING_DEPLOYMENT_NAME)

    embeddings_list = [item.embedding for item in response.data]

    return embeddings_list  

# Function to divide the list into chunks of specified size  
def chunk_list(lst, chunk_size):  
    for i in range(0, len(lst), chunk_size):  
        yield lst[i:i + chunk_size]  

def get_text_metadata_image_list(path_to_sample_document, image_path_list):

    extracted_metadata_list = []
    extracted_metadata_file_list = []
    document_title = ""
    document_summary = ""

    # Extract title from top_n_pages
    top_n_pages = 3
    # Reduce top_n_pages if it's a short document
    if len(image_path_list) < top_n_pages:
        top_n_pages = len(image_path_list)

    # Directories for saving extract ---------------
    # Create required directories if missing
    os.makedirs(document_extract_directory, exist_ok=True)

    file_name = os.path.basename(path_to_sample_document)
    child_directory_path = os.path.join(document_extract_directory,file_name+'_extract')

    # Check if the child directory exists and delete it if it does
    if os.path.exists(child_directory_path):
        shutil.rmtree(child_directory_path)
        print(f'[INFO] Previous extract child directory removed')

    # Create required directories if missing
    os.makedirs(child_directory_path, exist_ok=True)

    # Title --------------------------------------
    completion_title_json = json.loads(llm_completion(image_path_list[:top_n_pages], SystemMessage.EXTRACT_TITLE, detail = image_res))  
   
    # Validate if response is error free
    if "choices" in completion_title_json and len(completion_title_json["choices"]) and "finish_reason" in completion_title_json["choices"][0] and completion_title_json["choices"][0]["finish_reason"] == 'stop':
        document_title = json.loads(completion_title_json["choices"][0]["message"]["content"])["document_title"]
    else: # In case the AOAI response is not as expected above, print it out to the user
        print(f'[ERROR]: Could not retrieve the document title')
        print(f'completion_title_json:{json.dumps(completion_title_json, indent=4)}')

    print(f'[INFO] document_title:{document_title}')
    
    # Page Summary --------------------------------------
    # Process N images at a single time    
    image_path_list_groups = list(chunk_list(image_path_list, pages_to_summarise)) 

    # Save page/s summary to create document summary
    page_summary_list = []

    for image_path_list_group in image_path_list_groups:

        completion_page_summary_json = json.loads(llm_completion(image_path_list_group, SystemMessage.PAGE_SUMMARY, detail = image_res))  
   
        # Validate if response is error free
        if "choices" in completion_page_summary_json and len(completion_page_summary_json["choices"]) and "finish_reason" in completion_page_summary_json["choices"][0] and completion_page_summary_json["choices"][0]["finish_reason"] == 'stop':
            page_summary = json.loads(completion_page_summary_json["choices"][0]["message"]["content"])["page_summary"]
        else: # In case the AOAI response is not as expected above, print it out to the user
            print(f'[ERROR]: Could not retrieve the page summary')
            print(f'completion_page_summary_json:{json.dumps(completion_page_summary_json, indent=4)}')

        # print(f'[INFO] page_summary:{page_summary}')
        page_summary_list.append(page_summary)
        
        # break  # Comment out when done debugging

    print(f'[INFO] Page summary created')

    # Document Summary --------------------------------------
    # Summary of summaries - see 1st and 3rd parameter
    completion_document_summary_json = json.loads(llm_completion([], SystemMessage.DOCUMENT_SUMMARY, " ".join(page_summary_list), detail = image_res))  
   
    # Validate if response is error free
    if "choices" in completion_document_summary_json and len(completion_document_summary_json["choices"]) and "finish_reason" in completion_document_summary_json["choices"][0] and completion_document_summary_json["choices"][0]["finish_reason"] == 'stop':
        document_summary = json.loads(completion_document_summary_json["choices"][0]["message"]["content"])["document_summary"]
    else: # In case the AOAI response is not as expected above, print it out to the user
        print(f'[ERROR]: Could not retrieve the document summary')
        print(f'document_summary:{json.dumps(completion_document_summary_json, indent=4)}')

    # print(f'[INFO] document_summary:{document_summary}')      
    print(f'[INFO] Document summary created')

    # Content --------------------------------------
    page_sequence_number = 0

    # print(f'image_path_list: {len(image_path_list)}')
    # Extract content from each page separately
    for image_path in image_path_list:

        document_content = {}

        page_sequence_number += 1
        # print(f'page_sequence_number: {page_sequence_number}')

        # print(f'image_path:{image_path}')
        completion_content_json = json.loads(llm_completion([image_path], SystemMessage.EXTRACT_CONTENT, detail = image_res))
        
        # Validate if response is error free
        if "choices" in completion_content_json and len(completion_content_json["choices"]) and "finish_reason" in completion_content_json["choices"][0] and completion_content_json["choices"][0]["finish_reason"] == 'stop':
            document_content = json.loads(completion_content_json["choices"][0]["message"]["content"])
        else: # In case the AOAI response is not as expected above, print it out to the user
            print(f'[ERROR]: Could not retrieve the document content - {image_path}')
            print(f'completion_content_json:{json.dumps(completion_content_json, indent=4)}')

        # Enrich content
        document_content["document_title"] = document_title
        document_content["document_summary"] = document_summary
        document_content["page_sequence_number"] = page_sequence_number             

        # Save dictionary to a JSON file  
        json_extract_path = f'{os.path.join(child_directory_path, os.path.basename(image_path))}.json'
        with open(json_extract_path, 'w') as json_file:  
            json.dump(document_content, json_file, indent=4)  

        extracted_metadata_list.append(document_content)
        extracted_metadata_file_list.append(json_extract_path)

        # break # Comment out when done debugging
    
    print(f'[INFO] Page content extracted from {str(page_sequence_number)} pages')        

    return extracted_metadata_list, extracted_metadata_file_list

# Add missing Sections and Parent Sections
def add_missing_metadata(extracted_metadata_list, extracted_metadata_file_list):

    # Store extracts post updates
    extracted_metadata_updated_list = []

    # print(f'len(extracted_metadata_list): {len(extracted_metadata_list)}')
    # print(f'len(extracted_metadata_file_list): {len(extracted_metadata_file_list)}')

    # Each item is a page
    for i in range(len(extracted_metadata_list)):

        # print(f'Adding missing metadata to page sequence no. {str(i+1)}')
        page_content_json = extracted_metadata_list[i]
        metadata_file_path = extracted_metadata_file_list[i]

        is_modified = False

        # Skip first page
        if i > 0:           

            # Previous page
            prev_page_content_json = extracted_metadata_list[i-1]

            # Addition 1
            # Check if there's text item present on both current and previous page
            if "page_content" in page_content_json and len(page_content_json["page_content"]) > 0 and len(prev_page_content_json["page_content"]) > 0: 

                # Check if text present for the first item of the current page
                if len(page_content_json["page_content"][0]["text"].strip()) > 0 and page_content_json["page_content"][0]["text"].strip() != "[missing]": 
                
                    # Add section_name when missing
                    # Go to last first item on the current page and check if section_name is missing
                    if page_content_json["page_content"][0]["section_name"].strip() == "[missing]":
                        
                        # Check if the last item on previous page has section_name
                        if prev_page_content_json["page_content"][len(prev_page_content_json["page_content"])-1]["section_name"].strip() != "[missing]":
                            # Add previous page's, last item's section_name if it's not missing
                            page_content_json["page_content"][0]["section_name"] = prev_page_content_json["page_content"][len(prev_page_content_json["page_content"])-1]["section_name"]
                            is_modified = True
                            # print('section_name updated')
                    
                    # Add parent_section_name when missing, and section_name is missing
                    # Go to last first item on the current page and check if parent_section_name is missing
                    if page_content_json["page_content"][0]["parent_section_name"].strip() == "[missing]" and page_content_json["page_content"][0]["section_name"].strip() == "[missing]":
                        
                        # Check if the last item on previous page has parent_section_name
                        if prev_page_content_json["page_content"][len(prev_page_content_json["page_content"])-1]["parent_section_name"].strip() != "[missing]":
                            # Add previous page's, last item's parent_section_name if it's not missing
                            page_content_json["page_content"][0]["parent_section_name"] = prev_page_content_json["page_content"][len(prev_page_content_json["page_content"])-1]["parent_section_name"]
                            is_modified = True
                            # print('parent_section_name updated')

            # Addition 2
            # Check if there's text item present on current page
            if "page_content" in page_content_json and len(page_content_json["page_content"]) > 0:

                for j in range(len(page_content_json["page_content"])):

                    # Skip first item as it's section and parent section name will be used for items immediately after it with [missing] section and parent section
                    if j > 0:

                        if page_content_json["page_content"][j]["section_name"].strip() == "[missing]" and page_content_json["page_content"][j]["parent_section_name"].strip() == "[missing]":

                            # Assign from previous - section_name
                            page_content_json["page_content"][j]["section_name"] = page_content_json["page_content"][j-1]["section_name"]

                            # Assign from previous - parent_section_name
                            page_content_json["page_content"][j]["parent_section_name"] = page_content_json["page_content"][j-1]["parent_section_name"]

                            is_modified = True


        extracted_metadata_updated_list.append(page_content_json)

        # Overwrite previous extract with updated content (if it was modified)
        if is_modified:
            
            # print(f'Page sequence {i+1} modified')

            with open(metadata_file_path, 'w') as json_file:  
                json.dump(page_content_json, json_file, indent=4)

        # print(f'page_content_json:{json.dumps(page_content_json, indent=4)}')
        # print(f'metadata_file_path:{metadata_file_path}')

    return extracted_metadata_updated_list, extracted_metadata_file_list

    
# Given a directory path, read all .json files from the directory and return list of paths and loaded content
def load_json_content_from_dir(dir_path):

    # Hydrate these 2 list we created in step 1 EXTRACT using the json export
    extracted_metadata_updated_list, extracted_metadata_file_list = [], []
    
    # Read json extracts saved by previous step based on input file selected
    json_extract_list = glob.glob(os.path.join(dir_path, '*.json')) 
    # print(f'json_extract_list:{json_extract_list}')

    # Read each JSON file into a dictionary and print it  
    for extract in json_extract_list:  
        extracted_metadata_file_list.append(extract)
        with open(extract, 'r', encoding='utf-8') as f:  
            try:  
                data = json.load(f)  
                extracted_metadata_updated_list.append(data)                
            except json.JSONDecodeError as e:  
                print(print_colorful(f"[ERROR] Error reading extract {extract}: {e}",'1;31'))                

        
    return extracted_metadata_updated_list, extracted_metadata_file_list


# Organize the text into chunks to be inserted into the AI Search index, this includes vectorization
def create_chunks(file_path, extracted_metadata_updated_list, extracted_metadata_file_list):

    # Each chunk will be an AI Search Index record
    search_document_chunks_list = []

    # Each page
    for i in range(len(extracted_metadata_updated_list)):

        # Extracted items in each page
        page_extract = extracted_metadata_updated_list[i]        
        
        # Path to the image
        page_image_path = os.path.join(
            image_output_directory,
            os.path.basename(file_path),
            os.path.basename(extracted_metadata_file_list[i]).replace('.json',''))
        
        # print(f'page_content:{json.dumps(page_content, indent=4)}')
        # print(f'page_image_path:{page_image_path}')

        # Common attributes of the page
        page_header = page_extract["page_header"] if "page_header" in page_extract and page_extract["page_header"].strip() != '[missing]' else ''
        page_footer = page_extract["page_footer"] if "page_footer" in page_extract and page_extract["page_footer"].strip() != '[missing]'  else ''        
        page_number = int(page_extract["page_number"]) if "page_number" in page_extract and page_extract["page_number"].strip() != '[missing]' and page_extract["page_number"].isdigit() else 0
        document_title = page_extract["document_title"] if "document_title" in page_extract and page_extract["document_title"].strip() != '[missing]' else ''
        document_summary = page_extract["document_summary"] if "document_summary" in page_extract and page_extract["document_summary"].strip() != '[missing]' else ''
        page_sequence_number = int(page_extract["page_sequence_number"]) if "page_sequence_number" in page_extract else 0

        # Validate if page_content exists
        if "page_content" in page_extract: 

            text_item_counter = 0
        
            chunk_dict = {}
            for text_item in page_extract["page_content"]: # Child items, paragraphs etc.

                text_item_counter += 1

                # print(f'text_item:{text_item}')

                # Ensure text is not blank, else skip adding chunk to ensure blank text does not get added to AI Search index
                if "text" in text_item and text_item["text"].strip() != '' and text_item["text"].strip() != '[missing]':

                    file_name = os.path.basename(file_path)
                    section = text_item["section_name"] if "section_name" in text_item and text_item["section_name"].strip() != '[missing]' else ''
                    parent_section = text_item["parent_section_name"] if "parent_section_name" in text_item and text_item["parent_section_name"].strip() != '[missing]' else ''
                    text = text_item["text"] if "text" in text_item and text_item["text"].strip() != '[missing]' else ''

                    image_flag = True if "contains_image_diagam" in text_item and text_item["contains_image_diagam"].strip() != '[missing]' and text_item["contains_image_diagam"].strip().upper() == 'true'.upper() else False
                    image_diagram_summary =  text_item["image_diagram_summary"] if "image_diagram_summary" in text_item and text_item["image_diagram_summary"].strip() != '[missing]' else ''
                    
                    text_content = f'''  
                    {'----'}              
                    {'Page header: ' + page_header if page_header else ''}
                    {'----'}
                    {'Document title: ' + document_title if document_title else ''}
                    {'Document summary: ' + document_summary if document_summary else ''}
                    {'----'}
                    {'Prent section name: ' + parent_section if parent_section else ''}
                    {'Section name: ' + section if section else ''}                
                    {'Text content: ' + text if text else ''}

                    {'Summary of image / diagram (if present): ' + image_diagram_summary if image_diagram_summary else ''}

                    {'----'}
                    {'Page footer: ' + page_footer if page_footer else ''}
                    {'Printed page number (if present): ' + str(page_number) if page_number > 0 else ''}
                    {'Page sequence number: ' + str(page_sequence_number) if page_sequence_number > 0 else ''}
                    {'----'}
                    '''
                    # print(f'text_content:{text_content}')

                    # Vectorize: section, parent_section, text_content
                    section_vector, parent_section_vector, text_content_vector = [], [], []
                    vector_input_list = [] # To get all embeddings in a single call
                    vector_input_tags = [] # To remember which tag the embedding belongs to

                    if section:                        
                        vector_input_list.append(section)
                        vector_input_tags.append('section')
                    if parent_section:                        
                        vector_input_list.append(parent_section)
                        vector_input_tags.append('parent_section')
                    if text_content:                        
                        vector_input_list.append(text_content)
                        vector_input_tags.append('text_content')

                    # Validate if non-empty text was added
                    if len(vector_input_list) > 0:
                        vector_output_list =  get_vector(vector_input_list)

                    # Assign the embedding to respective tag as this was obtained in a single call
                    for j in range(len(vector_input_tags)):
                        input_tag_name = vector_input_tags[j]

                        if input_tag_name == 'section':
                            section_vector = vector_output_list[j]
                        elif input_tag_name == 'parent_section':
                            parent_section_vector = vector_output_list[j]
                        elif input_tag_name == 'text_content':
                            text_content_vector = vector_output_list[j]


                    chunk_dict = {
                        "id": urlsafe_encode("user_id" + '_' + file_name + '_' + str(page_sequence_number)+ '_' + str(text_item_counter)), # To make unique combination per chunk and encode to remove unwanted chars
                        "file_name": file_name,
                        "file_path": file_path,  
                        "extracted_title": document_title,
                        "section": section,  
                        "parent_section": parent_section,  
                        "text_content": text_content,  
                        "image_flag": image_flag,  
                        "page_sequence_number": page_sequence_number,  
                        "page_number": page_number,  
                        "page_image_path": page_image_path,    
                        "document_summary":document_summary,
                        "user_id": user_id,  
                        "section_vector": section_vector,  
                        "parent_section_vector": parent_section_vector,  
                        "text_content_vector": text_content_vector 
                        }  
                    
                    # print(f'chunk_dict:{json.dumps(chunk_dict, indent=4)}')

                    search_document_chunks_list.append(chunk_dict)

        # break # Comment post debugging

    # Save chunk list in file for review / debugging    
    # Create required directories if missing
    os.makedirs(chunk_export_directory, exist_ok=True)
    jsonl_child_directory_path = os.path.join(chunk_export_directory, file_name)
    os.makedirs(jsonl_child_directory_path, exist_ok=True)
    jsonl_path = os.path.join(jsonl_child_directory_path, 'chunks.jsonl')

    # Write the list of dictionaries to a JSONL file  
    with open(jsonl_path, 'w') as file:  
        for item in search_document_chunks_list:  
            json_line = json.dumps(item)  
            file.write(json_line + '\n') 
    print(f'[INFO] Chunks exported locally')

    return search_document_chunks_list
        
# https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/search/azure-search-documents/samples
def ingest_chunks(search_document_chunks_list):
    
    credential = DefaultAzureCredential()

    # search_client = SearchClient(AI_SEARCH_ENDPOINT, AI_SEARCH_INDEX_NAME, credential) # Entra Auth
    search_client = SearchClient(AI_SEARCH_ENDPOINT, AI_SEARCH_INDEX_NAME, AzureKeyCredential(AI_SEARCH_KEY))
    print('[INFO] AI Search client initialised')

    # 1000 item per batch limit
    # https://learn.microsoft.com/en-us/azure/search/search-what-is-data-import#pushing-data-to-an-index
    batches_list = chunk_list(search_document_chunks_list, AI_Search_batch_size) # Keep it below 1000 items

    for batch in batches_list:

        print(f'[INFO] Uploading {len(batch)} documents')
        result = search_client.merge_or_upload_documents(documents=batch)    
        print("[INFO] Upload of {} documents succeeded".format(sum(1 for r in result if r.succeeded)))          


############################ Code ############################


# Take user input
input_scenario = input(print_colorful('\nSelect scenario [1] EXTRACT [2] UPLOAD [3] QUERY [4] COMPARE: ','1;34'))

# Validate
if input_scenario not in [str(scenario.value) for scenario in Scenarios]:
    print(print_colorful('❌ Invalid input, please try again.','1;31'))
    sys.exit(1)

# print(f'scenario:{Scenarios(int(input_scenario))}')

# Handle document EXTRACT scenario
if Scenarios(int(input_scenario)) == Scenarios.EXTRACT:
    print(print_colorful(f'✅ You have selected {Scenarios(int(input_scenario))}', '1;32'))

    # Dynamically show file names based on available files in this format [key1] filename.extension [key2] filename.extension ...
    user_text = '\n'+' '.join([f'[{key}] {os.path.basename(path)}' for key, path in file_paths_dict.items()]) + ': '
    selected_document = input(user_text)    
    
    # Validate
    if selected_document not in [str(sampledocs.value) for sampledocs in SampleDocs]:
        print(print_colorful('❌ Invalid document, please try again.','1;31'))
        sys.exit(1)

    print(print_colorful(f'✅ You have selected {SampleDocs(int(selected_document))}', '1;32'))

    file_path = file_paths_dict[int(selected_document)]
    print(f'[INFO] File path:{file_path}')

    # # Doc. Intelligence OPTION
    # print(f'[INFO] Document analysis started')
    # analyze_document_result = analyze_document(file_path)
    # # print(analyze_document_result)
    # print(f'[INFO] Document analysis completed')

    # print(f'[INFO] Structure transformation started')
    # # get_structured_metadata(analyze_document_result)
    # build_document_map_pdf(analyze_document_result, enable_dev_code=True)
    # print(f'[INFO] Structure transformation completed')    
    
    # Multi-modal LLM OPTION
    # Convert PDF pages to images
    image_path_list = pdf_to_images(file_path, image_output_directory = image_output_directory)

    # Multi-modal LLM
    AOAI_client = initialise_AOAI_client()
    print(f'[INFO] AOAI client initialised')

    print(f'[INFO] Document content extraction started')
    extracted_metadata_list, extracted_metadata_file_list = get_text_metadata_image_list(file_path, image_path_list)
    # print(f'extracted_metadata_list:{json.dumps(extracted_metadata_list[0], indent=4)}')
    print(f'[INFO] Document content extraction completed')

    # Handle when Sections break across multiple pages, use previous last Section name as Section name of first [missing] section, overwrite JSON file.
    # Add missing Sections and Parent Sections
    extracted_metadata_updated_list, extracted_metadata_file_list = add_missing_metadata(extracted_metadata_list, extracted_metadata_file_list)
    print(f'[INFO] Missing informations added')

elif Scenarios(int(input_scenario)) == Scenarios.UPLOAD: # Handle document UPLOAD to AI Search scenario

    # Select file from user input
    print(print_colorful(f'✅ You have selected {Scenarios(int(input_scenario))}', '1;32'))

    # Dynamically show file names based on available files
    user_text = '\n'+' '.join([f'[{key}] {os.path.basename(path)}' for key, path in file_paths_dict.items()]) + ': '
    selected_document = input(user_text)

    # Validate
    if selected_document not in [str(sampledocs.value) for sampledocs in SampleDocs]:
        print(print_colorful('❌ Invalid document, please try again.','1;31'))
        sys.exit(1)

    print(print_colorful(f'✅ You have selected {SampleDocs(int(selected_document))}', '1;32'))

    file_path = file_paths_dict[int(selected_document)]
    print(f'[INFO] File path:{file_path}')

    # path_to_sample_document
    file_name = os.path.basename(file_path)
    child_directory_path = os.path.join(document_extract_directory,file_name+'_extract') # This is where the extracts were created by previous EXTRACT step
    # print(f'child_directory_path:{child_directory_path}')

    # Read json extracts saved by previous step EXTRACT based on input file selected  
    extracted_metadata_updated_list, extracted_metadata_file_list = load_json_content_from_dir(child_directory_path)
    print(f'[INFO] Extracts loaded')
    # print(f'len(extracted_metadata_updated_list):{len(extracted_metadata_updated_list)}')
    # print(f'len(extracted_metadata_file_list):{len(extracted_metadata_file_list)}')
    # print(f'extracted_metadata_updated_list[0]:{json.dumps(extracted_metadata_updated_list[0], indent=4)}')

    # Validate if extracts present
    if not extracted_metadata_file_list or not extracted_metadata_updated_list:
        print(print_colorful('❌ No extracts found, please run the EXTRACT step first.','1;31'))
        sys.exit(1)

    # Validate if extracts were loaded without errors
    if extracted_metadata_file_list and extracted_metadata_updated_list and len(extracted_metadata_file_list) != len(extracted_metadata_updated_list):
        print(print_colorful('❌ Some extracts loading encoutred errors, exiting the code.','1;31'))
        sys.exit(1)

    # Multi-modal LLM
    AOAI_client = initialise_AOAI_client()
    print(f'[INFO] AOAI client initialised')

    # Create chunks - section, sub section, text, image summary, vectors
    # Organize the text into chunks to be inserted into the AI Search index, this includes vectorization
    print(f'[INFO] Creating chunks')
    search_document_chunks_list = create_chunks(file_path, extracted_metadata_updated_list, extracted_metadata_file_list)
    # print(f'len(search_document_chunks_list):{len(search_document_chunks_list)}')
    print(f'[INFO] Chunks creation completed')

    # Ingest into AI Search index    
    print(f'[INFO] Ingesting chunks to AI Search')
    
    ingest_chunks(search_document_chunks_list)

    print(f'[INFO] Chunk ingestion to AI Search completed')


else:
    print(print_colorful('🚧 Coming soon, not implemented yet.','1;33'))
    sys.exit(1)