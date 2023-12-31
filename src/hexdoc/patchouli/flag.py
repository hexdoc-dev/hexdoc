from typing import Any

from pydantic import model_validator

from hexdoc.model import HexdocModel


class Flag(HexdocModel):
    name: str
    negated: bool = False

    @model_validator(mode="before")
    @classmethod
    def parse_flag(cls, data: Any) -> Any:
        if isinstance(data, str):
            assert (
                "," not in data
            )  # not sure if there are other invalid characters or not
            if data.startswith("!"):
                return {"name": data[1:], "negated": True}
            return {"name": data}

        return data

    def css_classname(self) -> str:
        base = "flag-" + self.name.replace(":", "-")
        if self.negated:
            return "not-" + base
        return base


class FlagExpression(HexdocModel):
    flags: list[Flag]
    conjuctive: bool = True

    @model_validator(mode="before")
    @classmethod
    def parse_flags(cls, data: Any) -> Any:
        if isinstance(data, str):
            if data.startswith("|") or data.startswith("&"):  # must be a list
                return {
                    "flags": data[1:].split(","),
                    "conjuctive": data.startswith("&"),
                }
            return {"flags": [data]}

        return data

    def css_classnames(self) -> str:
        flagclasses = " ".join(map(lambda f: f.css_classname(), self.flags))
        if self.conjuctive:
            return "flagall " + flagclasses
        return "flagany " + flagclasses
