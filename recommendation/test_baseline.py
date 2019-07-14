
import unittest
from recommendation.baseline import BasicRecommender

class testBasicRecommender(unittest.TestCase):
    def test_get_tags(self):
        article = "Donald Trump is the president of US"
        recommender = BasicRecommender(article)
        tag_spacy = recommender.get_tags()
        print('Detected tags = ', tag_spacy)
        self.assertIsInstance(tag_spacy, list)

    def test_recommend(self):
        pass

    def test_add_recommended_articles_to_session(self):
        pass

if __name__ == '__main__':
    unittest.main()
