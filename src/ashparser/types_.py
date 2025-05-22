from abc import ABC
from enum import StrEnum, auto

from ashparser import exceptions

__all__ = [
    "AshParser",
    "ConditionalType",
    "GroupType",
]


class ConditionalType(StrEnum):
    """Enum to represent the type of a conditional argument group."""

    FIRST_PRESENT_REST_REQUIRED = auto()
    FIRST_ABSENT_REST_FORBIDDEN = auto()

    @property
    def symbol(self) -> str:
        """Get the symbol for the conditional type."""
        return {
            ConditionalType.FIRST_PRESENT_REST_REQUIRED: "&",
            ConditionalType.FIRST_ABSENT_REST_FORBIDDEN: "&|",
        }[self]


class GroupType(StrEnum):
    """Enum to represent the type of a group."""

    ARGUMENT = auto()
    MUTEX = auto()
    RECURRING = auto()
    CONDITIONAL = auto()


class AshParser(ABC):
    """Base class for Argument and Parser."""

    def __init__(
        self,
        name: str,
        *,
        alias: str | None = None,
        help: str | None = None,
        required: bool = False,
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
        """
        self.name = name
        self.alias = alias
        self.help = help
        self.type = type(self)
        self.required = required

        self.validate_alias()

    def validate_alias(self) -> None:
        """Validate the alias.

        This method checks if the alias is valid and raises an exception if not.
        It probably does not need to be called except by the constructor but
        is public in case there is a use for it by the user.

        Raises:
            exceptions.InvalidAliasError: If the alias is invalid.
        """
        if self.alias is not None:
            if not self.name.startswith("-"):
                raise exceptions.InvalidAliasError(
                    self.alias, "positional arguments cannot have aliases"
                )
            if (
                len(self.alias) > 2
                or (len(self.alias) == 2 and self.alias[0] != "-")
                or not self.alias[-1].isalpha()
            ):
                raise exceptions.InvalidAliasError(
                    self.alias, "must be a single character"
                )
            if len(self.alias) == 1:
                self.alias = f"-{self.alias}"
