"""Constants and prize-tier metadata."""

from __future__ import annotations

# Standard prize slots per draw (National Savings structure)
PRIZE_SLOTS = {
    100: {"1st": 1, "2nd": 5, "3rd": 1199},
    200: {"1st": 1, "2nd": 5, "3rd": 2394},
    750: {"1st": 1, "2nd": 3, "3rd": 1696},
    1500: {"1st": 1, "2nd": 3, "3rd": 1696},
    7500: {"1st": 1, "2nd": 3, "3rd": 1696},
    15000: {"1st": 1, "2nd": 3, "3rd": 770},
    25000: {"1st": 1, "2nd": 3, "3rd": 330},
    40000: {"1st": 1, "2nd": 3, "3rd": 330},
}

# Typical prize amounts shown on allprizebond.pk (for display only)
PRIZE_AMOUNTS = {
    100: {"1st": "Rs. 700,000", "2nd": "Rs. 200,000", "3rd": "Rs. 1,000"},
    200: {"1st": "Rs. 750,000", "2nd": "Rs. 250,000", "3rd": "Rs. 1,250"},
    750: {"1st": "Rs. 1,500,000", "2nd": "Rs. 500,000", "3rd": "Rs. 9,300"},
    1500: {"1st": "Rs. 3,000,000", "2nd": "Rs. 1,000,000", "3rd": "Rs. 18,500"},
    7500: {"1st": "Rs. 15,000,000", "2nd": "Rs. 5,000,000", "3rd": "Rs. 93,000"},
    15000: {"1st": "Rs. 30,000,000", "2nd": "Rs. 10,000,000", "3rd": "Rs. 185,000"},
    25000: {"1st": "Rs. 50,000,000", "2nd": "Rs. 15,000,000", "3rd": "Rs. 312,000"},
    40000: {"1st": "Rs. 80,000,000", "2nd": "Rs. 25,000,000", "3rd": "Rs. 500,000"},
}

SUPPORTED_DENOMINATIONS = tuple(sorted(PRIZE_SLOTS))

BASE_URL = "https://allprizebond.pk/draw/{denomination}/{draw_date}"
HOMEPAGE_URL = "https://allprizebond.pk/"

DEFAULT_DENOMINATION = 200
DEFAULT_BONDS_FILE = "bonds.txt"
HISTORY_FILENAME = "history.sqlite"
LOG_FILENAME = "qismat.log"
WEB_PORT = 8765

CLAIM_NOTE = (
    "Verify this result through official National Savings channels before claiming. "
    "Take the original prize bond to a National Savings centre or an authorised bank. "
    "Claim rules and deadlines can change — confirm locally."
)
