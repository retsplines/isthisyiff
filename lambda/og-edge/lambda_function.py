"""
A Lambda@Edge Viewer Request function that produces a dummy HTML page response for /challenge/... requests
to allow customisation of the og:image and twitter:image cards.
"""

import sys
import re
import logging
import boto3

# Define the DynamoDB Table Name
TABLE_NAME = "isthisyiff"

# Creating the DynamoDB Client
dynamodb_client = boto3.client('dynamodb', region_name="eu-west-1")

CONTENT = """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Is This Yiff?!</title>
        <meta property="og:title" content="Is This Yiff?!" />
        <meta property="og:type" content="website" />
        <meta property="og:image" content="{og_image}" />
        <meta property="og:url" content="https://isthisyiff.net" />
        <meta property="og:description" content="A guessing game using artwork from e621.net" />
        <meta property="og:locale" content="en_GB" />
        <meta property="og:site_name" content="Is This Yiff?!" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="retsplines" />
        <meta name="twitter:title" content="Is This Yiff?!" />
        <meta name="twitter:description" content="Try to guess whether an image is yiff or not just based on a face-crop. Ready to play? You must be 18+ to continue." />
        <meta name="twitter:image" content="{og_image}" />
        <meta name="twitter:image:alt" content="Is This Yiff?!" />
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
        <link rel="manifest" href="/site.webmanifest">
        <meta name="msapplication-TileColor" content="#da532c">
        <meta name="theme-color" content="#ffffff">
        <meta http-equiv="refresh" content="0; url={redirect_to}" />
    </head>
    <body></body>
</html>

"""

# Define the resource root
RESOURCE_CROP_ROOT_URL = 'https://source-images.isthisyiff.net/crop/'

# Define the app path
BASE_URI = 'https://isthisyiff.net/'

# Set up the logging subsystem
logger = logging.getLogger()
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stderr)
stdout_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(stdout_handler)


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

def lambda_handler(event, context):
    
    # Return a HTML page with customised Open Graph image that JS-redirects to 
    # the main page (/# + the fragment path)
    request = event['Records'][0]['cf']['request']
    
    # The redirect destination
    redirect_to = BASE_URI

    # The default OG image
    og_image = BASE_URI + 'image/isthisyiff-logo.png'
    
    # Match the URL
    uri_matches = re.match('\/challenge\/(([0-9A-F]){8}-([0-9A-F]){4}-([0-9A-F]){4}-([0-9A-F]){4}-([0-9A-F]){12})', request['uri'])
    
    if uri_matches:
        # Lookup the challenge
        try:

            # Got enough to customise the OG image?
            post = get_post(uri_matches.group(1))
            og_image = RESOURCE_CROP_ROOT_URL + post['crop']['S']
            redirect_to = redirect_to + '#' + uri_matches.group(1)

        except Exception as e:
            logger.error('Failed to load post %s: %s' % (uri_matches.group(1), str(e)))
            pass

    response = {
        'status': '200',
        'statusDescription': 'OK',
        'headers': {
            "content-type": [
                {
                    'key': 'Content-Type',
                    'value': 'text/html'
                }
            ]
        },
        'body': CONTENT.format(og_image=og_image, redirect_to=redirect_to)
    }
    
    return response