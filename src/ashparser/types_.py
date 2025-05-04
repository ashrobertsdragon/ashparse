from enum import StrEnum, auto
from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import Any

__all__ = ["AshParser", "Argument", "ArgumentNamespace", "ConditionalType"]


class AshParser:
    def __init__(
        self, name: str, *, alias: str | None = None, help: str | None = None
    ) -> None:
        self.name = name
        self.alias = alias
        self.help = help


class Argument(AshParser):
    def __init__(
        self,
        name: str,
        *,
        type: type,
        alias: str | None = None,
        help: str | None = None,
        metavar: str | None = None,
        nargs: str | None = None,
        required: bool = False,
        choices: Sequence[Any] | None = None,
    ) -> None:
        super().__init__(name, alias=alias, help=help)
        self.type = type
        self.metavar = metavar
        self.nargs = nargs
        self.required = required
        self.choices = choices


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


class ConditionalType(StrEnum):
    FIRST_PRESENT_REST_REQUIRED = auto()
    FIRST_ABSENT_REST_FORBIDDEN = auto()
