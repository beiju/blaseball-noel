from lark import Lark


def _make_parser(name):
    with open(f"parser_grammars/{name}.lark", 'r') as f:
        return Lark(f, start='start', debug=True,
                    lexer='dynamic_complete', import_paths=['parser_grammars'])


class Parsers:
    batter_up = _make_parser('batter_up')
    steal = _make_parser('steal')
    ball = _make_parser('ball')
    walk = _make_parser('walk')
    hit = _make_parser('hit')
    home_run = _make_parser('home_run')
    fielding_out = _make_parser('fielding_out')
    mild_pitch = _make_parser('mild_pitch')
    strikeout = _make_parser('strikeout')
    blooddrain = _make_parser('blooddrain')

    def __init__(self):
        raise RuntimeError("This class should not be instantiated")
