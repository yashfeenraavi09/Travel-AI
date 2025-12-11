from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# Map interests to India-specific categories
INDIA_INTEREST_MAP = {
    "Temples & Shrines": "temples, shrines, religious sites",
    "Forts & Palaces": "historic forts, palaces, royal heritage",
    "Cultural Heritage": "cultural heritage, traditional arts",
    "Traditional Food": "local cuisine, street food, traditional dishes",
    "Museums & Art Galleries": "museums, art galleries, exhibitions"
}

@api_view(['POST'])
def generate_itinerary(request):
    """
    Generates AI-based itinerary for India-specific travel.
    Accepts:
      - city
      - location (lat, lon) optional
      - tripDuration: '1-day', '2–3 days', 'Week'
      - budget: 'Budget Friendly', 'Moderate', 'Luxury Experience'
      - interests: list of interests
    """

    data = request.data
    city = data.get("city")
    location = data.get("location", None)
    tripDuration = data.get("trip_duration", "1-day")
    budget = data.get("budget", "Moderate")
    interests = data.get("interests", [])

    if not city or not interests:
        return Response({"error": "City and interests are required"}, status=400)

    # Convert interests into India-specific prompt text
    interest_text = []
    for i in interests:
        mapped = INDIA_INTEREST_MAP.get(i)
        if mapped:
            interest_text.append(mapped)
    interest_str = ", ".join(interest_text)

    # Include location in prompt if provided
    location_str = f"User is currently at latitude/longitude: {location}. " if location else ""

    # Include budget guidance
    budget_map = {
        "Budget Friendly": "Focus on attractions with low entry fees and local experiences (under ₹2,000/day).",
        "Moderate": "Mix of popular attractions and comfortable options (₹2,000–₹5,000/day).",
        "Luxury Experience": "Include premium hotels, experiences, and guided tours (above ₹5,000/day)."
    }
    budget_str = budget_map.get(budget, "")

    # Construct prompt for Groq
    prompt = f"""
    You are an expert India travel planner AI.

    {location_str}
    Create a detailed day-wise travel itinerary for a trip in {city}.
    Trip Duration: {tripDuration}
    Interests: {interest_str}
    Budget: {budget_str}

    Include:
      - Famous monuments (e.g., Taj Mahal, Gateway of India, Jaipur Forts)
      - Suggested timings for visiting attractions
      - Local food and cultural experiences
      - Day-wise schedule

    Respond in plain text with 'Day 1:', 'Day 2:', etc.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful Indian travel assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }

    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        itinerary_text = result["choices"][0]["message"]["content"]

        return Response({"itinerary": itinerary_text})
    except Exception as e:
        print("Error generating itinerary:", e)
        return Response({"error": "Failed to generate itinerary"}, status=500)
