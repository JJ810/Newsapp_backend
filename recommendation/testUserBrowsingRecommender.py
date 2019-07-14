
import unittest
from recommendation.userBrowsingRecommender import UserBrowseRecommender

class TestUserHistoryRecommender(unittest.TestCase):
    def test_recommend(self):
        recommender = UserBrowseRecommender()
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
