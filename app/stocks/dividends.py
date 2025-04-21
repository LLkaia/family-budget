from datetime import datetime
from decimal import Decimal

import requests
from bs4 import BeautifulSoup

from stocks.schemas import DividendPaymentInfo
from validators import validate_cash


DIVIDEND_DATA_URL = "https://www.dividenddata.co.uk/dividend-payment-date-search.py"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
}


async def get_dividend_history_by_stock_symbol(stock_symbol: str) -> list[DividendPaymentInfo]:
    """Get dividend payment history by stock symbol."""
    dividends_history = []

    response = requests.get(DIVIDEND_DATA_URL, params={"searchTerm": stock_symbol}, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    for table in soup.find_all("table", class_="table table-striped", limit=2):
        for row in table.tbody.find_all("tr"):
            amount, date = row.find_all("td")[3:]
            amount = validate_cash(Decimal(amount.string.lstrip("$")))
            date = datetime.strptime(date.string, "%d-%b-%y").date()

            dividends_history.append(DividendPaymentInfo(amount=amount, payment_date=date))

    return dividends_history
