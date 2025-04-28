import httpx

from core.config import get_settings
from ollama.prompts import stock_positions_summary
from stocks.schemas import StockPositionPublic


config = get_settings()

HOST = config.ollama_host
TIMEOUT = 180
MODEL = "mistral"
IS_STREAM = False


async def get_stock_positions_summary(stock_positions: list[StockPositionPublic]) -> str:
    """Generate Stock Positions Summary."""
    prompt = stock_positions_summary.format(stock_positions=stock_positions)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{HOST}/api/generate", timeout=TIMEOUT, json={"model": MODEL, "stream": IS_STREAM, "prompt": prompt}
            )
        except httpx.ReadTimeout:
            return f"AI failed to generate response. Timeout {TIMEOUT}s was reached."

    response = response.json()
    try:
        return str(response["response"])
    except KeyError:
        return f"AI failed to generate response. Received: {response}."
