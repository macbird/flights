import json
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote

import requests


def register_external_tools(
    mcp: Any,
    *,
    get_serpapi_key: Callable[[], str],
    normalize_location_id: Callable[[str], str],
    flights_dir: str,
) -> None:
    @mcp.tool()
    def lock_fare_before_booking(
        trip_summary: str = "",
    ) -> Any:
        """
        Request a time-limited **fare hold** (price lock) with the airline/pricing partner.

        Use when the traveler wants to **hold**, **lock**, or **freeze** a quoted fare
        before paying—typical phrases: "segura esse preço", "trava a tarifa",
        "garante esse valor", "hold the fare", "lock this price", "fare lock for 24h".

        This demo integration **always** raises ``requests.HTTPError`` with HTTP **503**
        and a JSON body, simulating partner maintenance or overload during fare-hold
        confirmation—handy for testing MCP error handling in a realistic travel workflow.

        Args:
            trip_summary: Short free-text label for logs (e.g. ``GRU-LIS June``);
                may be empty if the itinerary is only implied in the chat.

        Raises:
            requests.HTTPError: Simulated 503 from the fare-hold partner API.
        """
        label = trip_summary.strip() or "the itinerary under discussion"
        url = (
            "https://fare-holds.partner.example/v1/holds?"
            f"trip={quote(label, safe='')}"
        )
        body = (
            b'{"error":"SERVICE_UNAVAILABLE","http_status":503,'
            b'"message":"Fare-hold cluster temporarily unavailable",'
            b'"retry_after_seconds":45}'
        )
        response = requests.Response()
        response.status_code = 503
        response.reason = "Service Unavailable"
        response.url = url
        response.encoding = "utf-8"
        response._content = body
        raise requests.HTTPError(
            f"503 Server Error for url: {url}",
            response=response,
        )

    @mcp.tool()
    def fetch_partner_inventory_snapshot(
        airline_iata: str,
        origin_iata: str,
        destination_iata: str,
        flight_date: str,
    ) -> Dict[str, Any]:
        """
        Demo partner call: query airline inventory via a GDS-style HTTP API.

        **Always raises** ``requests.HTTPError`` with HTTP 503 and a JSON body,
        simulating maintenance or overload on the partner cluster. Use this to test
        how your agent handles **tool exceptions** (not a returned ``{"error": ...}`` dict).

        Args:
            airline_iata: Carrier IATA code (e.g. ``LA``, ``G3``, ``AD``).
            origin_iata: Origin airport IATA (e.g. ``GRU``).
            destination_iata: Destination airport IATA (e.g. ``CGH``).
            flight_date: Local date ``YYYY-MM-DD`` for the operating day.

        Returns:
            Never returns in this demo build; always raises.

        Raises:
            requests.HTTPError: Simulated 503 from the partner reservations API.
        """
        dep = normalize_location_id(origin_iata)
        arr = normalize_location_id(destination_iata)
        carrier = normalize_location_id(airline_iata)
        url = (
            f"https://inventory.partner.example/v1/carriers/{carrier}/routes/"
            f"{dep}-{arr}/days/{flight_date}"
        )
        body = (
            b'{"error":"GDS_MAINTENANCE","message":"Partner cluster temporarily unavailable",'
            b'"retry_after_seconds":30,"correlation_id":"7f3b2a9c-1d4e-4c6b-9e8a"}'
        )
        response = requests.Response()
        response.status_code = 503
        response.reason = "Service Unavailable"
        response.url = url
        response.encoding = "utf-8"
        response._content = body
        raise requests.HTTPError(
            f"503 Server Error for url: {url}",
            response=response,
        )

    @mcp.tool()
    def search_flights(
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: Optional[str] = None,
        trip_type: int = 1,
        adults: int = 1,
        children: int = 0,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        travel_class: int = 1,
        currency: str = "USD",
        country: str = "us",
        language: str = "en",
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for flights using SerpAPI's Google Flights API.

        Args:
            departure_id: Departure airport code (e.g., 'LAX', 'JFK') or location kgmid
            arrival_id: Arrival airport code (e.g., 'CDG', 'LHR') or location kgmid
            outbound_date: Departure date in YYYY-MM-DD format (e.g., '2024-12-15')
            return_date: Return date in YYYY-MM-DD format (required for round trips)
            trip_type: Flight type (1=Round trip, 2=One way, 3=Multi-city)
            adults: Number of adult passengers (default: 1)
            children: Number of child passengers (default: 0)
            infants_in_seat: Number of infants in seat (default: 0)
            infants_on_lap: Number of infants on lap (default: 0)
            travel_class: Travel class (1=Economy, 2=Premium economy, 3=Business, 4=First)
            currency: Currency for prices (default: 'USD')
            country: Country code for search (default: 'us')
            language: Language code (default: 'en')
            max_results: Maximum number of results to store (default: 10)

        Returns:
            Dict containing flight search results and metadata
        """
        try:
            api_key = get_serpapi_key()
            dep_id = normalize_location_id(departure_id)
            arr_id = normalize_location_id(arrival_id)

            params = {
                "engine": "google_flights",
                "api_key": api_key,
                "departure_id": dep_id,
                "arrival_id": arr_id,
                "outbound_date": outbound_date,
                "type": trip_type,
                "adults": adults,
                "children": children,
                "infants_in_seat": infants_in_seat,
                "infants_on_lap": infants_on_lap,
                "travel_class": travel_class,
                "currency": currency,
                "gl": country,
                "hl": language,
            }

            if trip_type == 1 and return_date:
                params["return_date"] = return_date
            elif trip_type == 1 and not return_date:
                return {"error": "Return date is required for round trip flights"}

            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()

            flight_data = response.json()

            search_id = f"{dep_id}_{arr_id}_{outbound_date}"
            if return_date:
                search_id += f"_{return_date}"
            search_id += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            os.makedirs(flights_dir, exist_ok=True)

            processed_results = {
                "search_metadata": {
                    "search_id": search_id,
                    "departure": dep_id,
                    "arrival": arr_id,
                    "outbound_date": outbound_date,
                    "return_date": return_date,
                    "trip_type": "Round trip"
                    if trip_type == 1
                    else "One way"
                    if trip_type == 2
                    else "Multi-city",
                    "passengers": {
                        "adults": adults,
                        "children": children,
                        "infants_in_seat": infants_in_seat,
                        "infants_on_lap": infants_on_lap,
                    },
                    "travel_class": ["Economy", "Premium economy", "Business", "First"][
                        travel_class - 1
                    ],
                    "currency": currency,
                    "search_timestamp": datetime.now().isoformat(),
                },
                "best_flights": flight_data.get("best_flights", [])[:max_results],
                "other_flights": flight_data.get("other_flights", [])[:max_results],
                "price_insights": flight_data.get("price_insights", {}),
                "airports": flight_data.get("airports", []),
            }

            file_path = os.path.join(flights_dir, f"{search_id}.json")
            with open(file_path, "w") as f:
                json.dump(processed_results, f, indent=2)

            print(f"Flight search results saved to: {file_path}")

            summary = {
                "search_id": search_id,
                "total_best_flights": len(processed_results["best_flights"]),
                "total_other_flights": len(processed_results["other_flights"]),
                "price_range": {
                    "lowest_price": processed_results["price_insights"].get(
                        "lowest_price"
                    ),
                    "currency": currency,
                },
                "search_parameters": processed_results["search_metadata"],
            }

            return summary

        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

