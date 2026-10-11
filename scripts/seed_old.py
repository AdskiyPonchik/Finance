import requests
import random
from datetime import datetime, timedelta

# this script is only for data seeding

# --- CONFIG ---
BASE_URL = "http://127.0.0.1:8080/api"
USERNAME = "admin"
PASSWORD = "admin"
TX_COUNT = 1000  # more data for beauty

# --- AUTH ---
print(f"(!) Logging in as {USERNAME}...")
session = requests.Session()
auth_resp = session.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})

if auth_resp.status_code != 200:
    print(f"Error login: {auth_resp.text}")
    exit()

token = auth_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# --- FETCH CATEGORIES ---
print("(!) Fetching categories...")
cat_resp = session.get(f"{BASE_URL}/categories/", headers=headers)
categories = cat_resp.json()

# Dividing categories
expense_cats = [c for c in categories if c["type"] == "expense"]
income_cats = [c for c in categories if c["type"] == "income"]

if not expense_cats or not income_cats:
    print("Error: Need both Expense and Income categories to exist!")
    exit()

print(f"(!) Seeding with {len(expense_cats)} expense & {len(income_cats)} income categories...")

# --- GENERATE DATA ---
success_count = 0
today = datetime.now()

for i in range(TX_COUNT):
    days_back = random.randint(0, 365)
    tx_date = today - timedelta(days=days_back)

    # Решаем: Доход или Расход? (20% шанс на доход)
    is_income = random.random() < 0.1

    if is_income:
        # INCOME
        category = random.choice(income_cats)
        # Salaries are usually bigger: 1000 - 3000, hustles smaller
        if random.random() < 0.3:
            amount_eur = random.randint(1000, 3000)  # Big salary
        else:
            amount_eur = random.randint(50, 500)  # Side hustle
        sign = 1
    else:
        # EXPENSE
        category = random.choice(expense_cats)
        rand_val = random.random()
        if rand_val < 0.7:
            amount_eur = random.randint(3, 20)  # Coffee/Food
        elif rand_val < 0.95:
            amount_eur = random.randint(20, 100)  # Groceries
        else:
            amount_eur = random.randint(100, 800)  # Tech/Rent
        sign = -1

    # Converting to cents
    amount_cents = sign * (amount_eur * 100)

    payload = {
        "title": f"Auto-Seed {i} ({'Inc' if is_income else 'Exp'})",
        "amount": amount_cents,
        "date": tx_date.strftime("%Y-%m-%d"),
        "category_id": category["id"]
    }

    res = session.post(f"{BASE_URL}/transactions/", json=payload, headers=headers)
    if res.status_code == 200:
        success_count += 1
        if success_count % 50 == 0: print(f" -> {success_count}...")

print(f"\n(!!) DONE. Mixed {success_count} transactions.")