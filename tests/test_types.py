import pytest

from ashparser.types_ import Argument


class TestArgument:
    def test_argument_init_no_arguments(self):
        with pytest.raises(TypeError):
            Argument()  # type: ignore testing for missing arguments

    def test_argument_init_no_type(self):
        with pytest.raises(TypeError):
            Argument("foo")  # type: ignore testing for missing arguments

    def test_argument_init(self):
        arg = Argument("foo", type=int)
        assert arg.name == "foo"
        assert arg.type is int

    def test_argument_optional_arguments_defaults(self):
        arg = Argument("foo", type=int)
        assert arg.alias is None
        assert arg.help is None
        assert arg.descriptor is None
        assert arg.num_args is None
        assert arg.required is False
        assert arg.choices is None

    def test_argument_set_alias_single(self):
        arg = Argument(
            "foo",
            type=int,
            alias="a",
        )
        assert arg.alias == "a"

    def test_argument_set_alias_with_dash(self):
        arg = Argument(
            "foo",
            type=int,
            alias="-a",
        )
        assert arg.alias == "-a"

    def test_argument_set_help(self):
        arg = Argument("foo", type=int, help="bar")
        assert arg.help == "bar"

    def test_argument_set_descriptor(self):
        arg = Argument("foo", type=int, descriptor="bar")
        assert arg.descriptor == "bar"

    def test_argument_set_num_args_plus(self):
        arg = Argument("foo", type=int, num_args="+")
        assert arg.num_args == "+"
        assert arg._num_args == (1, float("inf"))

    def test_argument_set_num_args_question(self):
        arg = Argument("foo", type=int, num_args="?")
        assert arg.num_args == "?"
        assert arg._num_args == (0, 1)

    def test_argument_set_num_args_star(self):
        arg = Argument("foo", type=int, num_args="*")
        assert arg.num_args == "*"
        assert arg._num_args == (0, float("inf"))

    def test_argument_set_num_args_int(self):
        arg = Argument("foo", type=int, num_args=2)
        assert arg.num_args == 2
        assert arg._num_args == (2, 2)

    def test_argument_num_args_not_set(self):
        arg = Argument("foo", type=int)
        assert arg._num_args == (1, 1)

    def test_argument_set_choices(self):
        arg = Argument("foo", type=int, choices=[1, 2, 3])
        assert arg.choices == {1, 2, 3}

    def test_argument_set_min_max(self):
        arg = Argument("foo", type=int, min=1, max=2)
        assert arg._min == 1
        assert arg._max == 2
        assert arg.choices == {1, 2}

    def test_argument_set_choices_and_min_max(self):
        with pytest.raises(ValueError):
            Argument("foo", type=int, choices=[1, 2, 3], min=1, max=2)

    def test_argument_set_min_max_and_choices(self):
        with pytest.raises(ValueError):
            Argument("foo", type=int, min=1, max=2, choices=[1, 2, 3])

    def test_argument_set_required(self):
        arg = Argument("foo", type=int, required=True)
        assert arg.required

    def test_argument_required_not_set(self):
        arg = Argument("foo", type=int)
        assert not arg.required
