from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ashparser.argument import Argument
    from ashparser.group import ArgumentGroup
    from ashparser.types_ import AshParser, ConditionalType


class HelpFormatter:
    """A help formatter for the ArgumentGroup."""

    def __init__(self, group: ArgumentGroup, indent_size: int = 4) -> None:
        """Initialize the help formatter.

        Args:
            group (ArgumentGroup): The group to format help for.
            indent_size (int, optional): The size of the indentation.
                Defaults to 4.
        """
        self.group = group
        self.indent_size = indent_size

        # Dispatch table: group_type → formatting method
        self.usage_strategies: dict[
            str, Callable[[ArgumentGroup, list[str]], str]
        ] = {
            "argument_group": self._usage_none,
            "mutually_exclusive_group": self._usage_parens,
            "recurring_group": self._usage_brackets,
            "conditional_group": self._usage_conditional,
        }

    def format_help(self) -> str:
        """Generate the entire help text.

        Returns:
            str: The formatted help text.
        """
        lines = [self._format_usage(), ""]
        lines.extend(self._format_descriptions(self.group, 0))
        return "\n".join(lines)

    def _format_usage(self) -> str:
        """Generate the usage line.

        Returns:
            str: The formatted usage line.
        """
        parts = [f"Usage: {self.group.name.upper()}"]
        parts.extend(
            self._format_argument_usage(arg) for arg in self.group.arguments
        )
        return " ".join(parts)

    def _format_argument_usage(self, arg: AshParser) -> str:
        """Format usage for any argument type.

        Args:
            arg (AshParser): The argument to format usage for.

        Raises:
            ValueError: If the argument type is unknown.

        Returns:
            str: The formatted usage line.
        """
        if not isinstance(arg, ArgumentGroup):
            return self._format_simple_argument_usage(arg)

        group_type = self._get_group_type(arg)
        if not group_type:
            raise ValueError(f"Unknown argument type: {arg}")

        formatter = self.usage_strategies.get(group_type)
        if not formatter:
            raise ValueError(f"Unknown group type: {group_type!r}")

        parts = [self._format_argument_usage(child) for child in arg.arguments]
        return formatter(arg, parts)

    def _usage_none(self, group: "ArgumentGroup", parts: list[str]) -> str:
        return " ".join(parts)

    def _usage_parens(self, group: "ArgumentGroup", parts: list[str]) -> str:
        return f"({' '.join(parts)})"

    def _usage_brackets(self, group: "ArgumentGroup", parts: list[str]) -> str:
        return f"[{' '.join(parts)}]..."

    def _usage_conditional(
        self, group: "ArgumentGroup", parts: list[str]
    ) -> str:
        if not isinstance(group.subtype, ConditionalType):
            raise ValueError(f"Expected ConditionalType, got {group.subtype}")
        symbol = group.subtype.symbol
        if not parts:
            return f"<{symbol}>"
        first, *rest = parts
        ordered = [first, symbol, *rest]
        return f"<{' '.join(ordered)}>"

    def _format_simple_argument_usage(self, arg: AshParser) -> str:
        """Format usage for a simple (non-group) argument.

        Returns:
            str: The formatted usage line.
        """
        if arg.name.startswith("--"):
            name = f"[{arg.name}]"
        else:
            name = f"<{arg.name.upper()}>"

        if not isinstance(arg, Argument):
            return name

        suffix: str = "..." if arg.num_args[1] > 1 else ""

        display = (
            f"{arg.alias}, {name}{suffix}" if arg.alias else f"{name}{suffix}"
        )
        return (
            f"[{display} {arg.descriptor}]"
            if arg.descriptor
            else f"[{display}]"
        )

    def _format_descriptions(
        self, group: ArgumentGroup, indent_level: int
    ) -> list[str]:
        """Generate descriptions for all arguments recursively.

        Returns:
            list[str]: The formatted descriptions.
        """
        lines = []

        for arg in group.arguments:
            if not isinstance(arg, ArgumentGroup):
                lines.extend(
                    self._format_simple_argument_description(arg, indent_level)
                )
                continue

            if not arg.show_help:
                continue

            group_type = self._get_group_type(arg)

            lines.append(
                self._format_group_header(arg, indent_level, group_type)
            )

            lines.extend(self._format_descriptions(arg, indent_level + 1))

            if arg.arguments:
                lines.append("")

        return lines

    def _format_simple_argument_description(
        self, arg: AshParser, indent_level: int
    ) -> list[str]:
        """Format description for a simple (non-group) argument.

        Returns:
            list[str]: The formatted descriptions.
        """
        lines: list[str] = []
        indent: str = " " * (indent_level * self.indent_size)
        sig_parts = []
        if not arg.name.startswith("--"):
            sig_parts.append(arg.name.upper())

        elif arg.alias:
            sig_parts.append(arg.alias)

        sig_parts.append(f"{arg.name}")
        if isinstance(arg, Argument) and arg.descriptor:
            sig_parts.append(arg.descriptor)
            if arg.num_args[1] > 1:
                sig_parts.append("...")
            if arg.choices:
                sig_parts.append(f"{{{', '.join(map(str, arg.choices))}}}")

        signature = ", ".join(sig_parts)
        if arg.help:
            padding = max(35 - len(signature), 1)
            lines.append(f"{indent}{signature:<{padding}}{arg.help}")
        else:
            lines.append(f"{indent}{signature}")

        return lines

    def _format_group_header(
        self, group: ArgumentGroup, indent_level: int, group_type: str
    ) -> str:
        """Format header for a group.

        Args:
            group (ArgumentGroup): The group to format.
            indent_level (int): The indentation level.
            group_type (str): The type of the group.

        Raises:
            ValueError: If the group type is unknown.

        Returns:
            str: The formatted header.
        """
        indent = " " * (indent_level * self.indent_size)

        if group.name.startswith("--"):
            signature = (
                f"{group.alias, group.name}" if group.alias else group.name
            )
        else:
            signature = group.name

        if not group_type:
            raise ValueError(f"Unknown group type: {group}")

        parts = []
        for arg in group.arguments:
            if arg.name.startswith("--"):
                parts.append(f"{arg.alias, arg}" if arg.alias else arg)
            else:
                parts.append(arg.name.upper())

        formatter = self.usage_strategies.get(group_type)
        if not formatter:
            raise ValueError(f"Unknown group type: {group_type!r}")
        usage_info = formatter(group, parts)

        if usage_info:
            signature = f"{signature} {usage_info}"

        if group.help:
            padding = max(35 - len(signature), 1)
            return f"{indent}{signature:<{padding}}{group.help}"
        return f"{indent}{signature}"

    def _get_group_type(self, group: ArgumentGroup) -> str:
        """Get the type of a group.

        Args:
            group (ArgumentGroup): The group to get the type of.

        Returns:
            str: The type of the group.
        """
        return group.group_type
