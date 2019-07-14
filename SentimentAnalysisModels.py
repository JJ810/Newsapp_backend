from sklearn.feature_extraction.stop_words import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import BernoulliNB
import pandas as pd


# text = "Any random text here to check for positive/negative sentiment."


def get_sentiment_result(input_str_list):
    print("Loading Dataset")
    df = pd.read_csv("tweet_sentiment.csv")
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
