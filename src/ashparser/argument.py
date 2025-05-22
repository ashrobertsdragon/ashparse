import sys
from collections.abc import Sequence
from typing import Any, Literal

from ashparser import exceptions
from ashparser.types_ import AshParser


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
