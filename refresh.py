import time
from db import RedditDatabase
import praw
import dotenv

config = dotenv.dotenv_values(".env")
reddit = praw.Reddit(
    client_id=config["REDDIT_CLIENT_ID"],
    client_secret=config["REDDIT_CLIENT_SECRET"],
    client_username=config["REDDIT_CLIENT_USERNAME"],
    client_password=config["REDDIT_CLIENT_PASSWORD"],
    user_agent="post-update_1.0"
)

db = RedditDatabase()

recent_ids = db.get_recent_post_ids(days=2)

for post_id in recent_ids:
    try:
        submission = reddit.submission(id=post_id)
        db.update_post_metrics(post_id, submission.score, submission.num_comments, submission.upvote_ratio)
        print(f"Updated {post_id}: {submission.score} score, {submission.num_comments} comments")
        time.sleep(1)
    except Exception as e:
        print(f"Error updating post {post_id}: {e}")

db.close()