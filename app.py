import requests as requests
from flask import Flask, request, Response, jsonify
from flask_caching import Cache

from game_transformer import generate_game

config = {
    "DEBUG": True,  # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}

app = Flask(__name__)
# tell Flask to use the above defined config
app.config.from_mapping(config)
cache = Cache(app)

generate_game_memo = cache.memoize(timeout=0)(generate_game)


def transform_game(game):
    game_updates = generate_game_memo(game['id'])
    try:
        update = next(u for u in game_updates
                      if u.data['playCount'] == game['playCount'])
        return update.data
    except StopIteration:
        return {
            **game,
            'lastUpdate': "[unmodified] " + game['lastUpdate']
        }


def transform_item(item):
    return {
        **item,
        'data': {
            **item['data'],
            'value': {
                **item['data']['value'],
                'games': {
                    **item['data']['value']['games'],
                    'schedule': [transform_game(game)
                                 for game in
                                 item['data']['value']['games']['schedule']]
                }
            }
        }
    }


def get_stream(resp):
    stream_records = resp.json()
    return jsonify({
        **stream_records,
        'items': [transform_item(item) for item in stream_records['items']]
    })


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    resp = requests.request(
        method=request.method,
        url=request.url.replace(request.host_url, 'https://api.sibr.dev/'),
        headers={key: value for (key, value) in request.headers if
                 key != 'Host'},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)

    if 'type' in request.values and request.values['type'] == 'Stream':
        return get_stream(resp)

    excluded_headers = ['content-encoding', 'content-length',
                        'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    return Response(resp.content, resp.status_code, headers)


if __name__ == '__main__':
    app.run()
