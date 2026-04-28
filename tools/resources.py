import json
import os
from typing import Any


def register_resources(mcp: Any, *, flights_dir: str) -> None:
    @mcp.resource("flights://searches")
    def get_flight_searches() -> str:
        """
        List all available flight searches.

        This resource provides a list of all saved flight searches.
        """
        searches = []

        if os.path.exists(flights_dir):
            for filename in os.listdir(flights_dir):
                if filename.endswith(".json"):
                    search_id = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(flights_dir, filename)
                    try:
                        with open(file_path, "r") as f:
                            data = json.load(f)
                            metadata = data.get("search_metadata", {})
                            searches.append(
                                {
                                    "search_id": search_id,
                                    "route": f"{metadata.get('departure', 'N/A')} → {metadata.get('arrival', 'N/A')}",
                                    "dates": f"{metadata.get('outbound_date', 'N/A')} - {metadata.get('return_date', 'One way')}",
                                    "passengers": metadata.get("passengers", {}),
                                    "search_time": metadata.get("search_timestamp", "N/A"),
                                }
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue

        content = "# Flight Searches\n\n"
        if searches:
            content += f"Total searches: {len(searches)}\n\n"
            for search in searches:
                content += f"## {search['search_id']}\n"
                content += f"- **Route**: {search['route']}\n"
                content += f"- **Dates**: {search['dates']}\n"
                content += (
                    f"- **Passengers**: {search['passengers'].get('adults', 0)} adults"
                )
                if search["passengers"].get("children", 0) > 0:
                    content += f", {search['passengers']['children']} children"
                if search["passengers"].get("infants_in_seat", 0) > 0:
                    content += (
                        f", {search['passengers']['infants_in_seat']} infants in seat"
                    )
                if search["passengers"].get("infants_on_lap", 0) > 0:
                    content += (
                        f", {search['passengers']['infants_on_lap']} infants on lap"
                    )
                content += "\n"
                content += f"- **Search Time**: {search['search_time']}\n\n"
                content += "---\n\n"
        else:
            content += "No flight searches found.\n\n"
            content += "Use the search_flights tool to search for flights.\n"

        return content

    @mcp.resource("flights://{search_id}")
    def get_flight_search_details(search_id: str) -> str:
        """
        Get detailed information about a specific flight search.

        Args:
            search_id: The flight search ID to retrieve details for
        """
        file_path = os.path.join(flights_dir, f"{search_id}.json")

        if not os.path.exists(file_path):
            return (
                f"# Flight Search Not Found: {search_id}\n\n"
                "No flight search found with this ID."
            )

        try:
            with open(file_path, "r") as f:
                flight_data = json.load(f)

            metadata = flight_data.get("search_metadata", {})
            best_flights = flight_data.get("best_flights", [])
            other_flights = flight_data.get("other_flights", [])
            price_insights = flight_data.get("price_insights", {})

            content = f"# Flight Search: {search_id}\n\n"
            content += "## Search Details\n"
            content += (
                f"- **Route**: {metadata.get('departure', 'N/A')} → {metadata.get('arrival', 'N/A')}\n"
            )
            content += f"- **Dates**: {metadata.get('outbound_date', 'N/A')}"
            if metadata.get("return_date"):
                content += f" - {metadata['return_date']}"
            content += "\n"
            content += f"- **Trip Type**: {metadata.get('trip_type', 'N/A')}\n"
            content += f"- **Travel Class**: {metadata.get('travel_class', 'N/A')}\n"
            content += f"- **Currency**: {metadata.get('currency', 'USD')}\n"
            content += f"- **Search Time**: {metadata.get('search_timestamp', 'N/A')}\n\n"

            if price_insights:
                content += "## Price Insights\n"
                if "lowest_price" in price_insights:
                    content += (
                        f"- **Lowest Price**: {price_insights['lowest_price']} {metadata.get('currency', 'USD')}\n"
                    )
                if "price_level" in price_insights:
                    content += f"- **Price Level**: {price_insights['price_level']}\n"
                if (
                    "typical_price_range" in price_insights
                    and price_insights["typical_price_range"]
                ):
                    range_data = price_insights["typical_price_range"]
                    content += (
                        f"- **Typical Range**: {range_data[0]} - {range_data[1]} {metadata.get('currency', 'USD')}\n"
                    )
                content += "\n"

            if best_flights:
                content += f"## Best Flights ({len(best_flights)})\n\n"
                for i, flight in enumerate(best_flights[:5]):
                    content += f"### Option {i + 1}\n"
                    content += (
                        f"- **Price**: {flight.get('price', 'N/A')} {metadata.get('currency', 'USD')}\n"
                    )
                    content += (
                        f"- **Total Duration**: {flight.get('total_duration', 0)} minutes\n"
                    )
                    content += f"- **Flights**: {len(flight.get('flights', []))}\n"
                    if flight.get("layovers"):
                        content += f"- **Layovers**: {len(flight['layovers'])}\n"

                    for j, leg in enumerate(flight.get("flights", [])):
                        dep_airport = leg.get("departure_airport", {})
                        arr_airport = leg.get("arrival_airport", {})
                        content += (
                            f"  - **Flight {j + 1}**: {dep_airport.get('id', 'N/A')} → {arr_airport.get('id', 'N/A')}\n"
                        )
                        content += f"    - Departure: {dep_airport.get('time', 'N/A')}\n"
                        content += f"    - Arrival: {arr_airport.get('time', 'N/A')}\n"
                        content += f"    - Airline: {leg.get('airline', 'N/A')}\n"
                        content += (
                            f"    - Flight Number: {leg.get('flight_number', 'N/A')}\n"
                        )

                    content += "\n"

            if other_flights:
                content += "## Other Flights\n"
                content += f"Total other options: {len(other_flights)}\n"
                content += (
                    "Price range: "
                    f"{min(f.get('price', 0) for f in other_flights)} - "
                    f"{max(f.get('price', 0) for f in other_flights)} "
                    f"{metadata.get('currency', 'USD')}\n\n"
                )

            return content

        except json.JSONDecodeError:
            return f"# Error\n\nCorrupted flight data for search ID: {search_id}"

