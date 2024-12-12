import os
import pytz
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Union, Literal, Optional
from urllib.parse import urlencode
import requests

# Type alias for a single stock result after transformation
TransformedStockResult = Dict[str, Union[float, int, Optional[datetime]]]

# Type alias for the response JSON structure from Polygon API
PolygonAPIResponse = Dict[str, Union[str, int, List[Dict[str, Union[float, int]]]]]

# Static type for the API key
POLYGON_API_KEY: Optional[str] = os.getenv("POLYGON_API_KEY")


def transform_polygon_result(result: Dict[str, Union[float, int]]) -> TransformedStockResult:
    """
    Transform a raw Polygon API result dictionary into a structured format.

    Args:
        result (Dict[str, Union[float, int]]): The raw result from Polygon API.

    Returns:
        TransformedStockResult: The transformed stock data with additional fields.
    """
    unix_timestamp: float = result.get("t", 0) / 1000.0
    utc_timestamp: datetime = datetime.fromtimestamp(unix_timestamp, tz=pytz.timezone("UTC"))
    return {
        "open_price": result["o"],
        "close_price": result["c"],
        "high_price": result["h"],
        "low_price": result["l"],
        "number_of_trades": result["n"],
        "volume": result["v"],
        "volume_weighted_average": result["vw"],
        "raw_timestamp": result.get("t"),
        "time": utc_timestamp,
    }


@dataclass
class PolygonAPIClient:
    """
    A client for interacting with the Polygon API to fetch stock data.
    """
    ticker: str = "AAPL"
    multiplier: int = 5
    timespan: str = "minute"
    from_date: str = "2024-01-09"
    to_date: str = "2024-01-09"
    api_key: str = ""
    adjusted: bool = True
    sort: Literal["asc", "desc"] = "asc"

    def get_api_key(self) -> Optional[str]:
        """
        Retrieve the API key for Polygon API.

        Returns:
            Optional[str]: The API key to use for requests.
        """
        return self.api_key or POLYGON_API_KEY

    def get_headers(self) -> Dict[str, str]:
        """
        Generate headers for the API request.

        Returns:
            Dict[str, str]: The headers with authorization information.
        """
        api_key = self.get_api_key()
        return {
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }

    def get_params(self) -> Dict[str, Union[bool, int, str]]:
        """
        Generate the query parameters for the API request.

        Returns:
            Dict[str, Union[bool, int, str]]: Query parameters.
        """
        return {
            "adjusted": self.adjusted,
            "sort": self.sort,
            "limit": 50_000,
        }

    def generate_url(self, pass_auth: bool = False) -> str:
        """
        Construct the complete API URL with parameters.

        Args:
            pass_auth (bool, optional): Whether to include API key in the URL. Defaults to False.

        Returns:
            str: The fully constructed API URL.
        """
        ticker: str = self.ticker.upper()
        path: str = f"/v2/aggs/ticker/{ticker}/range/{self.multiplier}/{self.timespan}/{self.from_date}/{self.to_date}"
        url: str = f"https://api.polygon.io{path}"
        params: Dict[str, Union[bool, int, str]] = self.get_params()
        encoded_params: str = urlencode(params)
        url = f"{url}?{encoded_params}"
        if pass_auth:
            api_key = self.get_api_key()
            if api_key:
                url += f"&api_key={api_key}"
        return url

    def fetch_data(self) -> PolygonAPIResponse:
        """
        Fetch raw data from the Polygon API.

        Returns:
            PolygonAPIResponse: The raw response from the API.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        headers: Dict[str, str] = self.get_headers()
        url: str = self.generate_url()
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()

    def get_stock_data(self) -> List[TransformedStockResult]:
        """
        Fetch and transform stock data.

        Returns:
            List[TransformedStockResult]: A list of transformed stock data dictionaries.

        Raises:
            Exception: If no results are found for the ticker.
        """
        data: PolygonAPIResponse = self.fetch_data()
        results: Optional[List[Dict[str, Union[float, int]]]] = data.get("results")  # type: ignore
        if results is None:
            raise Exception(f"Ticker {self.ticker} has no results")
        return [transform_polygon_result(result) for result in results]

    def get_forex_data(self) -> List[TransformedStockResult]:
        """
        Fetch and transform stock data.

        Returns:
            List[TransformedStockResult]: A list of transformed stock data dictionaries.

        Raises:
            Exception: If no results are found for the ticker.
        """
        data: PolygonAPIResponse = self.fetch_data()
        results: Optional[List[Dict[str, Union[float, int]]]] = data.get("results")  # type: ignore
        if results is None:
            raise Exception(f"Ticker {self.ticker} has no results")
        return [transform_polygon_result(result) for result in results]

    def get_crypto_data(self) -> List[TransformedStockResult]:
        """
        Fetch and transform stock data.

        Returns:
            List[TransformedStockResult]: A list of transformed stock data dictionaries.

        Raises:
            Exception: If no results are found for the ticker.
        """
        data: PolygonAPIResponse = self.fetch_data()
        results: Optional[List[Dict[str, Union[float, int]]]] = data.get("results")  # type: ignore
        if results is None:
            raise Exception(f"Ticker {self.ticker} has no results")
        return [transform_polygon_result(result) for result in results]
