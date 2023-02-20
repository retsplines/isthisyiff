import os
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
RESOURCE_CROP_ROOT_URL = 'https://source-images.isthisyiff.retsplin.es/crop/'
RESOURCE_ORIG_ROOT_URL = 'https://source-images.isthisyiff.retsplin.es/'

# Define e621 URL for source links
E621_POST_URL = 'https://e621.net/posts/'

# Define report reasons
REPORT_REASONS = ['wrong_rating', 'copyright', 'unsuitable']

# Define the SNS topic for reports
REPORTS_SNS_ARN = os.environ.get('REPORTS_SNS_ARN', None)

# Creating the DynamoDB Client
dynamodb_client = boto3.client('dynamodb', region_name="eu-west-1")

# Create an SNS client
sns_client = boto3.client('sns')

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

    raise Exception('Failed to retrieve a random post after %d attempts' % attempts)

def get_post(post_uuid):
    """
    Return a post by UUID.
    """
    response = dynamodb_client.get_item(
        TableName=TABLE_NAME,
        Key={
            'uuid': {'S': post_uuid}
        }
    )
    
    if not response or 'Item' not in response:
        raise Exception('Could not find a post with UUID %s' % post_uuid)
        
    return response['Item']

def increment_post_counter(post_uuid, was_correct):
    """
    Increment counters on a post.
    """
    dynamodb_client.update_item(
        TableName=TABLE_NAME,
        Key={
            'uuid': {'S': post_uuid}
        },
        UpdateExpression=("ADD %s :inc" % ('correct_guesses' if was_correct else 'incorrect_guesses')),
        ExpressionAttributeValues={
            ":inc": {'N': "1"}
        }
    )
    
def increment_report_reason_count(post_uuid, reason):
    """
    Increment a report reason counter.
    """
    
    # Suitable reason?
    if reason not in REPORT_REASONS:
        raise Exception('Invalid report reason. Options are %s' % (','.join(REPORT_REASONS)))
    
    # Publish a notification
    sns_client.publish(
        TargetArn=REPORTS_SNS_ARN,
        Message=json.dumps({
            'default': json.dumps({
                'uuid': post_uuid,
                'reason': reason
            }),
            'email': 'A user reported a post for reason: ' + reason + '<br><br>' + \
                'View: https://isthisyiff.retsplin.es/#' + post_uuid
        }),
        MessageStructure='json',
        Subject='Reported content on IsThisYiff: ' + post_uuid + ' (' + reason + ')'
    )
    
    dynamodb_client.update_item(
        TableName=TABLE_NAME,
        Key={
            'uuid': {'S': post_uuid}
        },
        UpdateExpression=("ADD %s :inc" % ('reports_' + reason)),
        ExpressionAttributeValues={
            ":inc": {'N': "1"}
        }
    )
    
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

def route_post_report_challenge(event, context):
    """
    POST /challenge/{post_uuid}/report/{reason}
    """
    post_uuid = event['pathParameters']['post_uuid']
    reason = event['pathParameters']['reason']
    
    # Find the post to ensure it exists
    post = get_post(post_uuid)
    
    # Update the post
    increment_report_reason_count(post_uuid, reason)
    return build_json_response({})
    
def route_get_challenge(event, context):
    """
    GET /challenge
    Gets a new challenge.
    """
    
    post_uuid = event['pathParameters']['post_uuid'] if event['pathParameters'] and event['pathParameters']['post_uuid'] else None
    post = get_post(post_uuid) if post_uuid is not None else get_random_post()
        
    stripped_post = {
        'uuid': post['uuid']['S'],
        'crop': {
            'url': RESOURCE_CROP_ROOT_URL + post['crop']['S'],
            'width': int(post['crop_width']['N']),
            'height': int(post['crop_height']['N'])
        }
    }
    return build_json_response(stripped_post)

def route_post_challenge(event, context):
    """
    POST /challenge/{post_uuid}/{guess}
    Checks the response to a challenge.
    """
    post_uuid = event['pathParameters']['post_uuid']
    guess = event['pathParameters']['guess']
    
    # Valid guess?
    if guess not in ['s', 'e']:
        raise Exception('Challenge guesses must be either "s" or "e"')
    
    # Find the post with this UUID
    post = get_post(post_uuid)
    
    # Correct?
    correct = post['rating']['S'] == guess
    
    # Increment the appropriate counter
    increment_post_counter(post_uuid, correct)
    
    result = {
        'uuid': post['uuid']['S'],
        'source': {
            'id': int(post['id']['N']),
            'url': E621_POST_URL + str(post['id']['N']),
            'fav_count': int(post['fav_count']['N']),
            'score': int(post['score']['N'])
        },
        'result': {
            'actual': post['rating']['S'],
            'guess': guess
        },
        'orig': {
            'url': RESOURCE_ORIG_ROOT_URL + post['orig']['S'],
            'width': int(post['orig_width']['N']),
            'height': int(post['orig_height']['N'])
        },
        'crop': {
            'url': RESOURCE_CROP_ROOT_URL + post['crop']['S'],
            'width': int(post['crop_width']['N']),
            'height': int(post['crop_height']['N']),
            'position': {
                'left': int(post['crop_left']['N']),
                'top': int(post['crop_top']['N'])
            }
        },
        'statistics': {
            'correct_guesses': int(post['correct_guesses']['N']),
            'incorrect_guesses': int(post['incorrect_guesses']['N'])
        }
    }
    
    return build_json_response(result)

def lambda_handler(event, context):
    """
    Handle an HTTP request.
    """
    
    logger.info('%s %s' % (event['httpMethod'], (event['path'])))
    
    routes = {
        'GET /challenge': route_get_challenge,
        'GET /challenge/{post_uuid}': route_get_challenge,
        'POST /challenge/{post_uuid}/{guess}': route_post_challenge,
        'POST /challenge/{post_uuid}/report/{reason}': route_post_report_challenge
    }
    
    # Route the request
    resource_name = event['requestContext']['resourceId']
    
    # Handle errors that occur during dispatch
    try:

        # Dispatch to the appropriate route
        if resource_name in routes:
            return routes[resource_name](event, context)
        else:
            return build_json_response({
                'error': 'uwu 404 not found sorry hehe'
            }, 404)
        
    except Exception as e: 
        return build_json_response({
            'folf': 'sad :(',
            'error': str(e)
        }, 500)

