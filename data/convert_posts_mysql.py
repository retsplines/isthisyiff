import sys
import os
import csv
import argparse
import logging
import mysql.connector
from dateutil.parser import parse
from uuid import uuid4

"""
This tool converts e621's Post CSVs (from https://e621.net/db_export/) into an SQLite DB
"""

DEFAULT_BLACKLIST = ['gore', 'scat', 'watersports', 'young', 'loli', 'shota']

# Open the SQLite DB
con = mysql.connector.connect(
  host=os.environ.get('ITY_MYSQL_HOST', '127.0.0.1'),
  user=os.environ.get('ITY_MYSQL_USER', ''),
  password=os.environ.get('ITY_MYSQL_PASS', ''),
  database=os.environ.get('ITY_MYSQL_DB', 'isthisyiff'),
  autocommit=False
)

# Define the columns we'll generate.
#
# Where the value is a simple string, the string describes the type and the source will be the CSV column with the key name.
#
# Where the value is a dictionary, the 'type' key describes the type, plus the follwing other keys are valid:
#   - Any column may specifiy an alternate CSV source column with 'from'
#   - Any column may specify `exclude` to exclude the column from output, but `skip_if` and other logic will still run
#   - Any column may specify the `skip_if` option, which should be a filtering lambda.
#     If any column satisfies the filter, the row is skipped.
#   - Where the column is a `list`, the subtype may be set with `subtype`. Recursion is allowed.
#   - Where the column is a `list`, the `sep` key specifies the separator.
#   - Where the column is a `bool`, the `true` key specifies the value to be considered as 'true'.
#   - Where the column type is `true` or `false`, the value will always be emitted as that constant.
#
columns = {
    'id': {
        'type': 'int'
    },
    'created_at': 'date',
    'md5': 'str',
    'sources': {
        'from': 'source',
        'type': 'list',
        'sep': '\n'
    },
    'rating': {
        'type': 'str'
    },
    'image_width': 'int',
    'image_height': 'int',
    'tags': {
        'type': 'list',
        'subtype': 'str',
        'from': 'tag_string',
        'sep': ' ',
        # Skip undesirable tags
        'skip_if': lambda v: len(set(v.split(' ')) & set(DEFAULT_BLACKLIST)) > 0
    },
    'fav_count': 'int',
    'file_ext': {
        'type': 'str',
        'skip_if': lambda v: v not in ['png', 'jpg'] # Remove animations
    },
    'change_seq': 'int',
    'file_size': 'int',
    'comment_count': 'int',
    'description': 'str',
    'updated_at': 'date',
    'is_deleted': {
        'type': 'bool',
        'true': 't',
        # Ignore deleted posts
        'skip_if': lambda v: v == 't',
        'exclude': True
    },
    'is_pending': {
        'type': 'bool',
        'true': 't',
        # Ignore pending posts
        'skip_if': lambda v: v == 't',
        'exclude': True
    },
    'is_flagged': {
        'type': 'bool',
        'true': 't',
        # Ignore flagged posts
        'skip_if': lambda v: v == 't',
        'exclude': True
    },
    'score': {
        'type': 'int'
    },
    'up_score': 'int',
    'down_score': 'int',
    'is_processed': 'false'
}

# Some fields are huge, owo
csv.field_size_limit(sys.maxsize)

# Set up the logging subsystem
logger = logging.getLogger()
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stderr)
stdout_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(stdout_handler)

# Set up the command
parser = argparse.ArgumentParser(description='Converts an e621 posts CSV export into MySQL DB rows')
parser.add_argument('csv_path', help='The path to the source CSV', action='store', type=str)
parser.add_argument('--max-rows', help='Optionally, a maximum number of rows to process', action='store', dest='max_rows', type=int)
parser.add_argument('--log-percent-change', help='Optionally, how much the %% complete must change by to emit a log', action='store', dest='log_percent_change', type=float, default=0.01)
parser.add_argument('--delete-all', help='Optionally, delete the existing content.', action='store_true', dest='delete_all', default=False)

opts = parser.parse_args()

def gen_value_with_type(value, type, config={}):
    """
    Generates a processed value
    """

    # Date
    if (type == 'date'):
        if not value:
            return 0
        dt_value = parse(value)
        return int(dt_value.timestamp())

    # String-like
    if (type == 'str'):
        return str(value)

    # Numerics
    elif (type == 'int'):
        return int(value) if value != '' else 0

    # Boolean
    elif (type == 'bool'):
        return bool(value) if 'true' not in config else value == config['true']

    # Lists - if the element type isn't specified then just assumes they are 'str'
    elif (type == 'list'):

        # Process the list data appropriately
        items = filter(None, value.split(config['sep'] if 'sep' in config else ' '))

        return list(map(
            lambda val: gen_value_with_type(val, config['subtype'] if 'subtype' in config else 'str'),
            items
        ))

# Stat the file size
input_size_bytes = os.stat(opts.csv_path).st_size
logger.info('Input file %s is % d bytes' % (opts.csv_path, input_size_bytes))

# Keep track of progress
progress_bytes = 0
progress_rows = 0

# Track the progress percentage based on bytes read, and a "last" copy to know when to output
progress_pct = 0
progress_pct_last = 0

# Track created tags
created_tags = {}

# Delete existing content
if opts.delete_all:
    logger.info('Deleting all existing content!')
    con.start_transaction()    
    cur = con.cursor()
    cur.execute('TRUNCATE TABLE sources;')
    cur.execute('TRUNCATE TABLE post_tags;')
    cur.execute('TRUNCATE TABLE tags;')
    cur.execute('TRUNCATE TABLE posts;')
    cur.close()
    con.commit()

post_insertions = []
post_tag_insertions = []
source_insertions = []

def flush():
    """
    Perform inserts.
    """
    global post_insertions, post_tag_insertions, source_insertions

    con.start_transaction()    
    cur = con.cursor()

    if len(post_insertions) > 0:
        logger.debug('Got %d buffered post insertions - flushing' % len(post_insertions))
        placeholders = ['%s'] * len(post_insertions[0])
        cur.executemany("INSERT INTO posts VALUES(" + ','.join(placeholders) + ")", post_insertions)
        post_insertions = []
    
    if (len(post_tag_insertions) > 0):
        logger.debug('Got %d buffered post_tag insertions - flushing' % len(post_tag_insertions))
        cur.executemany(f"INSERT INTO post_tags VALUES(%s, %s)", post_tag_insertions)
        post_tag_insertions = []
    
    if (len(source_insertions) > 0):
        logger.debug('Got %d buffered source insertions - flushing' % len(source_insertions))
        cur.executemany(f"INSERT INTO sources VALUES (NULL, %s, %s)", source_insertions)
        source_insertions = []
    
    cur.close()
    con.commit()

# Read each CSV row
with open(opts.csv_path, 'r') as csv_file:
    reader = csv.DictReader(csv_file)

    for line in reader:

        progress_bytes += (len(','.join(line.values())) + 1)
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
        
        # Generate a formatted representation for the row
        row = {}
        insertable_columns = []
        skip_row = False

        for (key, type_or_config) in columns.items():

            if type(type_or_config) is str:
                
                # Data type is simple
                value_type = str(type_or_config)

                # Special 'uuid' type generates a UUID value
                if type_or_config == 'uuid':
                    row[key] = str(uuid4())
                elif type_or_config in ('false', 'true'):
                    row[key] = bool(type_or_config)
                else:
                    # The value is just copied directly from the CSV
                    row[key] = gen_value_with_type(line[key], type_or_config)

            elif type(type_or_config) is dict:
                
                # Data type is defined as a column config item
                # Assume 'str' if 'type' isn't configured for the column
                value_type = 'str' if 'type' not in type_or_config else type_or_config['type']

                # Special behaviour configured for this column
                source_value = line[key] if 'from' not in type_or_config else line[type_or_config['from']]
                row[key] = gen_value_with_type(

                    # Allow specification of the source data as 'from'
                    source_value,

                    # Value type defined by the column config
                    value_type,

                    # Provide the rest of the configuration
                    type_or_config
                )

                # Column has the skip_if lambda option specified?
                if 'skip_if' in type_or_config and type_or_config['skip_if'](source_value):
                    # Skip the whole row
                    skip_row = True
                    logger.debug('Row %d is skipped because column %s (value: %s) skip_if satisfied' % (progress_rows, key, source_value))
                    
                    # Ignore any further columns
                    break

                # Exclude the column?
                if 'exclude' in type_or_config and type_or_config['exclude']:
                    del row[key]

            else:
                
                logger.warn('Invalid column description: %s' % type_or_config)
                exit(-1)

            # Marshall all non-list and non-exluded items into an insertable string
            if key in row and value_type != 'list':
                insertable_columns.append(row[key])

        progress_rows += 1

        # Insert the tags, even if the row is skipped
        con.start_transaction()
        cur = con.cursor()
        for tag in row['tags']:

            # Tag entry already exists?
            if tag not in created_tags:
                cur.execute(f"INSERT INTO tags VALUES (NULL, %s, 0)", [tag])
                logger.debug(f"Tag {tag} has not yet been inserted, created it with tags ID {cur.lastrowid}")
                created_tags[tag] = cur.lastrowid

        cur.close()
        con.commit()

        # Skip?
        if skip_row:
            continue
        
        # Insert the post row
        placeholders = ['%s'] * len(insertable_columns)
        post_insertions.append(insertable_columns)
        logger.debug(f"Inserted post {row['id']}")

        # Insert the sources
        for source in row['sources']:
            source_insertions.append([row['id'], source])
            logger.debug(f"Linked post {row['id']} with source {source} with ID {cur.lastrowid}")

        # Insert the tag links
        for tag in row['tags']:

            # Insert a tag link
            post_tag_insertions.append([row['id'], created_tags[tag]])
            logger.debug(f"Tagged post {row['id']} with tag {tag} ID {created_tags[tag]}")

        # Enough entities to persist?
        if (len(post_insertions) > 1000):
            flush()

        # Processed enough?
        if 'max_rows' in opts and progress_rows == opts.max_rows:
            logger.debug('Processed %d rows (maximum specified by --max-rows reached)' % progress_rows)
            break

# One last flush
flush()

# Commit & close
con.commit()
con.close()
