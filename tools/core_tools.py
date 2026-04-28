import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def register_core_tools(mcp: Any, *, flights_dir: str) -> None:
    @mcp.tool()
    def simulate_error(
        message: str = "Simulated tool error for testing.",
        error_code: str = "SIMULATED_ERROR",
        as_exception: bool = False,
    ) -> Dict[str, Any]:
        """
        Simulate a tool failure for client or agent error-handling tests.

        By default returns the same structured shape used elsewhere in this server
        (a dict with an ``error`` field). When ``as_exception`` is true, raises
        ``RuntimeError`` so the host can exercise MCP tool error propagation.

        Args:
            message: Human-readable error description.
            error_code: Stable machine-readable code for assertions or routing.
            as_exception: If true, raise instead of returning a payload.

        Returns:
            A dict with ``error`` and ``error_code`` when ``as_exception`` is false.
        """
        if as_exception:
            raise RuntimeError(message)
        return {"error": message, "error_code": error_code}

    @mcp.tool()
    def test_tool_failure_now() -> Any:
        """
        Easiest MCP error test: no parameters, always raises ``RuntimeError``.

        Call this when the user asks to **test tool errors**, **simulate a crash**,
        **force an exception**, or uses short phrases such as: "simula erro",
        "testa falha da tool", "força exceção", "dry run de erro", "quebra de propósito".

        Raises:
            RuntimeError: Fixed airline-style message for assertions in the client.
        """
        raise RuntimeError(
            "Simulated failure: reservations API unavailable (retry in a few minutes)."
        )

    @mcp.tool()
    async def search_hotels(
        city: str,
        check_in: str,
        check_out: str,
        guests: int,
    ) -> Dict[str, Any]:
        """
        Simulates a hotel search API call returning JSON after 6 seconds.

        Args:
            city: Destination city name.
            check_in: Check-in date (YYYY-MM-DD).
            check_out: Check-out date (YYYY-MM-DD).
            guests: Number of guests.

        Returns:
            A JSON-like dict payload similar to a real hotel search API response.
        """
        await asyncio.sleep(6)

        now = datetime.now()
        request_id = f"hotels_{now.strftime('%Y%m%d_%H%M%S')}"

        payload: Dict[str, Any] = {
            "request_id": request_id,
            "status": "OK",
            "search_parameters": {
                "city": city,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests,
            },
            "currency": "USD",
            "hotels": [
                {
                    "hotel_id": "HTL-1001",
                    "name": "Downtown City Hotel",
                    "stars": 4,
                    "review_score": 8.7,
                    "address": f"Central District, {city}",
                    "nightly_rate": 152.35,
                    "total_price": 304.70,
                    "taxes_and_fees": 41.20,
                    "refundable": True,
                    "amenities": ["wifi", "breakfast_included", "gym"],
                },
                {
                    "hotel_id": "HTL-2044",
                    "name": "Riverside Boutique Stay",
                    "stars": 5,
                    "review_score": 9.1,
                    "address": f"Riverside, {city}",
                    "nightly_rate": 229.99,
                    "total_price": 459.98,
                    "taxes_and_fees": 62.80,
                    "refundable": False,
                    "amenities": ["wifi", "pool", "spa", "room_service"],
                },
                {
                    "hotel_id": "HTL-3098",
                    "name": "Airport Express Lodge",
                    "stars": 3,
                    "review_score": 8.0,
                    "address": f"Near Airport, {city}",
                    "nightly_rate": 96.10,
                    "total_price": 192.20,
                    "taxes_and_fees": 26.10,
                    "refundable": True,
                    "amenities": ["wifi", "shuttle", "parking"],
                },
            ],
            "meta": {
                "provider": "mock",
                "response_time_seconds": 6,
                "generated_at": now.isoformat(),
            },
        }

        return payload

    @mcp.tool()
    def get_flight_details(search_id: str) -> str:
        """
        Get detailed information about a specific flight search.

        Args:
            search_id: The search ID returned from search_flights

        Returns:
            JSON string with detailed flight information
        """
        file_path = os.path.join(flights_dir, f"{search_id}.json")

        if not os.path.exists(file_path):
            return f"No flight search found with ID: {search_id}"

        try:
            with open(file_path, "r") as f:
                flight_data = json.load(f)
            return json.dumps(flight_data, indent=2)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return f"Error reading flight data for {search_id}: {str(e)}"

    @mcp.tool()
    def filter_flights_by_price(
        search_id: str,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
    ) -> str:
        """
        Filter flights from a search by price range.

        Args:
            search_id: The search ID returned from search_flights
            max_price: Maximum price filter (optional)
            min_price: Minimum price filter (optional)

        Returns:
            JSON string with filtered flight results
        """
        file_path = os.path.join(flights_dir, f"{search_id}.json")

        if not os.path.exists(file_path):
            return f"No flight search found with ID: {search_id}"

        try:
            with open(file_path, "r") as f:
                flight_data = json.load(f)

            def price_filter(flight):
                price = flight.get("price", 0)
                if min_price is not None and price < min_price:
                    return False
                if max_price is not None and price > max_price:
                    return False
                return True

            filtered_best = [
                f for f in flight_data.get("best_flights", []) if price_filter(f)
            ]
            filtered_other = [
                f for f in flight_data.get("other_flights", []) if price_filter(f)
            ]

            result = {
                "search_id": search_id,
                "filters_applied": {"min_price": min_price, "max_price": max_price},
                "filtered_best_flights": filtered_best,
                "filtered_other_flights": filtered_other,
                "total_filtered": len(filtered_best) + len(filtered_other),
            }

            return json.dumps(result, indent=2)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            return f"Error processing flight data for {search_id}: {str(e)}"

    @mcp.tool()
    def filter_flights_by_airline(search_id: str, airlines: List[str]) -> str:
        """
        Filter flights from a search by specific airlines.

        Args:
            search_id: The search ID returned from search_flights
            airlines: List of airline names or codes to filter by

        Returns:
            JSON string with filtered flight results
        """
        file_path = os.path.join(flights_dir, f"{search_id}.json")

        if not os.path.exists(file_path):
            return f"No flight search found with ID: {search_id}"

        try:
            with open(file_path, "r") as f:
                flight_data = json.load(f)

            def airline_filter(flight):
                flight_airlines = set()
                for leg in flight.get("flights", []):
                    airline = leg.get("airline", "").lower()
                    flight_airlines.add(airline)

                return any(airline.lower() in flight_airlines for airline in airlines)

            filtered_best = [
                f for f in flight_data.get("best_flights", []) if airline_filter(f)
            ]
            filtered_other = [
                f for f in flight_data.get("other_flights", []) if airline_filter(f)
            ]

            result = {
                "search_id": search_id,
                "filters_applied": {"airlines": airlines},
                "filtered_best_flights": filtered_best,
                "filtered_other_flights": filtered_other,
                "total_filtered": len(filtered_best) + len(filtered_other),
            }

            return json.dumps(result, indent=2)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            return f"Error processing flight data for {search_id}: {str(e)}"

