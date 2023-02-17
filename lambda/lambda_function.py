import sys
import logging
import uuid
import json
import boto3
import random

# Set up the logging subsystem
logger = logging.getLogger()
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stderr)
stdout_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(stdout_handler)

# Define the DynamoDB Table Name
TABLE_NAME = "isthisyiff"

# Define the resource root
RESOURCE_CROPPED_ROOT_URL = 'https://source-images.isthisyiff.retsplin.es/crop/'
RESOURCE_FULL_ROOT_URL = 'https://source-images.isthisyiff.retsplin.es/'

# Creating the DynamoDB Client
dynamodb_client = boto3.client('dynamodb', region_name="eu-west-1")

def get_random_post(attempts=5):
    """
    Return a random post.
    """
    for attempt in range(attempts):
        try:
            response = dynamodb_client.scan(
                TableName=TABLE_NAME,
                Limit=1,
                ExclusiveStartKey={
                    'uuid': {'S': str(uuid.uuid4())}
                }
            )
            return response['Items'][0]
        except Exception as e:
            logging.warn('get_random_post() attempt %d failed: %s' % (attempt, e))

    raise RuntimeError('Failed to retrieve a random post after %d attempts' % attempts)

def build_json_response(content, status=200):
    """
    Build and return a response object.
    """
    return {
        "statusCode": status,
        "body": json.dumps(content),
        "headers": {
            "Content-Type": "application/json",
            "X-UwU-or-OwO": random.choice(['UwU', 'OwO'])
        }
    }

def route_get_challenge():
    """
    GET /challenge
    """
    post = get_random_post()
    stripped_post = {
        'uuid': post['uuid']['S'],
        'crop_url': RESOURCE_CROPPED_ROOT_URL + post['crop']['S']
    }
    return build_json_response(stripped_post)

def route_post_response():
    """
    POST /response
    """
    post = get_random_post()
    stripped_post = {
        'uuid': post['uuid']['S'],
        'crop_url': RESOURCE_CROPPED_ROOT_URL + post['crop']['S']
    }
    return build_json_response(stripped_post)

def lambda_handler(event, context):
    """
    Handle an HTTP request.
    """
    
    print(event)

    logger.info('%s %s' % (event['httpMethod'], (event['resource'])))

    # Handle errors that occur during dispatch
    try:

        # Dispatch to the appropriate route
        if (event['resource'] == '/challenge' and event['httpMethod'] == 'GET'):
            return route_get_challenge()
        elif (event['resource'] == '/response' and event['httpMethod'] == 'POST'):
            return build_json_response(get_random_post())
        else:
            return build_json_response({
                'error': 'uwu 404 not found sorry hehe'
            }, 404)
        
    except Exception as e: 
        return build_json_response({
            'error': str(e)
        }, 500)

