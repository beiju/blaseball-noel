import requests as requests
from flask import Flask, request, Response, jsonify

from game_transformer import generate_game

app = Flask(__name__)


def transform_game(game, valid_from):
    game_updates = generate_game(game['id'])
    return {
        **game,
        'lastUpdate': "[modified] " + game['lastUpdate']
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
                    'schedule': [transform_game(game, item['validFrom'])
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
    if 'type' in request.values and request.values['type'] == 'Stream':
        return get_stream(request.values)

    resp = requests.request(
        method=request.method,
        url=request.url.replace(request.host_url, 'https://api.sibr.dev/'),
        headers={key: value for (key, value) in request.headers if
                 key != 'Host'},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)

    excluded_headers = ['content-encoding', 'content-length',
                        'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    return Response(resp.content, resp.status_code, headers)


if __name__ == '__main__':
    app.run()
