from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from ashparser.argument import Argument
    from ashparser.group import ArgumentGroup
    from ashparser.types_ import ConditionalType, GroupType


class AddMixin:
    """Mixin class for adding arguments and groups to an argument group."""

    def _add_argument_to(
        self,
        target: "ArgumentGroup",
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
        target.arguments.append(arg)
        if arg.default is not None:
            target._namespace[arg.name] = arg.default
        target._namespace.set_type(arg.name, arg.type)

    def _add_argument_group_to(
        self,
        target: "ArgumentGroup",
        name: str,
        help: str | None = None,
        alias: str | None = None,
        required: bool = False,
    ) -> "ArgumentGroup":
        return target.add_group(
            target._namespace,
            GroupType.ARGUMENT,
            name,
            help,
            alias=alias,
            required=required,
        )

    def _add_recurring_group_to(
        self,
        target: "ArgumentGroup",
        name: str,
        help: str | None = None,
        alias: str | None = None,
        required: bool = False,
    ) -> "ArgumentGroup":
        return target.add_group(
            target._namespace,
            GroupType.RECURRING,
            name,
            help,
            alias=alias,
            required=required,
        )

    def _add_mutually_exclusive_group_to(
        self,
        target: "ArgumentGroup",
        name: str,
        help: str | None = None,
        required: bool = False,
    ) -> "ArgumentGroup":
        return target.add_group(
            target._namespace,
            GroupType.MUTEX,
            name,
            help,
            required=required,
        )

    def _add_conditional_group_to(
        self,
        target: "ArgumentGroup",
        conditional_type: ConditionalType,
        name: str,
        help: str | None = None,
    ) -> "ArgumentGroup":
        return target.add_group(
            target._namespace,
            GroupType.CONDITIONAL,
            name,
            help,
            subtype=conditional_type,
        )
