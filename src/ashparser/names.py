from typing import Any

from ashparser import exceptions


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
