import boto3
import sys
import json
import logging
import os
import hashlib
from PIL import Image

rekognition_client = boto3.client('rekognition')

CROP_SECRET = os.environ.get('ITY_CROP_SECRET', 'NICETRY')

MIN_CONFIDENCE = 25
bucket = os.environ.get('ITY_BUCKET_NAME', 'source-images.isthisyiff.retsplin.es')
model = os.environ.get('ITY_MODEL_ARN', '')

# Set up the logging subsystem
logger = logging.getLogger()
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stderr)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger.addHandler(stdout_handler)

def find_faces(post):

    logger.info('Finding custom labels for %s...' % post['name'])
    try:
        response = rekognition_client.detect_custom_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': post['name']}},
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
    
    im = Image.open('assets/' + post['name'])
    im_cropped = im.crop((left, top, left + width, top + height))

    # generate a new name based on the original basename, a secret and jpg extension 
    new_name = hashlib.sha1((post['name'].lower() + CROP_SECRET).encode('utf-8')).hexdigest() + '.jpg'
    logger.info('New name for the cropped image will be %s' % new_name)

    # Convert to RGB if required
    if im_cropped.mode in ("RGBA", "P"): 
        im_cropped = im_cropped.convert("RGB")

    # Save the image out to the 'crop' subdirectory
    im_cropped.save('face_crops/' + new_name)
    logger.info('Wrote cropped image out as %s' % new_name)

    return new_name

def main():

    # Load the list
    print('id,orig,crop,rating,score,fav_count,orig_width,orig_height,crop_left,crop_top,crop_width,crop_height')

    with open(sys.argv[1]) as post_file:

        post_list = json.loads(post_file.read())

        for post in post_list:
            
            post['name'] = post['cmd'].rsplit('/', 1)[1]
            face_spec = find_faces(post)

            # Was no face identified?
            if face_spec is None:
                logger.info('%s did not contain a face.' % post['name'])
                continue

            # Confidence too low?
            if face_spec['Confidence'] < MIN_CONFIDENCE:
                logger.info('%s best face confidence level %d is too low (< %d)' % (
                    post['name'],
                    face_spec['Confidence'],
                    MIN_CONFIDENCE
                ))
                continue

            # Calculate dimensions of the cropped image
            crop_width = int(face_spec['Geometry']['BoundingBox']['Width'] * post['image_width'])
            crop_height = int(face_spec['Geometry']['BoundingBox']['Height'] * post['image_height'])
            crop_left = int(face_spec['Geometry']['BoundingBox']['Left'] * post['image_width'])
            crop_top = int(face_spec['Geometry']['BoundingBox']['Top'] * post['image_height'])

            # Crop & save the image
            cropped_name = make_cropped_image(
                post,
                crop_left,
                crop_top,
                crop_width, 
                crop_height
            )

            # Emit a CSV line with the details
            print(','.join([
                str(post['id']),
                post['name'],
                cropped_name,
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