from lark import Lark


def _make_parser(name):
    with open(f"parser_grammars/{name}.lark", 'r') as f:
        return Lark(f.read(), start='start', debug=True,
                    lexer='dynamic_complete', import_paths=['parser_grammars'])


class Parsers:
    steal = _make_parser('steal')
    ball = _make_parser('ball')
    hit = _make_parser('hit')
    fielding_out = _make_parser('fielding_out')

    def __init__(self):
        raise RuntimeError("This class should not be instantiated")
