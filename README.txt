COMS6998 HW1 Dining Concierge Assistant

xc2551 Xiaoyue Chen
ml4687 Meiyou Liu


s3 frontend url:
http://restaurantrecommend.s3-website-us-east-1.amazonaws.com

Brief overview
Customer Service is a core service for a lot of businesses around the world and it is getting disrupted at the moment by Natural Language Processing-powered applications. In this first assignment you will implement a serverless, microservice-driven web application. Specifically, you will build a Dining Concierge chatbot that sends you restaurant suggestions given a set of preferences that you provide the chatbot with through conversation.

Outline of our implementation
1.Built and deployed the frontend of the application and hosted it in a aws S3 bucket.
2.Built an API for the application using API Gateway
    The API takes input from the frontend and delivers to the backend along with providing response to the frontend once the processing in the backend is done
    Lambda function (LF0) is created to perform chat functions
    Enabled CORS on our API methods and generate an SDK for our API.
3.Built the dining concierge chatbot using Amazon Lex
    Create a Lambda function (LF1) and use it as a code hook for Lex, which essentially entails the invocation of our Lambda before Lex responds to any of our requests -- this gives us the chance to manipulate and validate parameters as well as format the bot’s response.
    In LF1 we implemented:
        a.Three intents: Greeting Intent, Thank you intent and Dining Suggestion intent
        b.For the Dining Suggestions Intent, the system collects the following pieces of information from the user, through conversation:
            Location
            Cuisine
            Dining Time
            Number of people
            Phone number
            Email
        c.Verified whether the information entered by the user is valid. If the input is incorrect, notify the user to re-enter valid information.
        d.Based on the parameters collected from the user, the system pushes the information collected from the user (location, cuisine, etc.) to an SQS queue (Q1).
            The system also confirms to the user that it has received their request and that it will notify them over SES once it has the list of restaurant suggestions.
4.Integrated the Lex chatbot into our chat API
    call our Lex chatbot from the API Lambda (LF0).
    What our LF0 does:
        a.extracts the text message from the API request,
        b.send it to the Lex chatbot
        c.Waits for the response
        d.Sends back the response from Lex as the API response.
5.Used the Yelp API to collect 5,000+ random restaurants from different locations in New York.
    1000 restaurants of each of the following five cuisines: Chinese, Thai, Italian, American, Japanese
    Location contains: ['new york', 'nyc', 'new york city', 'ny', 'manhattan', 'brooklyn', 'queens']
    Stored the data collected from Yelp in DynamoDB
        a.Created a DynamoDB table named ‘yelp-restaurants’
        b.Made the id of each restaurant as the primary key
        c.Store those features that are necessary for our recommendation. ( Business ID, Name, Address, Catagories, Number of Reviews, Rating, Zip Code, Display phone number)
6.Created an ElasticSearch instance using the AWS ElasticSearch Service for indexing of the Yelp data.
    a. Using command line to create index restaurants in open search.
    b. Query the restaurants from yelp-api based on cuisines we supported.
    c. Store the cuisine and restaurants id into json format.
    d. Using command line to upload the json file into the index.
7.Built a suggestion module, that is decoupled from the Lex chatbot.
    Created a new Lambda function (LF2) that acts as a queue worker. Whenever it is invoked it:
        a.pulls a message from the SQS queue (Q1),
        b.gets a random restaurant recommendation for the cuisine collected through conversation from ElasticSearch
        c.gets the restaurants' information from DynamoDB
        c.formats them and sends them over email to the email address included in the SQS message, using SES.
        d.the email contains the name, address and rating on yelp information of the recommended restaurants.
8.Set up a CloudWatch event trigger that runs every minute and invokes the Lambda function 2.