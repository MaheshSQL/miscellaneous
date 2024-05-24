import base64 

#This file is used to simulate the actual input to the RunPromptOnImage function which will have image as 'base64String' input in request

# Please see file postman_test_payload.txt and add it's content to body of request to http://localhost:7071/api/RunPromptOnImage in postman

with open("./images/presentation.png", "rb") as image2string: 
	converted_string = base64.b64encode(image2string.read())
	# print(converted_string) 
	
with open('./images/encode.bin', "wb") as file: 
    file.write(converted_string)