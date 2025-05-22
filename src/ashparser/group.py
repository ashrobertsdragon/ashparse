from typing import TYPE_CHECKING, Any, Literal

from ashparser.mixins import AddMixin
from ashparser.types_ import AshParser, ConditionalType, GroupType

if TYPE_CHECKING:
    from collections.abc import Sequence
    from enum import Enum

    from ashparser.argument import Argument
    from ashparser.names import Names


class ArgumentGroup(AshParser, AddMixin):
    """The argument group class.

    This class represents a group of arguments that can be used together. It is
    not intended to be instantiated directly, but rather by the Parser class and
    then by parent argument groups.

    Attributes:
        arguments (list[AshParser]): List of arguments for the argument group.

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

    Raises:
        ParserError: If the argument group is not valid.
    """

    def __init__(
        self,
        namespace: Names,
        name: str,
        alias: str | None = None,
        help: str | None = None,  # noqa: A002
        required: bool = False,
        group_type: GroupType = GroupType.ARGUMENT,
        subtype: Enum | None = None,
        show_help: bool = True,
    ) -> None:
        """Initialize the argument group.

        Args:
            name (str): Name of the argument group.
            alias (str | None, optional): Alias for the argument group.
                Defaults to None.
            help (str | None, optional): Help text for the argument group.
                Defaults to None.
            required (bool, optional): Whether the argument group is required.
                Defaults to False.
            group_type (GroupType, optional): Type of the argument group.
                Defaults to GroupType.ARGUMENT. (Note: The root group is always
                an argument group.)
            subtype (Enum | None, optional): Subtype of the argument group.
                Defaults to None.
            show_help (bool, optional): Whether to pass the help for the
            argument group up to the parent. Defaults to True.
        """
        super().__init__(name, alias=alias, help=help, required=required)

        self._namespace = namespace

        self.group_type = group_type
        self.subtype = subtype
        self.show_help = show_help

        self.arguments: list[AshParser] = []

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

        See the Parser class for more details.
        """
        self._add_argument_to(
            self,
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

    def add_group(
        self,
        namespace: Names,
        group_type: GroupType,
        name: str,
        help: str | None = None,
        alias: str | None = None,
        required: bool = False,
        subtype: Enum | None = None,
    ) -> "ArgumentGroup":
        """Add an nested argument group to the argument group as an argument.

        The child group is returned to add arguments to.

        Args:
            namespace (Names): The namespace to add arguments to.
            group_type (GroupType): Type of the child group.
            name (str): Name of the child group.
            help (str | None, optional): Help text for the child group.
                Defaults to None.
            alias (str | None, optional): Alias for the child group.
                Defaults to None.
            required (bool, optional): Whether the child group is required.
                Defaults to False.
            subtype (Enum | None, optional): Subtype of the child group.
                Defaults to None.

        Returns:
            ArgumentGroup: The child group.
        """
        group = ArgumentGroup(
            namespace,
            name,
            alias=alias,
            help=help,
            required=required,
            group_type=group_type,
            subtype=subtype,
        )
        self.arguments.append(group)

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
            self._namespace.set_type(group.name, self._set_type(arg_types))
        return group

    @staticmethod
    def _set_type(arg_types: list[type]) -> type[tuple]:
        return tuple[tuple(arg_types)]

    def add_argument_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> "ArgumentGroup":
        """Add an argument group to the parser.

        See the Parser class for more details.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance.
        """
        return self._add_argument_group_to(self, name, required=required)

    def add_recurring_group(
        self,
        name: str,
        help: str,
        alias: str | None = None,
        required: bool = False,
    ) -> "ArgumentGroup":
        """Add a recurring group to the parser.

        See the Parser class for more details.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the recurring group.
        """
        return self._add_recurring_group_to(self, name, help, alias, required)

    def add_mutually_exclusive_group(
        self, name: str, help: str | None = None, required: bool = False
    ) -> "ArgumentGroup":
        """Add a mutually exclusive group to the parser.

        See the Parser class for more details.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the mutually
                exclusive group.
        """
        return self._add_mutually_exclusive_group_to(
            self, name, help, required=required
        )

    def add_conditional_argument_group(
        self,
        name: str,
        help: str,
        conditional_type: ConditionalType,
    ) -> "ArgumentGroup":
        """Add a conditional argument group to the parser.

        See the Parser class for more details.

        Returns:
            ArgumentGroup: A new ArgumentGroup instance for the conditional
                argument group.
        """
        return self._add_conditional_group_to(
            self, conditional_type, name, help
        )
