import pytest

from ashparser.parser import Parser


def test_parser_init_no_arguments():
    with pytest.raises(TypeError):
        Parser()
