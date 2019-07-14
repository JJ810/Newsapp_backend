
import unittest
import sqlite3
from recommendation.extract_tags import TagExtractorNLTK
from recommendation.extract_tags import TagExtractorSpacy

DBPATH = 'test.db'
TAGTABLE = 'article_tags'
ARTICLE = 'recommendation/trump.txt'

class TestTagExtractor(unittest.TestCase):
	def setup(self, dbPath=DBPATH, tagTable=TAGTABLE, article=ARTICLE):
		self.conn = sqlite3.connect(DBPATH)
		self.cur = self.conn.cursor()
		self.tagTable = tagTable
		self.input_text = open(article).read()

	def testTagextractorNLTK(self):
		self.setup()
		tag_extractor = TagExtractorNLTK(self.input_text)
		tags = tag_extractor.extract_tags()
		print('NLTK Tags = ', tags)
		self.assertIn('Trump', tags)

	def testTagExtractorSpacy(self):
		self.setup()
		tags = TagExtractorSpacy(self.input_text).extract_tags()
		print('Spacy tags = ', tags)
		self.assertIn('Trump', tags)

	def testDummy(self):
		self.assertEqual(2+3, 5)

if __name__=='__main__':
	unittest.main()
