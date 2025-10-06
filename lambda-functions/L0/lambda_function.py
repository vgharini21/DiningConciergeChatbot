import json
import boto3

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime')

def lambda_handler(event, context):
    print(event)
    print(context)
    
    msg_from_user = event['messages'][0]['unstructured']['text']

    # Initiate conversation with Lex
    response = client.recognize_text(
        botId='XOQKKRG4CQ',         
        botAliasId='SXGAFMZRNX',    
        localeId='en_US',
        sessionId="default",
        text=msg_from_user)

    print(response)    
    
    # Get message from Lex
    msg_from_lex = response.get('messages', [])

    print(msg_from_lex)
  
    unstructured_message = {
        'type': 'unstructured',
        'unstructured': {
            'text': msg_from_lex[0]['content']
        }
    }
    
    resp = {
        'statusCode': 200,
        'messages': [unstructured_message]
    }
    return resp