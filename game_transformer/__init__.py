from collections import defaultdict
from itertools import groupby

from blaseball_mike import chronicler, eventually

from game_transformer.GameRecorder import GameRecorder
from game_transformer.GameProducer import GameProducer


def generate_game(game_id):
    producer: GameProducer = get_game_producer(game_id)

    return [update for update in producer]


def get_game_producer(game_id):
    game_updates_by_play = fetch_game_updates(game_id)
    game_updates_flat = (flatten(game_updates_by_play[k]
                                 for k in sorted(game_updates_by_play.keys())))

    home_recorder = GameRecorder(game_updates_flat, 'home')
    away_recorder = GameRecorder(game_updates_flat, 'away')
    # Start with this == home, because it gets swapped to away as the first
    # (non-ignored) event.
    this_recorder, next_recorder = home_recorder, away_recorder

    for i, feed_event in enumerate(fetch_feed_events(game_id)):
        game_update = game_update_for_event(game_updates_by_play,
                                            feed_event['metadata']['play'])

        if feed_event['type'] == 2:  # half-inning start
            this_recorder, next_recorder = next_recorder, this_recorder
        elif feed_event['type'] == 54:  # incineration
            this_recorder.replace_player(feed_event)
            next_recorder.replace_player(feed_event)
        else:
            this_recorder.record_event(feed_event, game_update)

    return GameProducer(game_updates_flat, home_recorder, away_recorder)


def fetch_game_updates(game_id):
    game_updates_by_play = defaultdict(lambda: [])
    for game_update in chronicler.get_game_updates(game_ids=game_id,
                                                   cache_time=None):
        play_count = game_update['data']['playCount']
        game_updates_by_play[play_count].append(game_update)

    return game_updates_by_play


def fetch_feed_events(game_id):
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


def game_update_for_event(game_updates_by_play, play_count):
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
    return game_update


def flatten(t):
    return [item for sublist in t for item in sublist]
