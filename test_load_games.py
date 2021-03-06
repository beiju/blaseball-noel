import unittest

from parameterized import parameterized
from blaseball_mike import chronicler

from game_transformer import generate_game


class TestAllGames(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    @parameterized.expand([(g['gameId'],)
                           for g in chronicler.get_games(season=12, count=1)])
    def test_s12_game(self, game_id):
        game = generate_game(game_id)
        self.assertIsInstance(game, list)

    @parameterized.expand([(g['gameId'],)
                           for g in chronicler.get_games(season=13, count=10)])
    def test_s13_game(self, game_id):
        game = generate_game(game_id)
        self.assertIsInstance(game, list)


if __name__ == '__main__':
    unittest.main()
