import aiohttp
import asyncio
from typing import Dict
import random
from datetime import datetime, timedelta

from seed_old import amount_eur, success_count

BASE_URL = "http://127.0.0.1:8080/api"
USERNAME = "admin"
PASSWORD = "admin"
TX_COUNT = 1_000_000 # data count


def generate_payload(expense_cats, income_cats) -> Dict:
    today = datetime.now()
    days_back = random.randint(0, 365)
    tx_date = today - timedelta(days=days_back)
    is_income = random.random() < 0.1

    if is_income:
        category = random.choice(income_cats)
        amount_eur = random.randint(1000, 3000) if random.random() < 0.3 else random.randint(50, 500)
        sign = 1
    else:
        category = random.choice(expense_cats)
        rand_val = random.random()
        if rand_val < 0.7:
            amount_eur = random.randint(3, 20)
        elif rand_val < 0.95:
            amount_eur = random.randint(20, 100)
        else:
            amount_eur = random.randint(100, 800)
        sign = -1
    return {
        "title": f"Async ({'Inc' if is_income else 'Exp'})",
        "amount": sign * (amount_eur * 100),
        "date": tx_date.strftime("%Y-%m-%d"),
        "category_id": category["id"]
    }

async def main():
    async with aiohttp.ClientSession() as session:
        print("Logging in...")
        async with session.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD}) as resp:
            if resp.status != 200:
                print("Login failed")
                return
            token_data = await resp.json()
            token = token_data["access_token"]
            headers = {"Authorization": f"Bearer {token}"} #standart rfc 6750
        print("Fetching categories...")
        async with session.get(f"{BASE_URL}/categories/", headers=headers) as resp:
            categories = await resp.json()
            expense_cats = [c for c in categories if c["type"] == "expense"]
            income_cats = [c for c in categories if c["type"] == "income"]
        print(f"Preparing {TX_COUNT} requests...")
        tasks = []
        for _ in range(TX_COUNT):
            payload = generate_payload(expense_cats, income_cats)
            req = session.post(f"{BASE_URL}/transactions/", json=payload, headers=headers)
            tasks.append(req)

        print("Sending requests...")
        start_time = datetime.now()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        duration = datetime.now() - start_time
        success_count = sum(1 for resp in responses if resp.status == 200)
        print(f"Done in {duration}. Success = {success_count}/{TX_COUNT}")

if __name__ == "__main__":
    asyncio.run(main())