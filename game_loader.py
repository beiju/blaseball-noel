from collections import defaultdict
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


def flatten(t):
    return [item for sublist in t for item in sublist]


def get_game(tester, game_id):
    print("Fetching game updates...")
    game_updates_by_play = defaultdict(lambda: [])
    for game_update in chronicler.get_game_updates(game_ids=game_id, lazy=True,
                                                   cache_time=None):
        play_count = game_update['data']['playCount']
        game_updates_by_play[play_count].append(game_update)

    print("Processing feed events...")
    game = GameState(flatten(game_updates_by_play[k]
                             for k in sorted(game_updates_by_play.keys())))
    generated_updates = {}
    for i, feed_event in enumerate(feed_events(game_id)):
        play_count = feed_event['metadata']['play']
        game_updates = game_updates_by_play[play_count + 1]
        if len(game_updates) == 0:
            game_update = None
        elif len(game_updates) == 1:
            game_update = game_updates[0]['data']
        else:
            # If there's one with text and the rest without, use the one with
            # text
            filtered_updates = list(filter(
                lambda u: u['data']['lastUpdate'] != '', game_updates))
            if len(filtered_updates) == 1:
                game_update = filtered_updates[0]['data']
            elif len(filtered_updates) == 2 and (
                    filtered_updates[0]['data']['finalized'] !=
                    filtered_updates[1]['data']['finalized']):
                # Use the finalized one
                if filtered_updates[0]['data']['finalized']:
                    game_update = filtered_updates[0]['data']
                else:
                    game_update = filtered_updates[1]['data']
            else:
                raise RuntimeError("Can't choose which game update to use")
        generated_update = game.update(feed_event, game_update)

        assert_updates_equivalent(tester, game_update, generated_update)
        generated_updates[generated_update['playCount']] = generated_update

    return generated_updates


def feed_events(game_id):
    q = {
        'gameTags': game_id,
        'category': '0_or_2_or_3',
        'sortby': '{metadata,play}',
        'sortorder': 'asc'
    }
    # Eventually sorts by play but not subplay. groupby gets all the consecutive
    # elements from the same play, then sorted sorts those groups by subplay
    for _, group in groupby(
            eventually.search(cache_time=None, limit=-1, query=q),
            key=lambda e: e['metadata']['play']):
        yield from sorted(group, key=lambda e: e['metadata']['subPlay'])
