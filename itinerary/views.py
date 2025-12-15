from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# -----------------------------
# INDIA-SPECIFIC CONFIG
# -----------------------------

INDIA_INTEREST_MAP = {
    "Temples & Shrines": "temples, shrines, religious sites",
    "Forts & Palaces": "historic forts, palaces, royal heritage",
    "Cultural Heritage": "cultural heritage, traditional arts",
    "Traditional Food": "local cuisine, street food, traditional dishes",
    "Museums & Art Galleries": "museums, art galleries, exhibitions"
}

# Known places with free entry (truth override)
KNOWN_FREE_PLACES = {
    "Gateway of India",
    "Marine Drive",
    "Juhu Beach",
    "India Gate",
    "Charminar",
    "Howrah Bridge",
    "Rock Beach",
    "Marina Beach",
    "Haji Ali Dargah"
}

# Budget caps (per day)
BUDGET_CAPS = {
    "Budget Friendly": 2000,
    "Moderate": 5000,
    "Luxury Experience": 12000
}


# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------

def normalize_costs(itinerary_text):
    """
    Forces known free places to always show as Free
    """
    for place in KNOWN_FREE_PLACES:
        itinerary_text = itinerary_text.replace(
            f"{place} – Low-cost",
            f"{place} – Free"
        )
        itinerary_text = itinerary_text.replace(
            f"{place} – Moderate",
            f"{place} – Free"
        )
    return itinerary_text


def enforce_budget_language(itinerary_text, budget):
    """
    Ensures AI does not exceed budget promises
    """
    cap = BUDGET_CAPS.get(budget)

    if not cap:
        return itinerary_text

    if cap <= 2000:
        note = "\nNote: This itinerary prioritizes free attractions, street food, and public transport."
    elif cap <= 5000:
        note = "\nNote: This itinerary balances popular attractions with comfort."
    else:
        note = "\nNote: This itinerary includes premium experiences and flexibility."

    return itinerary_text + note


# -----------------------------
# API VIEW
# -----------------------------

@api_view(['POST'])
def generate_itinerary(request):
    """
    Generates a budget-safe, India-specific travel itinerary.
    """

    data = request.data

    city = data.get("city")
    location = data.get("location")
    trip_duration = data.get("trip_duration", "1-day")
    budget = data.get("budget", "Moderate")
    interests = data.get("interests", [])

    if not city or not interests:
        return Response(
            {"error": "City and interests are required"},
            status=400
        )

    # Convert interests to India-specific text
    interest_text = [
        INDIA_INTEREST_MAP[i]
        for i in interests
        if i in INDIA_INTEREST_MAP
    ]
    interest_str = ", ".join(interest_text)

    location_str = (
        f"User current coordinates: {location}. "
        if location else ""
    )

    budget_guidance = {
        "Budget Friendly": "Daily spending should stay under ₹2,000 using free attractions, street food, and public transport.",
        "Moderate": "Daily spending should be ₹2,000–₹5,000 with a mix of comfort and value.",
        "Luxury Experience": "Daily spending can exceed ₹5,000 including premium experiences."
    }.get(budget, "")

    # -----------------------------
    # PROMPT (STRICT & SAFE)
    # -----------------------------

    prompt = f"""
You are an expert Indian travel planning and budgeting assistant.

{location_str}
Plan a {trip_duration} trip in {city}.

User Budget Category: {budget}
Budget Guidance: {budget_guidance}
User Interests: {interest_str}

STRICT COST RULES (MANDATORY):
- NEVER give exact entry fees for monuments.
- Use ONLY these cost labels for attractions:
  • Free
  • Low-cost (₹0–₹100)
  • Moderate (₹100–₹500)
  • Premium (₹500+)
- Food costs may be estimated per meal.
- Transport costs may be estimated per day.
- If unsure, say "Cost varies".

For EACH DAY include:
- Attractions with cost label
- Suggested visit timings
- Estimated food cost range
- Estimated local transport cost
- Estimated total daily spend range

Respond ONLY in plain text using:
Day 1:
Day 2:
etc.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an Indian travel budgeting expert. "
                    "You must prioritize factual accuracy. "
                    "Never invent exact monument entry fees. "
                    "Use cost ranges and categories only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1100,
        "temperature": 0.3
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        itinerary_text = result["choices"][0]["message"]["content"]

        # Post-processing safety
        itinerary_text = normalize_costs(itinerary_text)
        itinerary_text = enforce_budget_language(itinerary_text, budget)

        return Response({"itinerary": itinerary_text})

    except Exception as e:
        print("Itinerary generation error:", e)
        return Response(
            {"error": "Failed to generate itinerary"},
            status=500
        )
