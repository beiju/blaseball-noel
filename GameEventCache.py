from game_loader import get_game


class GameEventCache:
    games = {}

    def __getitem__(self, game_id, play_count):
        if game_id not in self.games:
            self.games[game_id] = get_game(game_id)

        game = self.games[game_id]
        try:
            return game[play_count]
        except IndexError:
            # TODO What does the actual stream do when the game is over?
            return game[-1]
