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


GROCERY_CATEGORIES = [
    "Dairy", "Staples", "Vegetables", "Fruits", "Meat & Eggs",
    "Snacks", "Beverages", "Bakery", "Oils & Spices", "Household", "Other",
]

SUPPORTED_COUNTRIES = {"IN": "India", "US": "United States"}
SUPPORTED_CURRENCIES = {"INR": "₹", "USD": "$"}
