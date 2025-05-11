from datetime import datetime, UTC
import dotenv
import praw

from db import RedditDatabase

class RedditExtractor:
    def __init__(self, db, subreddit_name="portugal", env_path=".env"):
        self.config = dotenv.dotenv_values(env_path)
        self.reddit = praw.Reddit(
            client_id=self.config["REDDIT_CLIENT_ID"],
            client_secret=self.config["REDDIT_CLIENT_SECRET"],
            client_username=self.config["REDDIT_CLIENT_USERNAME"],
            client_password=self.config["REDDIT_CLIENT_PASSWORD"],
            user_agent="post-extraction_1.0"
        )
        self.subreddit = self.reddit.subreddit(subreddit_name)
        self.db = db

    def extract_and_store(self):
        print(f"[INFO] Starting stream for r/{self.subreddit.display_name}")
        for post in self.subreddit.stream.submissions():
            post_data = (
                post.id,
                post.title,
                datetime.fromtimestamp(post.created_utc).isoformat(),
                post.url,
                post.selftext,
                post.link_flair_text,
                post.score,
                post.upvote_ratio,
                post.num_comments,
                datetime.now(UTC)
            )

            if self.db.insert_post(post_data):
                print(f"[DB] Stored post at {post_data[2]} with title: {post_data[1]}")
            else:
                print(f"[DB] Post {post.id} already exists — skipped.")

    def close(self):
        self.db.close()

if __name__ == "__main__":
    db = RedditDatabase()
    extractor = RedditExtractor(db)
    try:
        extractor.extract_and_store()
    except KeyboardInterrupt:
        print("[INFO] Stopping extractor...")
    finally:
        extractor.close()