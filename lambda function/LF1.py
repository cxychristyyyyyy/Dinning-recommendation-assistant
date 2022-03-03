import json
import dateutil.parser
import datetime
import time
import os
import math
import random
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }
    
    

""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None



def isvalid_date(date):
    try:
        # ----------------------------------------------
        dateutil.parser.parse(date)
        
        return True
    except ValueError:
        return False

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            'isValid': is_valid,
            'violatedSlot': violated_slot
        }
    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_suggestion(slots):
    location = try_ex(lambda: slots['Location'])
    cuisine = try_ex(lambda:slots['Cuisine'])
    dining_date = try_ex(lambda:slots['DiningDate'])
    dining_time = try_ex(lambda:slots['DiningTime'])
    num_of_people = try_ex(lambda:slots['NumberofPPL'])
    phone_number = try_ex(lambda:slots['Phone'])
    email = try_ex(lambda:slots['Email'])
    
    valid_cities = ['new york', 'nyc', 'new york city', 'ny', 'manhattan', 'brooklyn', 'queens']
    cuisine_types = ['chinese', 'thai', 'american',  'italian', 'japanese']
    if location is not None and location.lower() not in valid_cities:
        return build_validation_result(False, 'Location', 'Sorry, {} is not a valid location. Try another location please'.format(location))
    
    if cuisine is not None and cuisine.lower() not in cuisine_types:
        return build_validation_result(False, 'Cuisine', 'Sorry,  {} is not a valid cuisine type. Try another cuisine type please.'.format(cuisine))
        
    if dining_date is not None:
        if not isvalid_date(dining_date):
            return build_validation_result(False, 'DiningDate', 'Sorry, this is not a valid date. Could you please give me a valid date?')
        elif datetime.datetime.strptime(dining_date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'DiningDate', 'The date you gave has already passed. Try a different date please.')
            
    if dining_time is not None:
        if len(dining_time) != 5:
            return build_validation_result(False, 'DiningTime', 'I did not recognize that, what time would you like to book your appointment?')

        hour, minute = str(dining_time).split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            return build_validation_result(False, 'DiningTime', 'I did not recognize that, what time would you like to book your appointment?')

        dinner_time = hour * 60 + minute
        now_time = datetime.datetime.now()
        if datetime.datetime.strptime(dining_date, '%Y-%m-%d').date() == datetime.date.today() and dinner_time - (now_time.hour * 60 + now_time.minute) < 60:
            return build_validation_result(False, 'DiningTime', 'Reservations must be scheduled at least one hour in advance. Could you please try another time?')
            

    if num_of_people is not None and (int(num_of_people) < 1):
        return build_validation_result(False, 'NumberofPPL', 'Sorry, the number of people cannot be less than one. How many people do you have?')
        
    if phone_number is not None:
        if not phone_number.isnumeric() or len(phone_number) != 10:
            return build_validation_result(False, 'Phone', 'Sorry,  this is not a valid phone number. Please enter a valid phone number.') 
            

    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """

def greetings(intent_request):
    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        output_session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Hi there, how can I help?'
        }
    )
    
def thank_you(intent_request):
    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        output_session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'You are welcome! Thank you for using this recommendation bot!'
        }
    )


def dining_suggestions(intent_request):
    location = intent_request['currentIntent']['slots']['Location']
    cuisine = intent_request['currentIntent']['slots']['Cuisine']
    dining_date = intent_request['currentIntent']['slots']['DiningDate']
    dining_time = intent_request['currentIntent']['slots']['DiningTime']
    num_of_people = intent_request['currentIntent']['slots']['NumberofPPL']
    phone_number = intent_request['currentIntent']['slots']['Phone']
    email = intent_request['currentIntent']['slots']['Email']
    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    source = intent_request['invocationSource']
    
    if source == 'DialogCodeHook':
        slots = intent_request['currentIntent']['slots']
        validation_result = validate_suggestion(slots)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                output_session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        return delegate(output_session_attributes, slots)
        
    elif source == 'FulfillmentCodeHook':
        sqs = boto3.client('sqs', aws_access_key_id="", aws_secret_access_key="")
        url = sqs.get_queue_url(QueueName='slotsQueue')
        queue_url = url['QueueUrl']
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageAttributes={
                'Location':{
                    'DataType': 'String',
                    'StringValue': location
                },
                'Cuisine':{
                    'DataType': 'String',
                    'StringValue': cuisine
                },
                'Dining_date':{
                    'DataType': 'String',
                    'StringValue': dining_date
                },
                'Dining_time':{
                    'DataType': 'String',
                    'StringValue': dining_time
                },
                'Number_of_people':{
                    'DataType': 'Number',
                    'StringValue': str(num_of_people)
                },
                'Phone_number':{
                    'DataType': 'String',
                    'StringValue': str(phone_number)
                },
                'Email':{
                    'DataType': 'String',
                    'StringValue': str(email)
                }
            },
            MessageBody=('Customer information input in chatbot')
        )
        
        print('Message id for this response msg is {}'.format(response['MessageId']))
        
        return close(
            output_session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': ' You’re all set. Expect my suggestions shortly! Have a good day.'
            }
        )


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':
        return greetings(intent_request)
    elif intent_name == 'ThankYouIntent':
        return thank_you(intent_request)
    elif intent_name == 'DiningSuggestionsIntent':
        return dining_suggestions(intent_request)
    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)



