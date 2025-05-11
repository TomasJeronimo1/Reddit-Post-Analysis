import sqlite3
from datetime import datetime, timedelta, UTC

class RedditDatabase:
    def __init__(self, db_path="reddit_posts.db"):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self._create_table()

    def insert_post(self, post_data):
        try:
            self.cursor.execute("""
                INSERT INTO posts (id, title, created_at, url, text, flair, score, upvote_ratio, num_comments, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, post_data)
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def close(self):
        self.connection.close()

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                url TEXT,
                text TEXT,
                flair TEXT,
                score INTEGER,
                upvote_ratio FLOAT,
                num_comments INTEGER,
                last_updated TIMESTAMP
            )
        """)

        self.connection.commit()
    
    def get_recent_post_ids(self, days=2):
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        self.cursor.execute("SELECT id FROM posts WHERE created_at >= ?", (cutoff,))
        return [row[0] for row in self.cursor.fetchall()]

    def update_post_metrics(self, post_id, score, num_comments, upvote_ratio):
        self.cursor.execute("""
            UPDATE posts
            SET score = ?, num_comments = ?, upvote_ratio = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (score, num_comments, upvote_ratio, post_id))
        
        self.connection.commit()