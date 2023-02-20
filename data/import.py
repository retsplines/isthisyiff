import boto3
import sys
import logging
import os
import hashlib
import csv
import urllib.request
import uuid
import argparse
import time
from PIL import Image

"""
Ridiculous monster Python script that does (almost) everything to ETL e621 data in CSV format into IsThisYiff
"""

rekognition_client = boto3.client('rekognition')
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')

# This is the secret used to generate a crop filename from an original filename
# If it's not kept secret, finding a fullsize-image from a crop image is trivial.
CROP_SECRET = os.environ.get('ITY_CROP_SECRET', '')
MIN_CONFIDENCE = 25

# S3 bucket details
bucket = os.environ.get('ITY_BUCKET_NAME', 'source-images.isthisyiff.retsplin.es')
prefix = os.environ.get('ITY_PREFIX', 'test')

# Prefix under which cropped images are placed
crop_prefix = os.environ.get('ITY_CROP_PREFIX', 'crop/')

# Rekognition model details
model = os.environ.get('ITY_MODEL_ARN', '')

# DynamoDB details
table_name = os.environ.get('ITY_DYNAMO_TABLE', '')

# Set up the command
parser = argparse.ArgumentParser(description='Reads a CSV of e621 posts, downloads the images, detects faces & uploads the result to AWS (S3 & DynamoDB)')
parser.add_argument('csv_path', help='The path to the source CSV', action='store', type=str)
parser.add_argument('--no-db', help='Optionally, skip writing to DynamoDB - just print', action='store_true', dest='no_db', default=False)
parser.add_argument('--skip-downloaded', help='Optionally, skip a file if we see it is already downloaded', action='store_true', dest='skip_downloaded', default=False)
parser.add_argument('--redownload-existing', help='Optionally, redownload existing files rather than using the local copy', action='store_true', dest='redownload_existing', default=False)
parser.add_argument('--skip-if-downloaded', help='Optionally, skip a file if we see it is already downloaded', action='store_true', dest='skip_if_downloaded', default=False)
parser.add_argument('--log-percent-change', help='Optionally, how much the %% complete must change by to emit a log', action='store', dest='log_percent_change', type=float, default=0.01)
parser.add_argument('--start-at-id', help='Optionally, start at an ID', action='store', dest='start_at_id', type=int, default=None)

opts = parser.parse_args()

# Set up the logging subsystem
logger = logging.getLogger()
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stderr)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger.addHandler(stdout_handler)

# Define a runID for these entries
run_id = int(time.time())
logger.info('IsThisYiff importer (Run ID %d)' % run_id)

def find_faces(post):

    object_key = ((prefix + '/') if prefix else '') + post['orig_name']
    logger.info('Finding custom labels for %s...' % object_key)
    try:
        response = rekognition_client.detect_custom_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': object_key}},
            ProjectVersionArn=model
        )
    except Exception as e:
        logger.warning('Rekognition said: %s' % e)
        return None

    best_confidence_face = None
    best_confidence = -1

    for customLabel in response['CustomLabels']:
        if 'Geometry' in customLabel:
            logger.info(
                'Got %s @ %.2f %.2f with confidence %.2f' % (
                    customLabel['Name'],
                    customLabel['Geometry']['BoundingBox']['Top'],
                    customLabel['Geometry']['BoundingBox']['Left'],
                    customLabel['Confidence']
                )
            )
            if customLabel['Confidence'] > best_confidence:
                # There will always be a bounding box if there's a geometry key present
                best_confidence_face = customLabel
                best_confidence = customLabel['Confidence']

    return best_confidence_face

def make_cropped_image(post, left, top, width, height):
    
    im = Image.open(post['orig_path'])
    im_cropped = im.crop((left, top, left + width, top + height))

    # generate a new name based on the original basename, a secret and jpg extension 
    new_name = hashlib.sha1((post['orig_path'].lower() + CROP_SECRET).encode('utf-8')).hexdigest() + '.jpg'
    logger.info('New name for the cropped image will be %s' % new_name)

    # Convert to RGB if required
    if im_cropped.mode in ("RGBA", "P"): 
        im_cropped = im_cropped.convert("RGB")

    # Save the image out to the 'crop' subdirectory
    im_cropped.save('crop/' + new_name)
    logger.info('Wrote cropped image out as %s' % new_name)

    return 'crop/' + new_name

def download_orig(post):
    """
    Download the original post to cache.
    """
    logger.info('Downloading original for %s (%s)...' % (post['id'], post['url']))
    urllib.request.urlretrieve(post['url'], post['orig_path'])
    logger.info('Downloaded %s' % post['url'])

def upload(source, object_key):
    """
    Upload an original post to S3
    """
    key = ((prefix + '/') if prefix else '') + object_key
    logger.info('Uploading %s as %s...' % (source, key))
    try:
        s3_client.upload_file(source, bucket, key)
    except Exception as e:
        logging.error(e)
        return False
    return True

def check_vars():
    """
    Check the environment is okay.
    """

    result = True

    if not CROP_SECRET or CROP_SECRET == '':
        logger.warning('! Running with improper crop secret %s - check ITY_CROP_SECRET' % CROP_SECRET)
    
    if prefix:
        logger.warning('! Running with a prefix - usually only good for testing')

    if not bucket:
        logger.error('! Cannot operate without an S3 bucket - check ITY_BUCKET_NAME')
        result = False

    if not model:
        logger.error('! Cannot operate without a Rekognition Custom Labels Model ARN - check ITY_MODEL_ARN')
        result = False

    if not table_name:
        logger.error('! Cannot operate without a DynamoDB table name - check ITY_DYNAMO_TABLE')
        result = False

    return result

def add_post_to_db(post):
    """
    Add a post to DynamoDB
    """

    post['uuid'] = str(uuid.uuid4()).upper()

    if opts.no_db:
        logger.warning('Skipped inserting due to --no-db')
        return

    try:

        dynamodb_client.put_item(
            TableName=table_name,
            Item={
                'uuid': { 'S': post['uuid'] },
                'id': { 'N': str(post['id']) },
                'orig': { 'S': post['orig_name'] },
                'crop': { 'S': post['crop_name'] },
                'rating': { 'S': post['rating'] },
                'score': { 'N': str(post['score']) },
                'fav_count': { 'N': str(post['fav_count']) },
                'orig_width': { 'N': str(post['image_width']) },
                'orig_height': { 'N': str(post['image_height']) },
                'crop_left': { 'N': str(post['crop_left']) },
                'crop_top': { 'N': str(post['crop_top']) },
                'crop_width': { 'N': str(post['crop_width']) },
                'crop_height': { 'N': str(post['crop_height']) },
                'import_run_id': { 'N': str(run_id) },
                'correct_guesses': { 'N': '0' },
                'incorrect_guesses': { 'N': '0' }
            }
        )

        logger.info('Inserted record for %s into %s with UUID %s' % (post['id'], table_name, post['uuid']))
    
    except Exception as e:
        logger.warning('Failed to insert %s in to DynamoDB: %s' % (post['id'], str(e)))
        return False

    return True

def main():

    # Enforce environment variables
    if not check_vars():
        exit(-1)

    print('id,orig,crop,rating,score,fav_count,orig_width,orig_height,crop_left,crop_top,crop_width,crop_height')

    # The list should be a CSV with these keys at least these columns:
    #   - id (e621 ID)
    #   - image_width (fullsize)
    #   - image_height (fullsize)
    #   - rating ('e' or 's')
    #   - score
    #   - fav_count
    #   - url (e621 fullsize image URL)

    # Stat the file size
    input_size_bytes = os.stat(opts.csv_path).st_size
    logger.info('Input file %s is % d bytes' % (opts.csv_path, input_size_bytes))

    # Keep track of progress
    progress_bytes = 0
    progress_rows = 0

    # Track the progress percentage based on bytes read, and a "last" copy to know when to output
    progress_pct = 0
    progress_pct_last = 0

    # Found our starting ID yet?
    found_starting_id = False

    # Read each CSV row
    with open(opts.csv_path, 'r') as csv_file:

        reader = csv.DictReader(csv_file)

        for post in reader:
                
            progress_bytes += (len(','.join(post.values())) + 1)
            progress_pct = (progress_bytes / input_size_bytes) * 100.0
            # Percentage change?
            if progress_pct - progress_pct_last > opts.log_percent_change:
                progress_pct_last = progress_pct
                logger.info(
                    '%s: %.2f%% complete (%d bytes of %d; %d rows)' % (
                        os.path.basename(opts.csv_path),
                        progress_pct,
                        progress_bytes,
                        input_size_bytes,
                        progress_rows
                    )
                )
  
            # {orig,crop}_path is the local relative path
            # {orig,crop}_name is the basename only
            post['orig_name'] = post['url'].rsplit('/', 1)[1]
            post['orig_path'] = 'orig/' + post['orig_name']

            progress_rows += 1
          
            # Skipping rows?
            if opts.start_at_id is not None and not found_starting_id:
                if int(post['id']) == opts.start_at_id:
                    found_starting_id = True
                else:
                    logger.info('Skipping %s because of --start-at-id' % post['id'])
                    continue


            logger.info(' ---------- Processing %s (%s) ----------' % (post['id'], post['orig_path']))

            # File already exists?
            if os.path.exists(post['orig_path']):
                if opts.skip_if_downloaded:
                    logger.warning(
                        'Skipping %s (%s) completely because we already have the file downloaded (--skip-existing)' % (
                            post['id'], post['orig_path']
                        )
                    )
                    continue
                elif opts.redownload_existing:
                    logger.warning('Redownloading %s (%s) (--redownload-existing)' % (post['id'], post['orig_path']))
                    download_orig(post)
                else:
                    logger.info('Already have %s orig %s - using it' % (post['id'], post['orig_path']))
            else:
                # Download the media
                download_orig(post)
            
            # Upload the media to S3
            if not upload(post['orig_path'], post['orig_name']):
                logger.warning('%s failed to upload to S3')
                continue

            face_spec = find_faces(post)

            # Was no face identified?
            if face_spec is None:
                logger.info('%s did not contain a face.' % post['orig_path'])
                continue

            # Confidence too low?
            if face_spec['Confidence'] < MIN_CONFIDENCE:
                logger.info('%s best face confidence level %d is too low (< %d)' % (
                    post['orig_path'],
                    face_spec['Confidence'],
                    MIN_CONFIDENCE
                ))
                continue

            # Calculate dimensions of the cropped image
            crop_width = int(face_spec['Geometry']['BoundingBox']['Width'] * int(post['image_width']))
            crop_height = int(face_spec['Geometry']['BoundingBox']['Height'] * int(post['image_height']))
            crop_left = int(face_spec['Geometry']['BoundingBox']['Left'] * int(post['image_width']))
            crop_top = int(face_spec['Geometry']['BoundingBox']['Top'] * int(post['image_height']))

            # Crop & save the image
            post['crop_path'] = make_cropped_image(
                post,
                crop_left,
                crop_top,
                crop_width, 
                crop_height
            )
            post['crop_name'] = os.path.basename(post['crop_path'])
            post['crop_left'] = crop_left
            post['crop_top'] = crop_top
            post['crop_width'] = crop_width
            post['crop_height'] = crop_height

            # Upload the cropped file
            logger.info('Uploading cropped version for %s' % post['id'])
            upload(post['crop_path'], crop_prefix + post['crop_name'])

            # Add the post to DynamoDB
            add_post_to_db(post)

            # Emit a CSV line with the details (so the output can be captured for CSV use)
            print(','.join([
                post['uuid'],
                str(post['id']),
                post['orig_path'],
                post['crop_name'],
                post['rating'],
                str(post['score']),
                str(post['fav_count']),
                str(post['image_width']),
                str(post['image_height']),
                str(crop_left),
                str(crop_top),
                str(crop_width),
                str(crop_height),
            ]))

if __name__ == "__main__":
    main()