from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .parser import Parser

__all__ = [
    "ParserError",
    "ArgumentError",
    "ArgumentTypeError",
    "MissingRequiredArgumentError",
    "UnknownArgumentError",
    "InvalidChoiceError",
    "InvalidAliasError",
    "TooManyArgumentsError",
    "TooFewArgumentsError",
]


class ParserError(Exception):
    """Base exception for all parser-related errors."""

    def __init__(self, msg: str, parser: "Parser"):
        self.msg = msg
        self.parser = parser
        super().__init__(f"{self.parser.name}: {msg}")


class ArgumentError(Exception):
    """Base exception for all argument-related errors."""

    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(msg)


class ArgumentTypeError(ArgumentError):
    """Raised when an argument value cannot be converted to the expected type."""

    def __init__(
        self, value: Any, expected_type: type, msg: str | None = None
    ):
        self.value = value
        self.expected_type = expected_type

        default_msg = f"Cannot convert '{value}' to {expected_type.__name__}"
        self.msg = msg or default_msg

        super().__init__(self.msg)


class MissingRequiredArgumentError(ArgumentError):
    """Raised when a required argument is not provided."""

    def __init__(self, arg_name: str):
        self.arg_name = arg_name
        msg = f"Required argument '{arg_name}' is missing"
        super().__init__(msg)


class UnknownArgumentError(ArgumentError):
    """Raised when an unknown argument is encountered."""

    def __init__(self, arg_name: str):
        self.arg_name = arg_name
        msg = f"Unknown argument '{arg_name}'"
        super().__init__(msg)


class InvalidChoiceError(ArgumentError):
    """Raised when an argument value is not among the allowed choices."""

    def __init__(self, arg_name: str, value: Any, choices: list[Any]):
        self.value = value
        self.choices = choices
        self.arg_name = arg_name

        choices_str = ", ".join(repr(c) for c in choices)
        msg = f"Invalid choice: '{value}' for '{arg_name}'. (choose from {choices_str})"
        super().__init__(msg)


class MutuallyExclusiveArgumentsError(ArgumentError):
    """Raised when mutually exclusive arguments are used together."""

    def __init__(self, arg_names: list[str]):
        self.arg_names = arg_names
        msg = f"Arguments {', '.join(repr(a) for a in arg_names)} are mutually exclusive"
        super().__init__(msg)


class InvalidValueError(ArgumentError):
    """Raised when an argument value is invalid for reasons other than type."""

    def __init__(
        self,
        value: Any,
        arg_name: str | None,
        reason: str | None = None,
    ):
        self.value = value
        self.arg_name = arg_name
        self.reason = reason

        reason_str = f": {reason}" if reason else ""
        msg = f"Invalid value '{value}' for '{arg_name}'{reason_str}"

        super().__init__(msg)


class InvalidAliasError(ArgumentError):
    """Raised when an argument alias is invalid."""

    def __init__(self, alias: str, reason: str | None = None):
        self.alias = alias
        self.reason = reason
        reason_str = f": {reason}" if reason else ""
        msg = f"Invalid alias '{alias}'{reason_str}"
        super().__init__(msg)


class TooFewArgumentsError(ArgumentError):
    """Raised when too few arguments are provided for a parameter."""

    def __init__(self, arg_name: str, min_expected: int, received: int):
        self.arg_name = arg_name
        self.min_expected = min_expected
        self.received = received
        msg = f"Too few arguments for '{arg_name}': expected at least {min_expected}, got {received}"
        super().__init__(msg)


class TooManyArgumentsError(ArgumentError):
    """Raised when too many arguments are provided for a parameter."""

    def __init__(self, arg_name: str, max_expected: int, received: int):
        self.arg_name = arg_name
        self.max_expected = max_expected
        self.received = received
        msg = f"Too many arguments for '{arg_name}': expected at most {max_expected}, got {received}"
        super().__init__(msg)
