import pandas as pd
import spacy
import sqlite3
from collections import Counter
from datetime import timezone
from zoneinfo import ZoneInfo
from langdetect import detect
from pysentimiento import create_analyzer
from db import RedditDatabase

class RedditTransformer:
    def __init__(self, db: RedditDatabase, timezone_str="Europe/Lisbon"):
        self.db = db
        self.df = None
        self.df_features = None
        self.timezone = ZoneInfo(timezone_str)
        self._load_spacy_models()
        print("Spacy loaded")
        self._load_sentiment_analyzers()
        print("Sentiment loaded")

    def _load_spacy_models(self):
        self.spacy_models = {
            "pt": spacy.load("pt_core_news_sm"),
            "en": spacy.load("en_core_web_sm"),
            "es": spacy.load("es_core_news_sm"),
        }

    def _load_sentiment_analyzers(self):
        self.analyzers = {
            "en": create_analyzer(task="sentiment", lang="en"),
            "es": create_analyzer(task="sentiment", lang="es"),
            "pt": create_analyzer(task="sentiment", lang="pt")
        }

    def load_data(self):
        query = "SELECT * FROM posts"
        self.df = pd.read_sql_query(query, self.db.connection)

    def transform(self):
        df = self.df.copy()

        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
        df["created_at"] = df["created_at"].dt.tz_convert(self.timezone)
        df["post_hour"] = df["created_at"].dt.strftime("%H:%M")
        df["post_weekday"] = df["created_at"].dt.day_name()

        df["engagement_score"] = df["score"] + df["num_comments"]
        df["score_to_comments_ratio"] = df.apply(
            lambda row: row["score"] / row["num_comments"] if row["num_comments"] > 0 else None,
            axis=1)
        
        df["word_count"] = df["text"].apply(lambda x: len(str(x).split()))
        df["text_length"] = df["text"].apply(lambda x: len(str(x)))
        df["question_detected"] = df["text"].apply(lambda x: "?" in str(x))

        df[["top_keywords", "detected_language"]] = df["text"].apply(
            lambda x: pd.Series(self.extract_keywords(str(x))))
        df["top_keywords"] = df["top_keywords"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")

        df[["sentiment_score", "sentiment_analysis"]] = df.apply(self.get_sentiment, axis=1)
        self.df_all = df.copy()
        self.df_features = df[[ 
            'id', 'post_hour', 'post_weekday', 'engagement_score',
            'score_to_comments_ratio', 'word_count', 'text_length',
            'question_detected', 'top_keywords', 'detected_language',
            'sentiment_score', 'sentiment_analysis'
        ]]

    def extract_keywords(self, text):
        try:
            lang = detect(text)
        except:
            return [], "unknown"

        if lang not in self.spacy_models:
            return [], lang

        doc = self.spacy_models[lang](text)
        keywords = [token.text.lower() for token in doc
                    if token.pos_ in ["NOUN", "ADJ"]
                    and not token.is_stop and token.is_alpha]
        return list(set(keywords)), lang
    
    def get_sentiment(self, row):
        lang = row.get("detected_language")
        text = row.get("text", "")

        sentiment_score = None
        sentiment_analysis = "unsupported"

        if lang in self.analyzers:
            try:
                result = self.analyzers[lang].predict(text)
                sentiment_score = result.probas[result.output]
                sentiment_analysis = result.output
            except Exception as e:
                print(f"[WARN] Sentiment failed for lang={lang}: {e}")

        return pd.Series([sentiment_score, sentiment_analysis], index=["sentiment_score", "sentiment_analysis"])

    def save_all_to_csv(self, filename):
        self.df_all.to_csv(filename, sep=";", index=False, encoding="utf-8-sig", quoting=1)

    def save_features_to_db(self, table_name="post_features"):
        self.df_features.to_sql(table_name, self.db.connection, if_exists="replace", index=False)

    def get_top_keywords(self, top_n=30):
        all_keywords = (
            self.df_features["top_keywords"]
            .dropna()
            .str.split(r",\s*")
            .explode()
            .str.strip()
        )
        
        all_keywords = all_keywords[all_keywords.str.len() > 1]
        all_keywords = all_keywords[~all_keywords.str.contains(r'^["\'\\]?$')]

        keyword_counts = Counter(all_keywords.tolist())
        return keyword_counts.most_common(top_n)

    def save_top_keywords_to_db(self, table_name="top_keywords", top_n=30):
        keywords = self.get_top_keywords(top_n)
        df_keywords = pd.DataFrame(keywords, columns=["keyword", "count"])
        df_keywords.to_sql(table_name, self.db.connection, if_exists="replace", index=False)

def main():

    try:
        db = RedditDatabase(db_path="reddit_posts.db")
        transformer = RedditTransformer(db)
        transformer.load_data()
        transformer.transform()

        transformer.save_features_to_db(table_name="features")
        transformer.save_top_keywords_to_db(table_name="top_keywords")
        transformer.save_all_to_csv("Merged_Sample.csv")

        print("[INFO] Data transformation complete.")
        print("[INFO] Top keywords saved to DB.")

    finally:
        db.close()

if __name__ == "__main__":
    main()