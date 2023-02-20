# `e621 → IsThisYiff?! ETL`

The [ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load) process for _IsThisYiff?!_ is a bit convoluted. E621 provides [daily DB exports](https://e621.net/db_export/) that contain a CSV of posts with their associated tags.

Searching this in a meaningful way proved to be a bit annoying, especially with the embedded CSV tag lists, so I wrote a Python script (`convert_posts_mysql.py`) and an associated schema (`schema.sql`). Once everything's in an SQL DB, you can use more powerful queries to find suitable posts.

Once I had exported some CSVs of interesting posts, I wrote a second script - `import.py` which does _everything else_. This script is a bit of a monster with too many responsibilities, but it does the following:

1. Read a CSV containing these columns (at least):
    - `id` (e621 ID)
    - `image_width` (fullsize)
    - `image_height` (fullsize)
    - `rating` (`'e'` or `'s'`)
    - `score`
    - `fav_count`
    - `url` (e621 fullsize image URL)
2. Download each e621 image to a local cache directory (`orig`)
3. Upload the image to an S3 bucket.
4. Use the Rekognition Custom Labels model to identify furry faces.
5. Create a cropped image and upload it to the same S3 bucket with a unique object name.
6. Create an object in a DynamoDB database summarising/associating the pair of images.
