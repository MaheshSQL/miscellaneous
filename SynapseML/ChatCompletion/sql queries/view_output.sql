
SELECT TOP (1000) 
	   [Date]
      ,[Hotel]
      ,[Highlights]
      ,[Review Comments]
      ,[messages_json]
      ,[chat_completions_json]
      ,[error_json]
	  	  
	  ,JSON_VALUE(JSON_QUERY([chat_completions_json], '$.choices[0].message'),'$.role') AS Output_role
	  ,JSON_VALUE(JSON_VALUE(JSON_QUERY([chat_completions_json], '$.choices[0].message'),'$.content'),'$.sentiment') AS Output_sentiment
	  ,JSON_VALUE(JSON_VALUE(JSON_QUERY([chat_completions_json], '$.choices[0].message'),'$.content'),'$.identified_action') AS Output_identified_action
	  ,JSON_VALUE(JSON_VALUE(JSON_QUERY([chat_completions_json], '$.choices[0].message'),'$.content'),'$.action_type') AS Output_action_type

FROM [dbo].[HotelReviews_Out]
WHERE 
	JSON_VALUE(JSON_QUERY([chat_completions_json], '$.choices[0].message'),'$.role') = 'assistant'