import sys
from abc import ABC
from collections.abc import Sequence
from enum import StrEnum, auto
from typing import Any, Literal

from . import exceptions

__all__ = [
    "AshParser",
    "Argument",
    "Names",
    "ConditionalType",
]


class ConditionalType(StrEnum):
    """Enum to represent the type of a conditional argument group."""

    FIRST_PRESENT_REST_REQUIRED = auto()
    FIRST_ABSENT_REST_FORBIDDEN = auto()


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
        self.positional: bool = False

        self._post_init()
        self.validate_alias()

    def _post_init(self) -> None:
        if not self.name.startswith("--"):
            self.positional = True

    def validate_alias(self) -> None:
        """Validate the alias.

        This method checks if the alias is valid and raises an exception if not.
        It probably does not need to be called except by the constructor but
        is public in case there is a use for it by the user.

        Raises:
            exceptions.InvalidAliasError: If the alias is invalid.
        """
        if self.alias is not None:
            if (
                len(self.alias) > 2
                or (len(self.alias) == 2 and self.alias[0] != "-")
                or not self.alias[-1].isalpha()
            ):
                raise exceptions.InvalidAliasError(
                    f"Invalid alias: {self.alias}"
                )
            if len(self.alias) == 1:
                self.alias = f"-{self.alias}"


class Argument(AshParser):
    """Represents a command-line argument for the parser.

    Argument defines the properties and constraints for a single command-line
    argument, including its type, default value, allowed choices, and other
    validation rules.
    """

    def __init__(
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
        """Initialize the argument.

        An Argument is a class that represents a single command-line argument.
        It has properties such as type, default value, allowed choices, and
        other validation rules.

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
            num_args (Literal["?", "*", "+"] | int | None, optional): Number of
                arguments for the argument. Defaults to None.
            required (bool, optional): Whether the argument is required.
                Defaults to False.
            choices (Sequence[Any] | None, optional): Allowed choices for the
                argument. Defaults to None.
            min (int | None, optional): Minimum value for the argument.
                Defaults to None.
            max (int | None, optional): Maximum value for the argument.
                Defaults to None.
        """
        super().__init__(name, alias=alias, help=help)
        self.type = type
        self.default = default
        self.descriptor = descriptor
        self._num_args = num_args
        self.required = required
        self.choices = choices
        self._min = min
        self._max = max
        self.num_args: tuple[int, int] = (1, 1)

        self._post_init()

    def _post_init(self) -> None:
        """Post-initialization method to set up argument attributes.

        This method processes the `num_args`, `choices`, and `_range` attributes
        of the Argument class. It validates and converts the `num_args`
        attribute to a tuple indicating the allowed number of arguments. If
        `num_args` is a special character ("*", "+", "?"), it uses
        `_parse_num_args`. For integer `num_args`, it ensures non-negativity.

        If `choices` are provided, they are converted to a set. If both
        `choices` and a valid numeric `_range` are present, an exception is
        raised, since these options are mutually exclusive.

        Raises:
            ArgumentError: When an argument is invalid.
            ArgumentTypeError: If `num_args` is not a valid type.
            InvalidValueError: If `num_args` is negative.
            ArgumentError: If both `required` and `default` are specified.
            MutuallyExclusiveArgumentsError: If both `choices` and `_range`
                are specified.
        """
        if self._num_args is None:
            self.num_args = (1, 1)
        elif self._num_args in ("*", "+", "?"):
            self._parse_num_args(self._num_args)
        else:
            if not isinstance(self._num_args, int):
                raise exceptions.ArgumentTypeError(
                    self._num_args,
                    int,
                    f"Invalid num_args value: {self._num_args}",
                )
            if self._num_args < 0:
                raise exceptions.InvalidValueError(
                    self._num_args, "num_args", "cannot be negative"
                )
            self.num_args = (self._num_args, self._num_args)

        if self.required and self.default is not None:
            raise exceptions.ArgumentError(
                "Cannot specify both required and a default value"
            )
        if self.choices is not None:
            self.choices = set(self.choices)

        if self.type in (int, float) and (
            self._min is not None or self._max is not None
        ):
            if not self._min:
                self._min = -sys.maxsize
            if not self._max:
                self._max = sys.maxsize
            if self._min > self._max:
                raise exceptions.ArgumentError("Min must be less than max")
            if self.choices is not None:
                raise exceptions.MutuallyExclusiveArgumentsError([
                    "range",
                    "choices",
                ])
            self.choices = set(range(self._min, self._max + 1))
        if self.name.startswith("-") and not self.name.startswith("--"):
            raise exceptions.ArgumentError(
                "Argument names must start with two or zero dashes"
            )

    def _parse_num_args(self, num_args_value: str) -> None:
        """Helper to parse the `num_args` attribute."""
        num_args_map = {
            "*": (0, sys.maxsize),
            "+": (1, sys.maxsize),
            "?": (0, 1),
        }
        self.num_args = num_args_map[num_args_value]


class Names:
    """Stores and manages argument values and their types.

    Names provides attribute and item access to argument values, and enforces
    type checking for assignments.
    """

    def __init__(self):
        """Initializes a new instance of the Names class."""
        self._values: dict[str, Any] = {}
        self._types: dict[str, type] = {}

    def __getattr__(self, key: str) -> Any:
        """Returns the value of an argument.

        Args:
            key (str): The name of the argument.

        Returns:
            Any: The value of the argument.

        Raises:
            AttributeError: If the argument is not found.
        """
        try:
            return self._values[key]
        except KeyError as e:
            raise AttributeError(f"No such argument: {key}") from e

    def __getitem__(self, key: str) -> Any:
        """Returns the value of an argument.

        Args:
            key (str): The name of the argument.

        Returns:
            Any: The value of the argument.

        Raises:
            ArgumentTypeError: If the argument has the wrong type.
            KeyError: If the argument is not found.
        """  # noqa: DOC502
        # A KeyError can be raised here even if it is not done explicitly
        value = self._values[key]
        if key in self._types and not isinstance(value, self._types[key]):
            raise exceptions.ArgumentTypeError(
                value,
                self._types[key],
                f"Expected {key} to be {self._types[key].__name__}, "
                f"got {type(value).__name__}",
            )
        return value

    def __setitem__(self, key: str, value: Any):
        """Sets the value of an argument.

        Args:
            key (str): The name of the argument.
            value (Any): The value to set.

        Raises:
            ArgumentTypeError: If the argument has the wrong type.
        """
        if key in self._types and not isinstance(value, self._types[key]):
            raise exceptions.ArgumentTypeError(
                value,
                self._types[key],
                f"Expected {key} to be {self._types[key].__name__}, "
                f"got {type(value).__name__}",
            )
        self._values[key] = value

    def __repr__(self) -> str:
        """Returns a string representation of the arguments."""
        args: dict[str, dict[str, Any]] = {
            name: {"value": value, "type": typ.__name__}
            for (name, value), typ in zip(
                self._values.items(), self._types.values()
            )
        }
        return f"<Args {args}>"

    def __str__(self) -> str:
        """Returns a string representation of the arguments."""
        args: dict[str, dict[str, Any]] = {
            name: {"value": value, "type": typ.__name__}
            for (name, value), typ in zip(
                self._values.items(), self._types.values()
            )
        }
        return str(args)

    def set_type(self, name: str, typ: type) -> None:
        """Set the type of an argument."""
        self._types[name] = typ
