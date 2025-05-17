import sys
from collections.abc import Sequence
from enum import Enum
from typing import Any, Literal

from indexed_dict import IndexedDict

from .types_ import (
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
        >>> parser.parse()
        {'arg1': {None: str}, 'arg2': {None: int}}
    """

    def __init__(
        self,
        name: str,
        alias: str | None = None,
        help: str | None = None,  # noqa: A002
        required: bool = False,
        show_help: bool = True,
        child: bool = False,
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
            show_help (bool, optional): Whether to show help for the parser.
                Defaults to True.
            child (bool, optional): Whether the parser is a child parser.
                Defaults to False for the root parser and set to True by the
                method `_add_group()`.
        """
        super().__init__(name, alias=alias, help=help, required=required)
        self.show_help = show_help
        self.child = child

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

        self._namespace = Names()
        self._parser_args: IndexedDict[str, Any] = IndexedDict()
        self._positional_args: IndexedDict[str, Any] = IndexedDict()
        self._recurring_data: dict[str, list[dict[str, Any]]] = {}
        self._consumed_args: list[str] = []

        if not self.child:
            self.positional = False

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
        group = Parser(
            name, alias=alias, help=help, required=required, child=True
        )
        _group = (subtype, group) if subtype else group

        self._groups[group_type].append(_group)
        self.arguments.append(group)
        arg_values: list[Any] = []
        arg_types: list[type] = []
        for arg in group.arguments:
            if isinstance(arg, Argument) and arg.default:
                value = arg.default
                self._namespace[arg.name] = value
                arg_values.append(value)

            arg_type = getattr(arg, "type", str)
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

    def _add_parser_args(
        self,
        parser: "Parser",
    ) -> None:
        for arg in parser.arguments:
            if not arg.name.startswith("--"):
                self._positional_args[arg.name] = arg
            self._parser_args[arg.name] = arg
            if arg.alias:
                self._parser_args[arg.alias] = arg

    # Parser logic
    def parse(self) -> Names:
        """Parse command line arguments.

        Raises:
            ValueError: If any arguments are missing or invalid.

        Returns:
            Names: Parsed command line arguments.
        """
        tokens = sys.argv[1:]
        result, _ = self._parse_arguments(self, tokens)

        self._validate_mutually_exclusive_arguments(result)
        self._validate_conditional_arguments(result)

        flattened = self._flatten_result(result)
        self._validate_required_arguments(flattened)

        for arg in self.arguments:
            if arg.name in flattened:
                self._namespace.values[arg.name] = flattened[arg.name]
            elif arg.required:
                raise ValueError(f"Missing required argument: {arg.name}")

        return self._namespace

    def _parse_argument(
        self, i: int, arg: Argument, tokens: list[str]
    ) -> tuple[dict[str, Any], int]:
        values, i = self._collect_argument_values(i, arg, tokens, len(tokens))
        self._validate_argument_count(arg, values)
        converted = list(map(arg.type, values))

        self._validate_choices(arg, converted)
        return {arg.name: converted}, i

    def _parse_group(
        self, arg: "Parser", i: int, tokens: list[str]
    ) -> tuple[dict[str, Any], int]:
        group_result, i = self._parse_arguments(arg, tokens[i:])

        if arg.name in self._recurring_data:
            self._recurring_data[arg.name].append(group_result)
            return {}, i
        return {arg.name: group_result}, i

    def _parse_tokens(
        self, token: str, tokens: list[str], i: int, position: int
    ) -> tuple[dict[str, Any], int]:
        arg = self._parser_args[token]

        if token not in self._recurring_data:
            self._pop_arg(arg, token, position)

        if isinstance(arg, Argument):
            result, i = self._parse_argument(i, arg, tokens)
        elif isinstance(arg, Parser):
            result, i = self._parse_group(arg, i, tokens)
        else:
            raise NotImplementedError

        return result, i

    def _parse_arguments(
        self, parser: "Parser", tokens: list[str], i: int = 0
    ) -> tuple[dict[str, Any], int]:
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
                raise ValueError(f"Unknown argument: {token}")

            i += 1
            results, i = self._parse_tokens(token, tokens, i, position)
            result.update(results)
            position += 1

            for name, group in self._recurring_data.items():
                result[name] = group

        return result, i

    def _pop_arg(self, arg: AshParser, token: str, position: int) -> None:
        if token.startswith("-"):
            self._consumed_args.append(arg.name)
            if token == arg.alias:
                self._parser_args.pop(arg.name)
            self._parser_args.pop(token)
        else:
            self._parser_args.pop_from_index(position)

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

    def _validate_choices(self, arg: Argument, converted: list[Any]) -> None:
        if arg.choices and (invalid := set(converted) - set(arg.choices)):
            raise ValueError(
                f"Invalid values for {arg.name}: "
                f"{', '.join(map(str, invalid))} not in {arg.choices}"
            )

    def _validate_argument_count(
        self, arg: Argument, values: list[str]
    ) -> None:
        min_n, max_n = arg.num_args
        if not min_n <= len(values) <= max_n:
            raise ValueError(
                f"Argument {arg.name} expected {min_n} to {max_n} values, "
                f"got {len(values)}"
            )

    def _validate_required_arguments(self, result: dict[str, Any]) -> None:
        for arg in self.arguments:
            if arg.required and arg.name not in result:
                raise ValueError(f"Missing required argument: {arg.name}")

    def _validate_mutually_exclusive_arguments(
        self, result: dict[str, Any]
    ) -> None:
        for group in self._mutually_exclusive_groups:
            used = [arg.name for arg in group.arguments if arg in result]
            if len(used) > 1:
                raise ValueError(
                    f"Mutually exclusive arguments used: {', '.join(used)}"
                )

    def _validate_conditional_arguments(self, result: dict[str, Any]) -> None:
        for group, ctype in self._conditional_groups:
            conditional = group.arguments[0]
            cond_present = conditional in result
            dependents = group.arguments[1:]
            for dep in dependents:
                dep_present = dep in result
                if ctype == ConditionalType.FIRST_PRESENT_REST_REQUIRED:
                    if cond_present and not dep_present:
                        raise ValueError(
                            f"{dep} is required when {conditional} is used"
                        )
                elif ctype == ConditionalType.FIRST_ABSENT_REST_FORBIDDEN:
                    if not cond_present and dep_present:
                        raise ValueError(
                            f"{dep} cannot be used when {conditional} "
                            "is not present"
                        )

    # Help generation
    def _format_help(self, indent: int = 0) -> str:
        lines = []
        if not self.show_help:
            return ""

        pad = "  " * indent

        for arg in self.arguments:
            name = f"{arg.alias}, {arg.name}" if arg.alias else arg.name
            details = f"{pad}{name}: {arg.help}"
            if arg.required:
                details += " (required)"
            if isinstance(arg, Argument) and arg.choices:
                details += f" Choices: {', '.join(str(c) for c in arg.choices)}"
            lines.append(details)

        for ex_group in self._mutually_exclusive_groups:
            items = " | ".join(arg.name for arg in ex_group.arguments)
            lines.append(f"{pad}({items})")

        for c_group, ctype in self._conditional_groups:
            symbol = {
                ConditionalType.FIRST_PRESENT_REST_REQUIRED: "&",
                ConditionalType.FIRST_ABSENT_REST_FORBIDDEN: "&|",
            }[ctype]
            parts = f" {symbol} ".join(arg.name for arg in c_group.arguments)
            lines.append(f"{pad}({parts})")

        for parser in self._argument_groups + self._recurring_groups:
            lines.extend((
                f"{pad}{parser.alias}, {parser.name}: {parser.help}",
                self._format_help(indent + 1),
            ))
        return "\n".join(line for line in lines if line)

    def _format_usage(self) -> str:
        tokens: list[str] = []

        for arg in self.arguments:
            token = f"<{arg.name}>" if arg.required else f"[{arg.name}]"
            tokens.append(token)

        tokens.extend(
            f"({group.alias} <{group.name}>)" for group in self._argument_groups
        )
        tokens.extend(
            f"[{r_group.alias} <{r_group.name}...>]"
            for r_group in self._recurring_groups
        )
        for ex_group in self._mutually_exclusive_groups:
            token = " | ".join(arg.name for arg in ex_group.arguments)
            tokens.append(f"[{token}]")

        for c_group, ctype in self._conditional_groups:
            symbol = {
                ConditionalType.FIRST_PRESENT_REST_REQUIRED: "&",
                ConditionalType.FIRST_ABSENT_REST_FORBIDDEN: "&|",
            }[ctype]
            tokens.append(
                f"({' '.join(arg.name for arg in c_group.arguments[:1])} "
                f"{symbol} "
                f"{' '.join(arg.name for arg in c_group.arguments[1:])})"
            )

        return f"Usage: {self.name} " + " ".join(tokens) + "\n"

    def print_help(self) -> None:
        """Print help message."""
        print(self._format_usage())
        print(self._format_help())
