from enum import StrEnum, auto
from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import Any, Literal

__all__ = ["AshParser", "Argument", "ArgumentNamespace", "ConditionalType"]


class ConditionalType(StrEnum):
    FIRST_PRESENT_REST_REQUIRED = auto()
    FIRST_ABSENT_REST_FORBIDDEN = auto()


class AshParser:
    def __init__(
        self, name: str, *, alias: str | None = None, help: str | None = None
    ) -> None:
        self.name = name
        self.alias = alias
        self.help = help
        self.validate_alias()

    def validate_alias(self) -> None:
        if self.alias is not None and (
            len(self.alias) > 2
            or (len(self.alias) > 1 and self.alias[0] != "-")
            or not self.alias[-1].isalpha()
        ):
            raise ValueError(f"Invalid alias: {self.alias}")


class Argument(AshParser):
    def __init__(
        self,
        name: str,
        *,
        type: type,
        alias: str | None = None,
        help: str | None = None,
        metavar: str | None = None,
        nargs: Literal["?", "*", "+"] | int | None = None,
        required: bool = False,
        choices: Sequence[Any] | None = None,
        min: int | None = None,
        max: int | None = None,
    ) -> None:
        super().__init__(name, alias=alias, help=help)
        self.type = type
        self.metavar = metavar
        self.nargs = nargs
        self.required = required
        self.choices = choices
        self._range = (min, max)
        self._nargs: tuple[int, int | float] = (1, 1)

        self._post_init()

    def _post_init(self) -> None:
        """
        Post-initialization method to set up argument attributes.

        This method processes the `nargs`, `choices`, and `_range` attributes
        of the Argument class. It validates and converts the `nargs` attribute
        to a tuple indicating the allowed number of arguments. If `nargs` is
        a special character ("*", "+", "?"), it uses `_parse_nargs`. For
        integer `nargs`, it ensures non-negativity.

        If `choices` are provided, they are converted to a set. If both
        `choices` and a valid numeric `_range` are present, an exception is
        raised, since these options are mutually exclusive.
        """

        if self.nargs is None:
            self._nargs = (1, 1)
        elif self.nargs in ("*", "+", "?"):
            self._parse_nargs(self.nargs)
        else:
            try:
                narg = int(self.nargs)
                if narg < 0:
                    raise ValueError("nargs cannot be negative")
                self._nargs = (narg, narg)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid nargs value: {self.nargs}") from e

        if self.choices is not None:
            self.choices = set(self.choices)

        if (
            self.type in (int, float)
            and self._range[0] is not None
            and self._range[1] is not None
            and self._range[0] < self._range[1]
        ):
            if self.choices is not None:
                raise ValueError("Cannot specify both range and choices")
            self.choices = set(range(self._range[0], self._range[1] + 1))

    def _parse_nargs(self, nargs_value: str) -> None:
        """Helper to parse the `nargs` attribute."""
        nargs_map = {
            "*": (0, float("inf")),
            "+": (1, float("inf")),
            "?": (0, 1),
        }
        self._nargs = nargs_map[nargs_value]


@dataclass
class ArgumentNamespace:
    values: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, key: str) -> Any:
        try:
            return self.values[key]
        except KeyError:
            raise AttributeError(f"No such argument: {key}")

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def __repr__(self) -> str:
        return f"<Args {self.values}>"
