from lark import Lark


def _make_parser(name):
    with open(f"parser_grammars/{name}.lark", 'r') as f:
        return Lark(f.read(), start='start', debug=True, lexer='dynamic_complete')


class Parsers:
    flyout = _make_parser('flyout')

    def __init__(self):
        raise RuntimeError("This class should not be instantiated")
