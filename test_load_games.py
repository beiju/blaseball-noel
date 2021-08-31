import unittest

from parameterized import parameterized
from blaseball_mike import chronicler

from game_loader import get_game


class TestAllGames(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_test(self):
        self.assertTrue(True)

    @parameterized.expand([(g['gameId'],)
                           for g in reversed(chronicler.get_games(season=12,
                                                                  count=8))])
    def test_s12_game(self, game_id):
        game = get_game(self, game_id)
        self.assertIsInstance(game, dict)


if __name__ == '__main__':
    unittest.main()
