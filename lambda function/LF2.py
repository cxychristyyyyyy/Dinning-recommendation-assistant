import json
import boto3
import requests
# from requests_aws4auth import AWS4Auth
import urllib3
import random


def lambda_handler(event, context):
    # get the auth info
    region = 'us-east-1'
    service = 'es'

    # create SQS client
    sqs = boto3.client('sqs', region_name=region)



    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=["Location", "Cuisine", "Dining_date", "Dining_time", "Number_of_people", "Phone_number",
                               "Email"],
        VisibilityTimeout=60,
        WaitTimeSeconds=0
    )

    print(response)
    
    # get the slots info from the responce
    message = response["Messages"][0]

    Location = message["MessageAttributes"]["Location"]["StringValue"]
    Cuisine = message["MessageAttributes"]["Cuisine"]["StringValue"]
    Dining_date = message["MessageAttributes"]["Dining_date"]["StringValue"]
    Dining_time = message["MessageAttributes"]["Dining_time"]["StringValue"]
    Number_of_people = message["MessageAttributes"]["Number_of_people"]["StringValue"]
    Phone_number = message["MessageAttributes"]["Phone_number"]["StringValue"]
    Email = message["MessageAttributes"]["Email"]["StringValue"]

    # get the receiptHandle for deleting the message
    receiptHandle = message["ReceiptHandle"]

    # delete the message in the SQS
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receiptHandle)

    # get the awsauth
    region = 'us-east-1'
    service = 'es'


    index = "restaurants"
    url = host + "/" + index + "/_search?q=" + str(Cuisine)

    r = requests.get(url, auth=auth)

    # make the reponse into the json format:
    dataset = json.loads(r.text)
    print(dataset)

    # randomly pick three restaurants from the datatset
    randomIndexList = random.sample(range(0, len(dataset["hits"]["hits"])), 3)

    # get the table in the DynamoDB
    db = boto3.resource('dynamodb', region_name=region)
    table = db.Table('yelp-restaurants')

    # initialize the message to be sent to the users.
    snsMessage = ""
    slots = []

    # randomly select the three restaurants from the datatset and get the detail of the restaurants from the db
    for i in range(3):
        randomIndex = randomIndexList[i]
        businessId = dataset["hits"]["hits"][randomIndex]["_source"]["RestaurantID"]

        restaurant = table.get_item(
            Key={"id": businessId}
        )
        print(restaurant)

        name = restaurant["Item"]["name"]
        address = restaurant["Item"]["address"]
        rating = restaurant["Item"]["rating"]
        msg = "{}. {} located at {}, which the rating on the Yelp is {}.\r\n".format(i + 1, name, address, rating)
        snsMessage = snsMessage + msg
        slots = slots + [name] + [address] + [rating]

    # send the email using SES service
    ses = boto3.client('ses', region_name=region)
    html = """<html>
        <head> </head>
        <body>
          <h1>Your restaurants suggestions!</h1>
          <p> Hello, Here are my {} restaurant suggestions for {} people, for {} at {}:</p >
          <p> 1. {}, located at {}, which the rating on the Yelp is {}. </p >
          <p> 2. {}, located at {}, which the rating on the Yelp is {}. </p >
          <p> 3. {}, located at {}, which the rating on the Yelp is {}. </p >
          <p> Enjoy your meal!! </p >
        </body>
        </html>
                """.format(Cuisine, Number_of_people, Dining_date, Dining_time,
                           slots[0], slots[1], slots[2],
                           slots[3], slots[4], slots[5],
                           slots[6], slots[7], slots[8])
    response = ses.send_email(
        Source='xc2551@columbia.edu',
        Destination={
            'ToAddresses': [Email]
        },
        Message={
            'Subject': {
                'Data': 'Restaurants Recommendation for you!'
            },
            'Body': {
                'Text': {
                    'Data': 'hello!'
                },
                'Html': {
                    'Data': html
                }
            }
        }
    )