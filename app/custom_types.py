import re
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema


class StockSymbol(str):
    """Stock Symbol Data Type."""

    _stock_symbol_pattern = r"^[A-Z0-9]{1,6}([.-][A-Z0-9]{1,4})?$"

    @classmethod
    def _validate(cls, v: str) -> "StockSymbol":
        """Validate stock symbol."""
        if not isinstance(v, str):
            raise PydanticCustomError("stock_symbol_type", "Value must be a string")

        v = v.strip().upper()
        if not 1 <= len(v) <= 6:
            raise PydanticCustomError("stock_symbol_length", "Value must be between 1 and 6 characters")

        if not re.fullmatch(cls._stock_symbol_pattern, v):
            raise PydanticCustomError("stock_symbol_pattern", f"Value must follow pattern: {cls._stock_symbol_pattern}")

        return cls(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Return a schema that calls a validator function before validating."""
        return core_schema.no_info_before_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetCoreSchemaHandler
    ) -> dict[str, Any]:
        """Modify the generated json schema."""
        json_schema = handler(schema)
        json_schema.update(
            {
                "title": "Stock Symbol",
                "description": "Valid Stock Symbol (1-6 uppercase letters and numbers, could contain '.' or '-')",
                "examples": ["AAPL", "MSFT", "BRK.B", "BF-B", "9984.T"],
                "pattern": cls._stock_symbol_pattern,
            }
        )
        return dict(json_schema)
