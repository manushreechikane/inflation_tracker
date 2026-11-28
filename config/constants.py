"""Fixed values shared across the project. Nothing here reads the environment."""
from enum import Enum

APP_NAME = "InflationLens"
APP_TAGLINE = "Your groceries. Your prices. Your real inflation."

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


class ProcessingStatus(str, Enum):
    UPLOADED = "uploaded"
    OCR_SUCCESS = "ocr_success"
    OCR_PARTIAL = "ocr_partial"
    OCR_FAILED = "ocr_failed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VerificationStatus(str, Enum):
    PENDING = "pending"      # extracted, not yet reviewed by the user
    VERIFIED = "verified"    # the only status used in inflation maths
    REJECTED = "rejected"


class CPISourceType(str, Enum):
    API = "api"
    MANUAL_IMPORT = "manual_import"
    BUNDLED_SAMPLE = "bundled_sample"


GROCERY_CATEGORIES = [
    "Dairy", "Staples", "Vegetables", "Fruits", "Meat & Eggs",
    "Snacks", "Beverages", "Bakery", "Oils & Spices", "Household", "Personal care",
    "Other",
]

# Category guesses from product names, used only when a receipt does not say.
CATEGORY_KEYWORDS = {
    "Dairy": ["milk", "curd", "yogurt", "paneer", "butter", "cheese", "cream", "ghee"],
    "Staples": ["atta", "flour", "rice", "dal", "pulse", "sugar", "salt", "wheat", "sooji", "besan", "poha"],
    "Vegetables": ["onion", "tomato", "potato", "chilli", "spinach", "carrot", "cabbage", "beans", "cucumber", "ginger", "garlic"],
    "Fruits": ["apple", "banana", "orange", "grape", "mango", "pomegranate", "lemon"],
    "Meat & Eggs": ["egg", "chicken", "mutton", "fish", "prawn"],
    "Snacks": ["biscuit", "chips", "namkeen", "chocolate", "cookie", "wafer", "kurkure"],
    "Beverages": ["tea", "coffee", "juice", "cola", "water", "soda", "drink"],
    "Bakery": ["bread", "bun", "cake", "rusk", "pav"],
    "Oils & Spices": ["oil", "masala", "turmeric", "chilli powder", "cumin", "coriander", "mustard", "pepper"],
    "Household": ["surf", "detergent", "soap", "dishwash", "cleaner", "harpic", "phenyl", "tissue", "garbage"],
    "Personal care": ["shampoo", "toothpaste", "toothbrush", "deodorant", "razor", "sanitary"],
}

# Package units we normalise into. Everything is stored in the base unit so
# price-per-gram comparisons survive a change of pack size.
MASS_UNITS = {"g": 1.0, "gm": 1.0, "gms": 1.0, "gram": 1.0, "grams": 1.0,
              "kg": 1000.0, "kgs": 1000.0, "kilo": 1000.0, "kilogram": 1000.0}
VOLUME_UNITS = {"ml": 1.0, "millilitre": 1.0, "milliliter": 1.0, "cc": 1.0,
                "l": 1000.0, "lt": 1000.0, "ltr": 1000.0, "litre": 1000.0,
                "liter": 1000.0, "litres": 1000.0, "liters": 1000.0}
COUNT_UNITS = {"pc": 1.0, "pcs": 1.0, "piece": 1.0, "pieces": 1.0, "nos": 1.0,
               "pack": 1.0, "pkt": 1.0, "packet": 1.0, "dozen": 12.0}

BASE_UNIT = {"g": "g", "kg": "g", "ml": "ml", "l": "ml", "pc": "pcs", "pcs": "pcs"}

SUPPORTED_COUNTRIES = {
    "IN": {"label": "India", "cpi_source": "MoSPI (manual import)"},
    "US": {"label": "United States", "cpi_source": "BLS API"},
}
SUPPORTED_CURRENCIES = {"INR": "₹", "USD": "$"}

# Words that mark a receipt line as tax / total / payment metadata rather than
# a purchased product when parsing.
RECEIPT_KEYWORDS = (
    "total", "subtotal", "sub total", "tax", "gst", "cgst", "sgst", "vat",
    "discount", "saving", "change", "cash", "card", "upi", "balance", "round off",
    "invoice", "bill no", "bill number", "gstin", "phone", "mobile", "date",
    "time", "cashier", "thank", "visit", "qty", "items", "item count", "amount",
)
