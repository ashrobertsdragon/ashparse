from ashparser.parser import Parser


def test_parser_init_no_arguments():
    parser = Parser()
    assert parser
