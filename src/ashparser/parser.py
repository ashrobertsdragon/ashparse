import sys
from collections.abc import Sequence
from typing import Any, Literal

from indexed_dict import IndexedDict

from ashparser import exceptions
from ashparser.argument import Argument
from ashparser.group import ArgumentGroup
from ashparser.help_formatter import HelpFormatter
from ashparser.mixins import AddMixin
from ashparser.names import Names
from ashparser.types_ import (
    AshParser,
    ConditionalType,
    GroupType,
)


class Parser(AddMixin):
    """AshParser parser for command line arguments.

    The AshParser command line argument parser is inspired by Python's argparse,
    but with typing and better argument group support.

    Methods:
        add_argument: Add an argument to the argument group.
        add_argument_group: Add an argument group to the argument group as a
            nested group.
        add_recurring_group: Add an argument group that can be used multiple
            times to the argument group.
        add_mutually_exclusive_group: Add a group of mutually exclusive
            arguments to the argument group.
        add_conditional_group: Add an argument group to the argument group where
            arguments can be conditionally required.
        parse: Parse the command line arguments and return the namespace.

    Example:
        >>> parser = Parser("example")
        >>> parser.add_argument("input", type=str)
        >>> parser.add_argument("count", type=int, default=1)
        >>> args = parser.parse(["file.txt"])
        >>> print(args)
        {
            "input": {"value": "file.txt", "type": str},
            "count": {"value": 1, "type": int}
        }
    """

    def __init__(self, name: str = "", help: str | None = None) -> None:
        """Initialize a new Parser instance.

        Args:
            name (str): Name of the parser (used for internal grouping).
            help (str | None): Optional help description.
        """
        self._namespace = Names()
        self._root_group = ArgumentGroup(
            namespace=self._namespace, name=name, help=help
        )
        self._parser_args: IndexedDict[str, Any] = IndexedDict()
        self._positional_args: IndexedDict[str, Any] = IndexedDict()
        self._recurring_data: dict[str, list[dict[str, Any]]] = {}
        self._consumed_args: list[str] = []

    def add_argument(
        self,
        name: str,
        *,
        type: type,
        alias: str | None = None,
        help: str | None = None,
        default: Any = None,
        descriptor: str | None = None,
        num_args: Literal["?", "*", "+"] | int | None = None,
        required: bool = False,
        choices: Sequence[Any] | None = None,
        min: int | None = None,
        max: int | None = None,
    ) -> None:
        """Add an argument to the argument group.

        Args:
            name (str): Name of the argument.
            type (type): Type of the argument.
            alias (str | None, optional): Alias for the argument.
                Defaults to None.
            help (str | None, optional): Help text for the argument.
                Defaults to None.
            default (Any, optional): Default value for the argument.
                Defaults to None.
            descriptor (str | None, optional): Descriptor for the argument.
                Defaults to None.
            num_args (Literal["?", "*", "+"] | int | None, optional):
                Specifies how many values are expected:
                    - '?' = zero or one
                    - '*' = zero or more
                    - '+' = one or more
                    - int = exactly that many
                    - None = exactly one (default behavior)
            required (bool, optional): Whether the argument is required.
                Defaults to False.
            choices (Sequence[Any] | None, optional): Choices for the argument.
                Defaults to None.
            min (int | None, optional): Minimum value for the argument.
                Defaults to None.
            max (int | None, optional): Maximum value for the argument.
                Defaults to None.

        Example:
            >>> parser = Parser("my_parser")
            >>> parser.add_argument("--arg1", type=str)
            >>> parser.add_argument(
            ...     "--arg2", type=int, help="Help text for arg2", required=True
            ... )
            >>> parser.add_argument("arg3", type=float, default=3.14)
            >>> parser.add_argument("--arg4", type=str, num_args="+")
            >>> parser.add_argument("--arg5", type=str, num_args=2)
            >>> parser.add_argument("arg6", type=str, choices=["a", "b", "c"])
            >>> args = parser.parse([
            ...     "--arg2",
            ...     "42",
            ...     "2.71",  # arg3
            ...     "--arg4",
            ...     "foo",
            ...     "bar",
            ...     "--arg5",
            ...     "x",
            ...     "y",
            ...     "b",  # arg6
            ...     "--level",
            ...     "7",
            ... ])
            >>> print(args)
            {
                "arg2": {"value": 42, "type": int},
                "arg3": {"value": 2.71, "type": float},
                "arg4": {"value": ["foo", "bar"], "type": str},
                "arg5": {"value": ["x", "y"], "type": str},
                "arg6": {"value": "b", "type": str},
                "level": {"value": 7, "type": int},
            }
        """
        self._add_argument_to(
            self._root_group,
            name,
            type=type,
            alias=alias,
            help=help,
            default=default,
            descriptor=descriptor,
            num_args=num_args,
            required=required,
            choices=choices,
            min=min,
            max=max,
        )

    def add_argument_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> ArgumentGroup:
        """Add an argument group to the parser.

        An argument group is a grouping of arguments using a subparser.

        Args:
            name (str): Name of the argument group.
            help (str): Help text for the argument group.
            alias (str | None, optional): Alias for the argument group.
                Defaults to None.
            required (bool, optional): Whether the argument group is required.
                Defaults to False.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the argument group.

        Example:
            >>> parser = Parser("my_parser")
            >>> group = parser.add_argument_group(
            ...     "credentials", "Login credentials"
            ... )
            >>> group.add_argument("username", type=str)
            >>> group.add_argument("password", type=str)
            >>> result = parser.parse(["user", "secret"])
            >>> print(result)
            {
                "credentials": {
                    "username": {"value": "user", "type": str},
                    "password": {"value": "secret", "type": str}
                }
            }
        """
        return self._add_argument_group_to(
            self._root_group, name, required=required
        )

    def add_recurring_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> ArgumentGroup:
        """Add a recurring group to the parser.

        A recurring group is a group of arguments that can be used multiple
        times in the same command line.

        Args:
            name (str): Name of the recurring group.
            help (str): Help text for the recurring group.
            alias (str | None, optional): Alias for the recurring group.
                Defaults to None.
            required (bool, optional): Whether the recurring group is required.
                Defaults to False.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the recurring group.

        Example:
            >>> parser = Parser("job_parser")
            >>> job_group = parser.add_recurring_group(
            ...     "--job", "Job entry group"
            ... )
            >>> job_group.add_argument("name", type=str)
            >>> job_group.add_argument("duration", type=int)
            >>> result = parser.parse([
            ...     "--job",
            ...     "name",
            ...     "build",
            ...     "duration",
            ...     "120",
            ...     "--job",
            ...     "name",
            ...     "test",
            ...     "duration",
            ...     "30",
            ... ])
            >>> print(result)
            {
                "--job": [
                    {
                        "name": {"value": "build", "type": str},
                        "duration": {"value": 120, "type": int}
                    },
                    {   "name": {"value": "test", "type": str},
                        "duration": {"value": 30, "type": int}
                    }
                ]
            }
        """
        return self._add_recurring_group_to(
            self._root_group, name, help, alias, required
        )

    def add_mutually_exclusive_group(
        self, name: str, help: str | None = None, required: bool = False
    ) -> ArgumentGroup:
        """Add a mutually exclusive group to the parser.

        A mutually exclusive group is a group of mutually exclusive arguments.

        Args:
            name (str): Name of the mutually exclusive group.
            help (str | None, optional): Help text for the mutually exclusive
                group. Defaults to None.
            required (bool, optional): Whether the mutually exclusive group is
                required. Defaults to False.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the mutually
                exclusive group.

        Example:
            >>> parser = Parser("my_parser")
            >>> mx = parser.add_mutually_exclusive_group("output")
            >>> mx.add_argument("--json", type=bool)
            >>> mx.add_argument("--xml", type=bool)
            >>> result = parser.parse(["--json", "true"])
            >>> print(result)
            {
                "output": {
                    "--json": {"value": True, "type": bool}
                }
            }
        """
        return self._add_mutually_exclusive_group_to(
            self._root_group, name, help, required=required
        )

    def add_conditional_argument_group(
        self,
        name: str,
        help: str,
        conditional_type: ConditionalType,
    ) -> ArgumentGroup:
        """Add a conditional argument group to the parser.

        A conditional argument group is a group of arguments where certain
        arguments can be conditionally required or forbidden.

        Args:
            name (str): Name of the conditional argument group.
            help (str): Help text for the conditional argument group.
            conditional_type (ConditionalType): Type of the conditional argument
                group.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the conditional
                argument group.

        Example:
            >>> parser = Parser("my_parser")
            >>> cond = parser.add_conditional_argument_group(
            ...     "db",
            ...     "Database options",
            ...     conditional_type=ConditionalType.FIRST_PRESENT_REST_REQUIRED,
            ... )
            >>> cond.add_argument("--use-db", type=bool)
            >>> cond.add_argument("--db-name", type=str)
            >>> result = parser.parse([
            ...     "--use-db",
            ...     "true",
            ...     "--db-name",
            ...     "my_db",
            ... ])
            >>> print(result)
            {
                "db": {
                    "--use-db": {"value": True, "type": bool},
                    "--db-name": {"value": "my_db", "type": str}
                }
            }
        """  # noqa 501
        return self._add_conditional_group_to(
            self._root_group, conditional_type, name, help
        )

    def parse(self, args: list[str] = sys.argv[1:]) -> Names:
        """Parses command-line arguments into a typed `Names` object.

        This method consumes arguments from `sys.argv[1:]` and:
        - Matches tokens to expected arguments including positional, optional,
            and recurring groups
        - Applies argument validation rules (e.g. required, mutually exclusive,
            and conditional)
        - Converts argument values to the appropriate types
        - Returns a structured, typed object with the parsed results

        Returns:
            Names: A typed namespace containing all parsed argument values.
                Each argument can be accessed via its name attribute
                    (e.g. `args.input_file`) or dictionary-style
                    (e.g. `args["input_file"]`).

        Raises:
            MissingRequiredArgumentError: If a required argument is
                missing.
            UnknownArgumentError: If an unexpected argument is
                encountered.
            MutuallyExclusiveArgumentError: If mutually exclusive
                arguments are provided.
            ConditionalArgumentError: If a conditional argument is
                not provided.
            InvalidValueError: If an argument has an invalid value.
            ArgumentTypeError: If an argument has an invalid type.
            InvalidChoiceError: If an argument has an invalid choice.
            TooManyArgumentsError: If too many arguments are provided.
            TooFewArgumentsError: If too few arguments are provided.

        Notes:
            - Recurring groups will be returned as a list of dictionaries.
            - If an argument is not provided and has no default, it will not
                appear in the result.
            - Argument types are validated and converted before being stored.

        Example:
            >>> parser = ArgumentGroup()
            >>> parser.add_argument("input_file", type=str, required=True)
            >>> parser.add_argument("--verbose", default=False, type=bool)

            >>> args = parser.parse(["input.txt"])
            >>> print(args)
            >>> {
            ...     "input_file": {"value": "input.txt", "type": str},
            ...     "--verbose": {"value": False, "type": bool},
            ... }
        """  # noqa: DOC502
        result, _ = self._parse_args(self._root_group, args)

        self._validate_mutually_exclusive_arguments(result)
        self._validate_conditional_arguments(result)

        flattened = self._flatten_result(result)
        self._validate_required_arguments(flattened)

        for arg in self._root_group.arguments:
            if arg.name in flattened:
                self._namespace.values[arg.name] = flattened[arg.name]
            elif arg.required:
                raise exceptions.MissingRequiredArgumentError(arg.name)

        return self._namespace

    def _consume_argument(
        self, i: int, arg: Argument, tokens: list[str]
    ) -> tuple[dict[str, Any], int]:
        values, i = self._collect_argument_values(i, arg, tokens, len(tokens))
        self._validate_argument_count(arg, values)
        converted = list(map(arg.type, values))

        self._validate_choices(arg, converted)
        return {arg.name: converted}, i

    def _consume_group(
        self, arg: ArgumentGroup, i: int, tokens: list[str]
    ) -> tuple[dict[str, Any], int]:
        group_result, i = self._parse_args(arg, tokens[i:])

        if arg.name in self._recurring_data:
            self._recurring_data[arg.name].append(group_result)
            return {}, i
        return {arg.name: group_result}, i

    def _collect_argument_values(
        self,
        i: int,
        arg: Argument,
        tokens: list[str],
        total: int,
    ) -> tuple[list[str], int]:
        values = []

        while (
            i < total
            and len(values) < arg.num_args[1]
            and not (
                (peek := tokens[i]).startswith("-")
                and arg.type
                not in {
                    int,
                    float,
                }
            )
        ):
            values.append(peek)
            i += 1

        return values, i

    def _flatten_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Flatten non-recurring groups in result.

        Args:
            result: The parsed result to flatten.

        Returns:
            dict: Flattened result.
        """
        flat_result = {}

        for name, value in result.items():
            if name not in self._recurring_data and isinstance(value, dict):
                for arg_name, arg_value in value.items():
                    flat_result[arg_name] = arg_value
            else:
                flat_result[name] = value
        return flat_result

    def _index_parser_args(
        self,
        parser: ArgumentGroup,
    ) -> None:
        for arg in parser.arguments:
            if not arg.name.startswith("--"):
                self._positional_args[arg.name] = arg
            self._parser_args[arg.name] = arg
            if arg.alias:
                self._parser_args[arg.alias] = arg

    def _parse_args(
        self, parser: ArgumentGroup, tokens: list[str], i: int = 0
    ) -> tuple[dict[str, Any], int]:
        self._index_parser_args(parser)
        self._recurring_data.update({
            g.name: []
            for g in parser.arguments
            if isinstance(g, ArgumentGroup)
            and g.group_type == GroupType.RECURRING
        })
        result: dict[str, Any] = {}
        position = 0
        total = len(tokens)

        while i < total:
            token = tokens[i]
            last_consumed = (
                self._consumed_args[-1]
                if self._consumed_args
                else self._parser_args.get_key_from_index(0)
            )
            next_positional = self._positional_args.get_key_from_index(position)

            if token in self._parser_args:
                last_consumed = token
                self._consumed_args.append(token)
            elif self._parser_args.position(
                last_consumed
            ) > self._parser_args.position(next_positional):
                raise exceptions.UnknownArgumentError(token)

            i += 1
            results, i = self._parse_tokens(token, tokens, i, position)
            result.update(results)
            position += 1

            for name, group in self._recurring_data.items():
                result[name] = group

        return result, i

    def _parse_tokens(
        self, token: str, tokens: list[str], i: int, position: int
    ) -> tuple[dict[str, Any], int]:
        arg = self._parser_args[token]

        if token not in self._recurring_data:
            self._pop_consumed_arg(arg, token, position)

        if isinstance(arg, Argument):
            result, i = self._consume_argument(i, arg, tokens)
        elif isinstance(arg, ArgumentGroup):
            result, i = self._consume_group(arg, i, tokens)
        else:
            raise NotImplementedError

        return result, i

    def _pop_consumed_arg(
        self, arg: AshParser, token: str, position: int
    ) -> None:
        if token.startswith("-"):
            self._consumed_args.append(arg.name)
            if token == arg.alias:
                self._parser_args.pop(arg.name)
            self._parser_args.pop(token)
        else:
            self._parser_args.pop_from_index(position)

    def _validate_choices(self, arg: Argument, converted: list[Any]) -> None:
        if arg.choices and (invalid := set(converted) - set(arg.choices)):
            raise exceptions.InvalidChoiceError(
                arg.name, invalid, list(arg.choices)
            )

    def _validate_argument_count(
        self, arg: Argument, values: list[str]
    ) -> None:
        min_n, max_n = arg.num_args
        actual_n = len(values)
        if actual_n < min_n:
            raise exceptions.TooFewArgumentsError(arg.name, min_n, actual_n)
        if actual_n > max_n:
            raise exceptions.TooManyArgumentsError(arg.name, max_n, actual_n)

    def _validate_required_arguments(self, result: dict[str, Any]) -> None:
        for arg in self._root_group.arguments:
            if arg.required and arg.name not in result:
                raise exceptions.MissingRequiredArgumentError(arg.name)

    def _validate_mutually_exclusive_arguments(
        self, result: dict[str, Any]
    ) -> None:
        for argument in self._root_group.arguments:
            if not isinstance(argument, ArgumentGroup):
                continue
            if argument.group_type != GroupType.MUTEX:
                continue
            group = argument
            used = [arg.name for arg in group.arguments if arg in result]
            if len(used) > 1:
                raise exceptions.MutuallyExclusiveArgumentsError(used)

    def _validate_conditional_arguments(self, result: dict[str, Any]) -> None:
        # sourcery skip: raise-from-previous-error
        for argument in self._root_group.arguments:
            if not isinstance(argument, ArgumentGroup):
                continue
            if argument.group_type != GroupType.CONDITIONAL:
                continue
            group = argument
            ctype = group.subtype
            if not ctype:
                raise NotImplementedError
            conditional = group.arguments[0]
            cond_present = conditional in result
            dependents = group.arguments[1:]
            for dep in dependents:
                dep_present = dep in result
                validator_name = f"_validate_{ctype.value}"
                try:
                    validator = getattr(self, validator_name)
                except AttributeError:
                    raise NotImplementedError(
                        "No validator implemented for conditional type "
                        f"'{ctype.value}'"
                    )

                validator(conditional, dep, cond_present, dep_present)

    @staticmethod
    def _validate_first_present_rest_required(
        conditional: AshParser,
        dep: AshParser,
        cond_present: bool,
        dep_present: bool,
    ) -> None:
        if cond_present and not dep_present:
            raise exceptions.ConditionalDependencyError(
                arg_name=dep.name,
                condition=conditional.name,
                relation="is required when",
            )

    @staticmethod
    def _validate_first_absent_rest_forbidden(
        conditional: AshParser,
        dep: AshParser,
        cond_present: bool,
        dep_present: bool,
    ) -> None:
        if not cond_present and dep_present:
            raise exceptions.ConditionalDependencyError(
                arg_name=dep.name,
                condition=conditional.name,
                relation="is forbidden when",
            )

    # Help generation
    def print_help(self, help_formatter: type[HelpFormatter]) -> None:
        """Print the help text for the parser."""
        formatter = help_formatter(self._root_group)
        print(formatter.format_help())
