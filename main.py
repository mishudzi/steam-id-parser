import aiohttp
import asyncio
from bs4 import BeautifulSoup
import sqlite3

async def fetch_data(session, profile_url):
    async with session.get(profile_url) as response:
        return await response.text()

async def get_user_data(profile_url, session):
    html_content = await fetch_data(session, profile_url)
    soup = BeautifulSoup(html_content, 'html.parser')

    error_message = soup.find('div', {'id': 'message'})
    if error_message and 'Указанный профиль не найден.' in error_message.text:
        return None, None

    name_tag = soup.find('span', class_='actual_persona_name')
    name = name_tag.text if name_tag else 'Unknown'

    level_tag = soup.find('div', class_='persona_name persona_level')
    level_text = level_tag.text if level_tag else ''
    level = level_text.replace('Уровень', '').strip() if level_text else 'Unknown'

    return name, level

async def process_combination(combination, session, cursor, semaphore, conn):
    base_url = "https://steamcommunity.com/id/"
    profile_link = base_url + combination

    async with semaphore:
        try:
            name, level = await asyncio.wait_for(get_user_data(profile_link, session), timeout=30)
            if name is not None and level is not None:
                cursor.execute('INSERT INTO users (profile_link, name, level) VALUES (?, ?, ?)', (profile_link, name, level))
                print(f"Processed: {profile_link} - {name} - {level}")
                conn.commit()
        except asyncio.TimeoutError:
            print(f"Timeout error for {profile_link}. Waiting for 5 seconds...")
            await asyncio.sleep(5)

async def main():
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_link TEXT,
            name TEXT,
            level TEXT
        )
    ''')

    characters = "abcdefghijklmnopqrstuvwxyz1234567890-_"
    combinations = [a + b + c for a in characters for b in characters for c in characters]

    semaphore = asyncio.Semaphore(50)
    async with aiohttp.ClientSession() as session:
        tasks = [process_combination(combination, session, cursor, semaphore, conn) for combination in combinations]
        await asyncio.gather(*tasks)

    conn.close()
    print("Parsing and data insertion complete.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
