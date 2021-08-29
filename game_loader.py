from itertools import groupby

from blaseball_mike import chronicler, eventually

from GameState import GameState


def assert_updates_equivalent(tester: 'TestAllGames', actual, generated):
    # No accidental cheating
    tester.assertIsNot(actual, generated)

    if actual is None:
        # Nothing I can do
        return

    tester.assertDictEqual(actual, generated)


def get_game(tester, game_id):
    print("Fetching game updates...")
    game_update_by_play = {}
    for game_update in chronicler.get_game_updates(game_ids=game_id, lazy=True,
                                                   cache_time=None):
        play_count = game_update['data']['playCount']
        if (play_count not in game_update_by_play or
                game_update_by_play[play_count]['timestamp'] <
                game_update['timestamp']):
            game_update_by_play[play_count] = game_update

    print("Processing feed events...")
    reference_i = min(k for k, v in game_update_by_play.items()
                      if v['data']['homePitcher'] is not None)
    game = GameState(game_update_by_play[reference_i])
    for i, feed_event in enumerate(feed_events(game_id)):
        play_count = feed_event['metadata']['play']
        game_update = game_update_by_play.get(play_count + 1, None)
        if game_update is not None:
            game_update = game_update['data']
        generated_update = game.update(feed_event, game_update)

        assert_updates_equivalent(tester, game_update, generated_update)


def feed_events(game_id):
    q = {
        'gameTags': game_id,
        'category': '0_or_3',
        'sortby': '{metadata,play}',
        'sortorder': 'asc'
    }
    # Eventually sorts by play but not subplay. groupby gets all the consecutive
    # elements from the same play, then sorted sorts those groups by subplay
    for _, group in groupby(
            eventually.search(cache_time=None, limit=-1, query=q),
            key=lambda e: e['metadata']['play']):
        yield from sorted(group, key=lambda e: e['metadata']['subPlay'])
