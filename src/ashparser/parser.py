import sys
from collections.abc import Sequence
from enum import Enum
from typing import Any, Literal

from indexed_dict import IndexedDict

from ashparser import exceptions
from ashparser.help_formatter import HelpFormatter
from ashparser.types_ import (
    Argument,
    AshParser,
    ConditionalType,
    Names,
)


class Parser(AshParser):
    """AshParser parser for command line arguments.

    The AshParser command line argument parser is inspired by Python's argparse,
    but with typing and better argument group support.

    Attributes:
        arguments (list[AshParser]): List of arguments for the parser.

    Methods:
        add_argument: Add an argument to the parser.
        add_argument_group: Add an argument group to the parser as a subparser.
        add_recurring_group: Add an argument group that can be used multiple
            times to the parser.
        add_mutually_exclusive_group: Add a group of mutually exclusive
            arguments to the parser.
        add_conditional_group: Add an argument group to the parser where
            arguments can be conditionally required.
        parse: Parse command line arguments.

    Raises:
        ParserError: If the parser is not valid.

    Example:
        >>> parser = Parser("my_parser")
        >>> parser.add_argument("arg1", type=str)
        >>> parser.add_argument("arg2", type=int)
        >>> parser.parse(["apple", "2"])  # simulate command line with list
        {'arg1': {"apple": str}, 'arg2': {2: int}}
    """

    def __init__(
        self,
        name: str,
        alias: str | None = None,
        help: str | None = None,  # noqa: A002
        required: bool = False,
        show_help: bool = True,
    ) -> None:
        """Initialize the parser.

        Args:
            name (str): Name of the parser.
            alias (str | None, optional): Alias for the parser.
                Defaults to None.
            help (str | None, optional): Help text for the parser.
                Defaults to None.
            required (bool, optional): Whether the parser is required.
                Defaults to False.
            show_help (bool, optional): Whether to pass the help for the parser
                up to the parent. Defaults to True.
        """
        super().__init__(name, alias=alias, help=help, required=required)
        self.show_help = show_help

        self.arguments: list[AshParser] = []
        self._recurring_groups: list[Parser] = []
        self._argument_groups: list[Parser] = []
        self._mutually_exclusive_groups: list[Parser] = []
        self._conditional_groups: list[tuple[Parser, ConditionalType]] = []

        self._groups: dict[str, list] = {
            "argument_group": self._argument_groups,
            "recurring_group": self._recurring_groups,
            "mutually_exclusive_group": self._mutually_exclusive_groups,
            "conditional_group": self._conditional_groups,
        }

        self._groups_by_type: dict[Parser, str] = {}

        self._namespace = Names()
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
        """Add an argument to the parser.

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
                Number of arguments for the argument. Defaults to None.
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
            >>> parser.add_argument("arg1", type=str)
            >>> parser.add_argument(
            ...     "arg2", type=int, help="Help text for arg2", required=True
            ... )
            >>> parser.add_argument("arg3", type=float, default=3.14)
            >>> parser.add_argument("arg4", type=str, num_args="+")
            >>> parser.add_argument("arg5", type=str, num_args=2)
            >>> parser.add_argument("arg6", type=str, choices=["a", "b", "c"])
            >>> parser.parse()
        """
        arg = Argument(
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
        self.arguments.append(arg)
        if arg.default:
            self._namespace[arg.name] = arg.default
        self._namespace.set_type(arg.name, arg.type)

    def _add_group(
        self,
        group_type: str,
        name: str,
        help: str | None = None,
        alias: str | None = None,
        required: bool = False,
        subtype: Enum | None = None,
    ) -> "Parser":
        group = Parser(name, alias=alias, help=help, required=required)
        _group = (group, subtype) if subtype else group

        self._groups[group_type].append(_group)
        self.arguments.append(group)
        self._groups_by_type[group] = group_type

        arg_values: list[Any] = []
        arg_types: list[type] = []
        for arg in group.arguments:
            if isinstance(arg, Argument) and arg.default:
                value = arg.default
                self._namespace[arg.name] = value
                arg_values.append(value)

            arg_type: type = getattr(arg, "type", str)
            self._namespace.set_type(arg.name, arg_type)
            arg_types.append(arg_type)

        if group_type == "recurring_group":
            self._namespace[group.name] = tuple(arg_values)
            self._namespace.set_type(group.name, tuple[arg_types])
        return group

    def add_argument_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> "Parser":
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
            Parser: A new Parser instance for the argument group.

        Example:
            parser = Parser("my_parser")
            parser.add_argument("arg1", type=str)
            group1 = parser.add_argument_group("group1", "Help text for group1")
            group1.add_argument("arg2", type=bool)
            group1.add_argument("arg3", type=int)
            parser.parse()
        """
        return self._add_group("argument_group", name, help, alias, required)

    def add_recurring_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> "Parser":
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
            Parser: A new Parser instance for the recurring group.

        Example:
            >>> parser = Parser("my_parser")
            >>> parser.add_argument("arg1", type=str)
            >>> group1 = parser.add_recurring_group(
            ...     "group1", "Help text for group1"
            ... )
            >>> group1.add_argument("arg2", type=bool)
            >>> group1.add_argument("arg3", type=int)
            >>> args = parser.parse()
            >>> print(args)
            {
                "arg1": "value1",
                "group1": [
                    {
                        "arg2": True,
                        "arg3": 1
                    },
                    {
                        "arg2": False,
                        "arg3": 2
                    }
                ]
            }
        """
        return self._add_group("recurring_group", name, help, alias, required)

    def add_mutually_exclusive_group(
        self, name: str, help: str | None = None, required: bool = False
    ) -> "Parser":
        """Add a mutually exclusive group to the parser.

        A mutually exclusive group is a group of mutually exclusive arguments.

        Args:
            name (str): Name of the mutually exclusive group.
            help (str | None, optional): Help text for the mutually exclusive
                group. Defaults to None.
            required (bool, optional): Whether the mutually exclusive group is
                required. Defaults to False.

        Returns:
            Parser: A new Parser instance for the mutually exclusive group.
        """
        return self._add_group(
            "mutually_exclusive_group", name, help, required=required
        )

    def add_conditional_argument_group(
        self,
        name: str,
        help: str,
        conditional_type: ConditionalType,
    ) -> "Parser":
        """Add a conditional argument group to the parser.

        A conditional argument group is a group of arguments where certain
        arguments can be conditionally required or forbidden.

        Args:
            name (str): Name of the conditional argument group.
            help (str): Help text for the conditional argument group.
            conditional_type (ConditionalType): Type of the conditional argument
                group.

        Returns:
            Parser: A new Parser instance for the conditional argument group.
        """
        return self._add_group(
            "conditional_group",
            name,
            help,
            required=False,
            subtype=conditional_type,
        )

    # Parser logic
    def parse(self) -> Names:
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
            >>> parser = Parser()
            >>> parser.add_argument("input_file", type=str, required=True)
            >>> parser.add_argument("--verbose", action="store_true")

            >>> args = parser.parse()
            >>> print(args.input_file)
            >>> if args.verbose:
            >>>    print("Verbose mode enabled.")
        """  # noqa: DOC502
        tokens = sys.argv[1:]
        result, _ = self._parse_args(self, tokens)

        self._validate_mutually_exclusive_arguments(result)
        self._validate_conditional_arguments(result)

        flattened = self._flatten_result(result)
        self._validate_required_arguments(flattened)

        for arg in self.arguments:
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
        self, arg: "Parser", i: int, tokens: list[str]
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
        parser: "Parser",
    ) -> None:
        for arg in parser.arguments:
            if not arg.name.startswith("--"):
                self._positional_args[arg.name] = arg
            self._parser_args[arg.name] = arg
            if arg.alias:
                self._parser_args[arg.alias] = arg

    def _parse_args(
        self, parser: "Parser", tokens: list[str], i: int = 0
    ) -> tuple[dict[str, Any], int]:
        self._index_parser_args(parser)
        self._recurring_data.update({
            g.name: [] for g in parser._recurring_groups
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
        elif isinstance(arg, Parser):
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
        for arg in self.arguments:
            if arg.required and arg.name not in result:
                raise exceptions.MissingRequiredArgumentError(arg.name)

    def _validate_mutually_exclusive_arguments(
        self, result: dict[str, Any]
    ) -> None:
        for group in self._mutually_exclusive_groups:
            used = [arg.name for arg in group.arguments if arg in result]
            if len(used) > 1:
                raise exceptions.MutuallyExclusiveArgumentsError(used)

    def _validate_conditional_arguments(self, result: dict[str, Any]) -> None:
        # sourcery skip: raise-from-previous-error
        for group, ctype in self._conditional_groups:
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
        formatter = help_formatter(self)
        print(formatter.format_help())
