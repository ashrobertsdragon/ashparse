import sys
from collections.abc import Sequence
from enum import Enum
from typing import Any, Literal

from .types_ import (
    AshParser,
    Argument,
    Names,
    ConditionalType,
    IndexedDict,
)


class Parser(AshParser):
    def __init__(
        self,
        name: str,
        alias: str | None = None,
        help: str | None = None,
        required: bool = False,
        show_help: bool = True,
    ) -> None:
        super().__init__(name, alias=alias, help=help, required=required)
        self.show_help = show_help

        self.arguments: list[AshParser] = []
        self._recurring_groups: list["Parser"] = []
        self._argument_groups: list["Parser"] = []
        self._mutually_exclusive_groups: list["Parser"] = []
        self._conditional_groups: list[tuple["Parser", ConditionalType]] = []

        self._groups: dict[str, list] = {
            "argument_group": self._argument_groups,
            "recurring_group": self._recurring_groups,
            "mutually_exclusive_group": self._mutually_exclusive_groups,
            "conditional_group": self._conditional_groups,
        }

        self._namespace = Names()
        self._parser_args: IndexedDict[str, Any] = IndexedDict()
        self._recurring_data: dict[str, list[dict[str, Any]]] = {}

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

        self._namespace[group.name] = tuple(arg_values)
        self._namespace.set_type(group.name, tuple[arg_types])
        return group

    def add_recurring_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> "Parser":
        return self._add_group("recurring_group", name, help, alias, required)

    def add_argument_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> "Parser":
        return self._add_group("argument_group", name, help, alias, required)

    def add_mutually_exclusive_group(
        self, name: str, help: str | None = None, required: bool = False
    ) -> "Parser":
        return self._add_group(
            "mutually_exclusive_group", name, help, required=required
        )

    def add_conditional_argument_group(
        self,
        name: str,
        help: str,
        conditional_type: ConditionalType,
        required: bool = False,
    ) -> "Parser":
        return self._add_group(
            "conditional_group",
            name,
            help,
            required=required,
            subtype=conditional_type,
        )

    @staticmethod
    def _add_parser_args(
        parser: "Parser", parser_args: IndexedDict[str, Any]
    ) -> IndexedDict[str, Any]:
        for arg in parser.arguments:
            parser_args[arg.name] = arg
            if arg.alias:
                parser_args[arg.alias] = arg
        return parser_args

    # Parser logic

    def _validate_choices(self, arg: Argument, converted: list[Any]) -> None:
        if arg.choices and (invalid := set(converted) - set(arg.choices)):
            raise ValueError(
                f"Invalid values for {arg.name}: {', '.join(map(str, invalid))} not in {arg.choices}"
            )

    def _validate_argument_count(
        self, arg: Argument, values: list[str]
    ) -> None:
        min_n, max_n = arg.num_args
        if not min_n <= len(values) <= max_n:
            raise ValueError(
                f"Argument {arg.name} expected {min_n} to {max_n} values, got {len(values)}"
            )

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

    def _pop_arg(self, arg: AshParser, token: str, position: int) -> None:
        if token.startswith("-"):
            if token == arg.alias:
                self._parser_args.pop(arg.name)
            self._parser_args.pop(token)
        else:
            self._parser_args.pop_from_index(position)

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
        self._parser_args = self._add_parser_args(parser, self._parser_args)
        self._recurring_data.update(
            {g.name: [] for g in parser._recurring_groups}
        )
        result: dict[str, Any] = {}
        position = 0
        total = len(tokens)

        while i < total:
            token = tokens[i]

            if (
                token not in self._parser_args
                and position != self._parser_args.position(token)
            ):
                raise ValueError(f"Unexpected token: {token}")

            i += 1
            results, i = self._parse_tokens(token, tokens, i, position)
            result.update(results)
            position += 1

            for name, group in self._recurring_data.items():
                result[name] = group

        return result, i

    def parse(self) -> Names:
        """
        Parse command line arguments.

        Raises:
            ValueError: If any arguments are missing or invalid.
        Returns:
            Names: Parsed command line arguments.
        """
        tokens = sys.argv[1:]
        result, _ = self._parse_arguments(self, tokens)

        self._validate_required_arguments(result)
        self._validate_mutually_exclusive_arguments(result)
        self._validate_conditional_arguments(result)

        for arg in self.arguments:
            if arg.name in result:
                self._namespace.values[arg.name] = result[arg.name]
            elif arg.required:
                raise ValueError(f"Missing required argument: {arg.name}")

        return self._namespace

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
                            f"{dep} cannot be used when {conditional} is not present"
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
                details += (
                    f" Choices: {', '.join(str(c) for c in arg.choices)}"
                )
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
            lines.extend(
                (
                    f"{pad}{parser.alias}, {parser.name}: {parser.help}",
                    self._format_help(indent + 1),
                )
            )
        return "\n".join(line for line in lines if line)

    def _format_usage(self) -> str:
        tokens: list[str] = []

        for arg in self.arguments:
            token = f"<{arg.name}>" if arg.required else f"[{arg.name}]"
            tokens.append(token)

        tokens.extend(
            f"({group.alias} <{group.name}>)"
            for group in self._argument_groups
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
                f"({' '.join(arg.name for arg in c_group.arguments[:1])} {symbol} {' '.join(arg.name for arg in c_group.arguments[1:])})"
            )

        return f"Usage: {self.name} " + " ".join(tokens) + "\n"

    def print_help(self):
        print(self._format_usage())
        print(self._format_help())
