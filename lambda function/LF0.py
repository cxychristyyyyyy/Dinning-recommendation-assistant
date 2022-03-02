import json
import boto3

print('Loading function')



def lambda_handler(event, context):
    client = boto3.client('lex-runtime')

    # message
    msg = event['messages'][0]

    input_msg = msg["unstructured"]["text"]

    response = client.post_text(botName='RecommendateBot',
                                botAlias='restaurantRecommendation',
                                userId='123456',
                                inputText=input_msg)

    response_msg = response['message']

    # form the response to the users
    if response_msg is not None:
        ans = {
            'statusCode': 200,
            'messages': [
                {
                    "type": "unstructured",
                    "unstructured": {
                        "text": response_msg
                    }
                }

            ]
        }

        return ans