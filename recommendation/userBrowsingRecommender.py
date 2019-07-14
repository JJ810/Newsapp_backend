
"""
Recommendation system based on User History.
Does not calculate User history. Needs User History as Input

Takes People from DB as well as self calculated tags. Feature can be turned off
by calculate_tags knob in the constructor.

Current Working solution assumes all articles to be in user's browsing history.

# TODO: Filtering in Django
"""

from recommendation.extract_tags import TagExtractorNLTK
from recommendation.extract_tags import TagExtractorSpacy

from sklearn.feature_extraction.stop_words import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import BernoulliNB

import pandas as pd
import sqlite3


DBPATH = 'db.sqlite3'
POSTTABLE = 'api_post'
TWEET_CSV_PATH = 'tweet_sentiment.csv'


class UserBrowseRecommender:
    """
    Cosider that we have a Pandas DataFrame that contains user history.
    UID - AID
    Creation of this is handled by django. If required modify the constructor.
    Rest can be used as is.
    """
    def __init__(self, userID=1, dbPath=DBPATH, postTable=POSTTABLE, calculate_tags=True):
        # self.userHistory = userHistory
        self.dbPath = dbPath
        self.postTable = postTable
        self.calculate_tags = calculate_tags
        self.conn = sqlite3.connect(self.dbPath)
        self.cur = self.conn.cursor()
        # self.article_data = self.cur.execute('SELECT * FROM {0}'.format(self.postTable))
        self.all_articles = pd.read_sql_query('SELECT * FROM {0}'.format(self.postTable), self.conn)
        self.user_articles = self.filter_articles()
        self.test_sentiment_results()
        self.recommend()


    def filter_articles(self):
        """
        Filter articles based on user history. (Do this in DB preferably).
        """
        return self.all_articles


    @staticmethod
    def get_sentiment_result(input_str_list, train_file=TWEET_CSV_PATH):
        print("Loading Dataset")
        df = pd.read_csv(train_file)
        df["tweet"] = df["tweet"].str.lower()
        print("Removing StopWords")
        df["tweet"] = df["tweet"].apply(
            lambda x: ' '.join([word for word in x.split() if word not in (ENGLISH_STOP_WORDS)]))
        print("Building TFIDF Matrix")
        tfidf = TfidfVectorizer()
        tfidf_mat = tfidf.fit_transform(df['tweet'])
        print("Training Models:")
        print("-Naive Bayes")
        nb_clf = BernoulliNB().fit(tfidf_mat, df["classes"])
        output_list = []
        for input_str in input_str_list:
            tfidf_mat_test = tfidf.transform([input_str])
            print("Predicting Labels:", input_str)
            print("-Prediction from Naive Bayes CLassifier:", nb_clf.predict(tfidf_mat_test)[0])
            print("\nNote: 0 means Negative and 1 means Positive.")
            output_list.append(str(nb_clf.predict(tfidf_mat_test)[0]))
        return output_list


    def test_sentiment_results(self):
        sent = self.get_sentiment_result(['I love Trump', 'I hate Trump'])
        print('SENTIMENTS', sent)


    def build_system(self, article_data):
        df = pd.DataFrame(columns=['article_ID','tag', 'feel'])
        feels = self.get_sentiment_result(article_data.main_sentence)
        for i in range(article_data.shape[0]):
            tags = [article_data.people1[i], article_data.people2[i], article_data.people3[i], article_data.people4[i]]
            tags = [tag for tag in tags if len(tag)>0]
            if self.calculate_tags:
                tags_extracted = TagExtractorSpacy(article_data.main_sentence[i]).extract_tags()
                tags = list(set(tags).union(tags_extracted))
            df.loc[i] = [i, tags, int(feels[i])]
        return df

    def recommend(self):
        all_articles_data = self.build_system(self.all_articles)
        user_articles_data = self.build_system(self.user_articles)
        print('*'*20)
        print(all_articles_data)
        print('*'*20)
        print(user_articles_data)
        print('*'*20)
