from ashparser.types_ import AshParser, Argument, ConditionalType


class Parser(AshParser):
    def __init__(
        self,
        name: str,
        alias: str | None = None,
        help: str = "",
        show_help: bool = True,
    ) -> None:
        super().__init__(name, alias=alias, help=help)
        self.show_help = show_help

        self._arguments: list[Argument] = []
        self._recurring_groups: list["Parser"] = []
        self._argument_groups: list["Parser"] = []
        self._mutually_exclusive_groups: list["Parser"] = []
        self._conditional_groups: list[tuple[ConditionalType, "Parser"]] = []

        self._groups = {
            "argument_group": self._argument_groups,
            "recurring_group": self._recurring_groups,
            "mutually_exclusive_group": self._mutually_exclusive_groups,
            "conditional_group": self._conditional_groups,
        }
