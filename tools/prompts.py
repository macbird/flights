from typing import Any


def register_prompts(mcp: Any) -> None:
    @mcp.prompt()
    def travel_planning_prompt(
        departure: str,
        destination: str,
        departure_date: str,
        return_date: str = "",
        passengers: int = 1,
        budget: str = "",
        preferences: str = "",
    ) -> str:
        """Generate a comprehensive travel planning prompt for Claude."""
        prompt = (
            "Plan a comprehensive trip from "
            f"{departure} to {destination} departing on {departure_date}"
        )

        if return_date:
            prompt += f" and returning on {return_date}"
        else:
            prompt += " (one way)"

        prompt += f" for {passengers} passenger{'s' if passengers != 1 else ''}."

        if budget:
            prompt += f" Budget consideration: {budget}."

        if preferences:
            prompt += f" Travel preferences: {preferences}."

        prompt += f"""

Please help with the following travel planning tasks:

1. **Flight Search**: Use the search_flights tool to find the best flight options:
   - Search for flights from {departure} to {destination}
   - Departure date: {departure_date}"""

        if return_date:
            prompt += f"""
   - Return date: {return_date}
   - Trip type: Round trip (1)"""
        else:
            prompt += """
   - Trip type: One way (2)"""

        prompt += f"""
   - Number of passengers: {passengers}
   - Analyze price insights and recommend best options

2. **Flight Analysis**: Once flights are found, provide:
   - Summary of the best flight options with pros and cons
   - Price comparison and value analysis
   - Duration and layover analysis
   - Airline and aircraft information
   - Carbon emissions comparison if available

3. **Travel Recommendations**: Based on the destination and dates:
   - Best times to book and travel tips
   - Airport information and transportation options
   - Weather considerations for travel dates
   - General destination tips and highlights

4. **Budget Planning**: If budget information provided:
   - Flight cost analysis within budget
   - Tips for finding better deals
   - Alternative travel dates if current search is expensive

Present the information in a clear, organized format with actionable recommendations. Use the flight search tools first, then provide comprehensive analysis and recommendations based on the results."""

        return prompt

    @mcp.prompt()
    def flight_comparison_prompt(search_id: str) -> str:
        """Generate a prompt for detailed flight comparison and analysis."""
        return f"""Analyze and compare the flight options from search ID: {search_id}

Please provide a comprehensive analysis including:

1. **Flight Overview**: Use get_flight_details('{search_id}') to retrieve the complete flight data

2. **Best Options Analysis**:
   - Top 3-5 recommended flights with detailed breakdown
   - Price-to-value ratio analysis
   - Total travel time comparison
   - Layover analysis (duration, airports, overnight stays)

3. **Detailed Comparison Table**:
   - Price comparison across all options
   - Duration comparison (flight time vs total time)
   - Number of stops and layover quality
   - Airlines and aircraft types
   - Departure/arrival times convenience

4. **Filtering Suggestions**:
   - Use filter_flights_by_price to show budget-friendly options
   - Use filter_flights_by_airline for preferred carriers
   - Highlight direct flights vs connections

5. **Decision Recommendations**:
   - Best overall value option
   - Fastest travel option
   - Most convenient schedule option
   - Budget-conscious option

6. **Booking Considerations**:
   - Price trends and booking timing advice
   - Airline policies and baggage considerations
   - Seat selection and upgrade opportunities

Please format the analysis in a clear, easy-to-read structure with specific recommendations for different traveler priorities (speed, cost, convenience, comfort)."""

