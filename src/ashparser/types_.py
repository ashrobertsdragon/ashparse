import sys
from abc import ABC
from collections.abc import Iterator, Sequence, KeysView, ItemsView, ValuesView
from enum import StrEnum, auto
from typing import Any, Generic, Literal, TypeVar

from . import exceptions

__all__ = [
    "AshParser",
    "Argument",
    "Names",
    "ConditionalType",
    "IndexedDict",
]


class ConditionalType(StrEnum):
    FIRST_PRESENT_REST_REQUIRED = auto()
    FIRST_ABSENT_REST_FORBIDDEN = auto()


class AshParser(ABC):
    def __init__(
        self,
        name: str,
        *,
        alias: str | None = None,
        help: str | None = None,
        required: bool = False,
    ) -> None:
        self.name = name
        self.alias = alias
        self.help = help
        self.type = type(self)
        self.required = False

        self.validate_alias()

    def validate_alias(self) -> None:
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
    """
    Represents a command-line argument for the parser.

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
        super().__init__(name, alias=alias, help=help)
        self.type = type
        self.default = default
        self.descriptor = descriptor
        self._num_args = num_args
        self.required = required
        self.choices = choices
        self._min = min
        self._max = max
        self.num_args: tuple[int, int | float] = (1, 1)

        self._post_init()

    def _post_init(self) -> None:
        """
        Post-initialization method to set up argument attributes.

        This method processes the `num_args`, `choices`, and `_range` attributes
        of the Argument class. It validates and converts the `num_args` attribute
        to a tuple indicating the allowed number of arguments. If `num_args` is
        a special character ("*", "+", "?"), it uses `_parse_num_args`. For
        integer `num_args`, it ensures non-negativity.

        If `choices` are provided, they are converted to a set. If both
        `choices` and a valid numeric `_range` are present, an exception is
        raised, since these options are mutually exclusive.
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
                raise exceptions.MutuallyExclusiveArgumentsError(
                    ["range", "choices"]
                )
            self.choices = set(range(self._min, self._max + 1))

    def _parse_num_args(self, num_args_value: str) -> None:
        """Helper to parse the `num_args` attribute."""
        num_args_map = {
            "*": (0, float("inf")),
            "+": (1, float("inf")),
            "?": (0, 1),
        }
        self._num_args = num_args_map[num_args_value]


class Names:
    """
    Stores and manages argument values and their types.

    Names provides attribute and item access to argument values, and enforces
    type checking for assignments.
    """

    def __init__(self):
        self.values: dict[str, Any] = {}
        self._types: dict[str, type] = {}

    def __getattr__(self, key: str) -> Any:
        try:
            return self.values[key]
        except KeyError as e:
            raise AttributeError(f"No such argument: {key}") from e

    def __getitem__(self, key: str) -> Any:
        value = self.values[key]
        if key in self._types and not isinstance(value, self._types[key]):
            raise exceptions.ArgumentTypeError(
                value,
                self._types[key],
                f"Expected {key} to be {self._types[key].__name__}, got {type(value).__name__}",
            )
        return value

    def __setitem__(self, key: str, value: Any):
        if key in self._types and not isinstance(value, self._types[key]):
            raise exceptions.ArgumentTypeError(
                value,
                self._types[key],
                f"Expected {key} to be {self._types[key].__name__}, got {type(value).__name__}",
            )
        self.values[key] = value

    def __repr__(self) -> str:
        args: dict[str, dict[str, Any]] = {
            name: {"value": value, "type": typ.__name__}
            for (name, value), typ in zip(
                self._values.items(), self._types.values()
            )
        }
        return f"<Args {args}>"

    def set_type(self, name: str, typ: type):
        self._types[name] = typ


K = TypeVar("K")
V = TypeVar("V")


class IndexedDict(Generic[K, V]):
    """
    A dictionary that preserves insertion order and allows index-based access.

    IndexedDict provides both key-based and index-based operations, making it
    useful for scenarios where order matters and fast lookups are required.
    """

    def __init__(self) -> None:
        self._index: list[K] = []
        self._dict: dict[K, V] = {}

    def __setitem__(self, key: K, value: V) -> None:
        if key not in self._dict:
            self._index.append(key)
        self._dict[key] = value

    def __getitem__(self, key: K) -> V:
        return self._dict[key]

    def __delitem__(self, key: K) -> None:
        self._index.remove(key)
        del self._dict[key]

    def __len__(self) -> int:
        return len(self._index)

    def __iter__(self) -> Iterator[V]:
        for key in self._index:
            yield self._dict[key]

    def __repr__(self) -> str:
        return f"<IndexedDict {self._dict}>"

    def __str__(self) -> str:
        return str(self._dict)

    def __contains__(self, key: K) -> bool:
        return key in self._dict

    def __bool__(self) -> bool:
        return bool(self._dict)

    def __reversed__(self) -> Iterator[K]:
        return reversed(self._index)

    def enumerated(self) -> Iterator[tuple[int, K, V]]:
        for key in self._index:
            yield self.position(key), key, self._dict[key]

    def items(self) -> ItemsView[K, V]:
        return self._dict.items()

    def values(self) -> ValuesView[V]:
        return self._dict.values()

    def keys(self) -> KeysView[K]:
        return self._dict.keys()

    def get(self, key: K, default=None) -> V | None:
        return self._dict.get(key, default)

    def position(self, key: K) -> int:
        return self._index.index(key)

    def get_from_index(self, index: int) -> V:
        return self._dict[self._index[index]]

    def pop(self, key: K, default: Any = None) -> Any:
        if key in self._index:
            self._index.remove(key)
        return self._dict.pop(key, default)

    def pop_from_index(self, index: int) -> V:
        return self._dict.pop(self._index[index])

    def clear(self) -> None:
        self._index.clear()
        self._dict.clear()
