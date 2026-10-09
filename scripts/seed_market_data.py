"""
seed_market_data.py
-------------------
Seeds realistic baseline Mandi price records for all major Indian commodities
(across states like Punjab, Haryana, UP, MP, Rajasthan, Maharashtra, Gujarat, etc.)
into the PostgreSQL database so the market analysis feature works immediately,
even when data.gov.in is experiencing downtime.
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env", file=sys.stderr)
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 15})
Session = sessionmaker(bind=engine)

SEED_DATA = [
    # Wheat
    {"commodity": "Wheat", "state": "Punjab", "district": "Ludhiana", "market": "Khanna", "min_price": "2275", "max_price": "2450", "modal_price": "2350"},
    {"commodity": "Wheat", "state": "Haryana", "district": "Karnal", "market": "Karnal", "min_price": "2275", "max_price": "2420", "modal_price": "2330"},
    {"commodity": "Wheat", "state": "Madhya Pradesh", "district": "Sehore", "market": "Sehore", "min_price": "2400", "max_price": "2850", "modal_price": "2600"},
    {"commodity": "Wheat", "state": "Uttar Pradesh", "district": "Agra", "market": "Fatehabad", "min_price": "2250", "max_price": "2380", "modal_price": "2310"},
    {"commodity": "Wheat", "state": "Rajasthan", "district": "Kota", "market": "Kota", "min_price": "2300", "max_price": "2520", "modal_price": "2410"},

    # Paddy / Rice
    {"commodity": "Rice", "state": "Punjab", "district": "Amritsar", "market": "Amritsar", "min_price": "2183", "max_price": "3800", "modal_price": "3200"},
    {"commodity": "Rice", "state": "Haryana", "district": "Kurukshetra", "market": "Thanesar", "min_price": "2200", "max_price": "3950", "modal_price": "3350"},
    {"commodity": "Rice", "state": "Uttar Pradesh", "district": "Varanasi", "market": "Varanasi", "min_price": "2183", "max_price": "2300", "modal_price": "2220"},
    {"commodity": "Rice", "state": "West Bengal", "district": "Burdwan", "market": "Memari", "min_price": "2150", "max_price": "2400", "modal_price": "2280"},
    {"commodity": "Paddy", "state": "Punjab", "district": "Patiala", "market": "Patiala", "min_price": "2203", "max_price": "3400", "modal_price": "2850"},
    {"commodity": "Paddy", "state": "Andhra Pradesh", "district": "Guntur", "market": "Tenali", "min_price": "2183", "max_price": "2350", "modal_price": "2250"},

    # Maize
    {"commodity": "Maize", "state": "Karnataka", "district": "Davangere", "market": "Davangere", "min_price": "1950", "max_price": "2280", "modal_price": "2150"},
    {"commodity": "Maize", "state": "Bihar", "district": "Gulabbagh", "market": "Purnea", "min_price": "2050", "max_price": "2350", "modal_price": "2200"},
    {"commodity": "Maize", "state": "Madhya Pradesh", "district": "Chhindwara", "market": "Chhindwara", "min_price": "1900", "max_price": "2150", "modal_price": "2050"},
    {"commodity": "Maize", "state": "Rajasthan", "district": "Bhilwara", "market": "Bhilwara", "min_price": "1980", "max_price": "2200", "modal_price": "2100"},

    # Cotton
    {"commodity": "Cotton", "state": "Gujarat", "district": "Rajkot", "market": "Rajkot", "min_price": "6800", "max_price": "7550", "modal_price": "7200"},
    {"commodity": "Cotton", "state": "Maharashtra", "district": "Yavatmal", "market": "Yavatmal", "min_price": "6700", "max_price": "7400", "modal_price": "7100"},
    {"commodity": "Cotton", "state": "Telangana", "district": "Warangal", "market": "Warangal", "min_price": "6750", "max_price": "7450", "modal_price": "7150"},

    # Mustard / Rapeseed
    {"commodity": "Mustard", "state": "Rajasthan", "district": "Bharatpur", "market": "Bharatpur", "min_price": "5200", "max_price": "5650", "modal_price": "5450"},
    {"commodity": "Mustard", "state": "Haryana", "district": "Rewari", "market": "Rewari", "min_price": "5150", "max_price": "5580", "modal_price": "5400"},
    {"commodity": "Mustard", "state": "Madhya Pradesh", "district": "Morena", "market": "Morena", "min_price": "5100", "max_price": "5500", "modal_price": "5320"},

    # Soybean
    {"commodity": "Soybean", "state": "Madhya Pradesh", "district": "Indore", "market": "Indore", "min_price": "4300", "max_price": "4750", "modal_price": "4550"},
    {"commodity": "Soybean", "state": "Maharashtra", "district": "Latur", "market": "Latur", "min_price": "4250", "max_price": "4700", "modal_price": "4500"},
    {"commodity": "Soybean", "state": "Rajasthan", "district": "Kota", "market": "Kota", "min_price": "4200", "max_price": "4680", "modal_price": "4480"},

    # Onion
    {"commodity": "Onion", "state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon", "min_price": "1400", "max_price": "2800", "modal_price": "2100"},
    {"commodity": "Onion", "state": "Maharashtra", "district": "Ahmednagar", "market": "Rahata", "min_price": "1350", "max_price": "2650", "modal_price": "2050"},
    {"commodity": "Onion", "state": "Karnataka", "district": "Hubli", "market": "Hubli", "min_price": "1500", "max_price": "2900", "modal_price": "2200"},
    {"commodity": "Onion", "state": "Madhya Pradesh", "district": "Neemuch", "market": "Neemuch", "min_price": "1200", "max_price": "2400", "modal_price": "1850"},

    # Potato
    {"commodity": "Potato", "state": "Uttar Pradesh", "district": "Agra", "market": "Agra", "min_price": "1100", "max_price": "1650", "modal_price": "1400"},
    {"commodity": "Potato", "state": "West Bengal", "district": "Hooghly", "market": "Sheoraphuly", "min_price": "1200", "max_price": "1750", "modal_price": "1500"},
    {"commodity": "Potato", "state": "Punjab", "district": "Jalandhar", "market": "Jalandhar", "min_price": "1050", "max_price": "1550", "modal_price": "1300"},

    # Tomato
    {"commodity": "Tomato", "state": "Karnataka", "district": "Kolar", "market": "Kolar", "min_price": "1600", "max_price": "3200", "modal_price": "2400"},
    {"commodity": "Tomato", "state": "Maharashtra", "district": "Pune", "market": "Narayangaon", "min_price": "1500", "max_price": "3000", "modal_price": "2250"},
    {"commodity": "Tomato", "state": "Andhra Pradesh", "district": "Chittoor", "market": "Madanapalle", "min_price": "1700", "max_price": "3400", "modal_price": "2500"},

    # Gram / Chana
    {"commodity": "Gram", "state": "Madhya Pradesh", "district": "Vidisha", "market": "Vidisha", "min_price": "5600", "max_price": "6200", "modal_price": "5950"},
    {"commodity": "Gram", "state": "Rajasthan", "district": "Bikaner", "market": "Bikaner", "min_price": "5500", "max_price": "6100", "modal_price": "5850"},
    {"commodity": "Gram", "state": "Maharashtra", "district": "Akola", "market": "Akola", "min_price": "5550", "max_price": "6150", "modal_price": "5900"},

    # Sugarcane
    {"commodity": "Sugarcane", "state": "Uttar Pradesh", "district": "Muzaffarnagar", "market": "Muzaffarnagar", "min_price": "350", "max_price": "380", "modal_price": "365"},
    {"commodity": "Sugarcane", "state": "Maharashtra", "district": "Kolhapur", "market": "Kolhapur", "min_price": "340", "max_price": "375", "modal_price": "360"},

    # Groundnut
    {"commodity": "Groundnut", "state": "Gujarat", "district": "Junagadh", "market": "Junagadh", "min_price": "5800", "max_price": "6800", "modal_price": "6400"},
    {"commodity": "Groundnut", "state": "Rajasthan", "district": "Bikaner", "market": "Bikaner", "min_price": "5600", "max_price": "6600", "modal_price": "6200"},
    {"commodity": "Groundnut", "state": "Andhra Pradesh", "district": "Anantapur", "market": "Anantapur", "min_price": "5700", "max_price": "6700", "modal_price": "6300"},

    # Bajra
    {"commodity": "Bajra", "state": "Rajasthan", "district": "Jaipur", "market": "Chomu", "min_price": "2200", "max_price": "2500", "modal_price": "2350"},
    {"commodity": "Bajra", "state": "Haryana", "district": "Bhiwani", "market": "Bhiwani", "min_price": "2150", "max_price": "2450", "modal_price": "2300"},

    # Barley
    {"commodity": "Barley", "state": "Rajasthan", "district": "Sri Ganganagar", "market": "Sri Ganganagar", "min_price": "1850", "max_price": "2200", "modal_price": "2050"},
    {"commodity": "Barley", "state": "Uttar Pradesh", "district": "Aligarh", "market": "Aligarh", "min_price": "1800", "max_price": "2150", "modal_price": "2000"},
]

now = datetime.now(timezone.utc)
db = Session()
try:
    print(f"Seeding {len(SEED_DATA)} market records into PostgreSQL...")
    for r in SEED_DATA:
        db.execute(text("""
            INSERT INTO market_prices
                (commodity, state, district, market, min_price, max_price, modal_price, fetched_at)
            VALUES
                (:commodity, :state, :district, :market, :min_price, :max_price, :modal_price, :fetched_at)
        """), {
            "commodity": r["commodity"],
            "state": r["state"],
            "district": r["district"],
            "market": r["market"],
            "min_price": r["min_price"],
            "max_price": r["max_price"],
            "modal_price": r["modal_price"],
            "fetched_at": now,
        })
    db.commit()
    print("Successfully seeded market prices into PostgreSQL!")
except Exception as exc:
    db.rollback()
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)
finally:
    db.close()
