
import sqlite3
from recommendation.extract_tags import TagExtractorNLTK
from recommendation.extract_tags import TagExtractorSpacy
import pandas as pd

DBPATH = 'test.db'
TAGTABLE = 'article_tags'

class BasicRecommender(object):
	def __init__(self, article, dbPath=DBPATH, tagTable=TAGTABLE):
		self.dbPath = dbPath
		self.tagTable = tagTable
		self.conn = sqlite3.connect(self.dbPath)
		self.cur = self.conn.cursor()
		self.article = article

	def get_tags(self):
		"""
		Gets tags from current article. This same method should be used to insert new row in DB
		when new articles get added
		"""
		return TagExtractorSpacy(self.article).extract_tags()

	def recommend(self):
		tags = self.get_tags()
		articles = """
		SELECT article_id from {0} WHERE TAGS IN ({1})
		""".format(self.tagTable, ', '.join(tags))
		df = pd.read_sql_query(conn, articles)
		return df

	def add_recommended_articles_to_session(self):
		create = """DROP TABLE IF EXISTS {} CREATE TABLE{}""".format() #ToDo: How to get this unique
		insert = """
		INSERT INTO {0} (article_id)({1})
		""".format(self.tagTable, self.recommend())
		cur.execute(insert)
