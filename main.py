import asyncio

from extract.tiktok_scraper import get_comments
from load.db import init_db, save_comments, save_video_urls, get_video_urls
from manager import manager  # импорт менеджера
from transform.clean_comments import clean_comments

USERNAME = "toptier.ielts"  # замените на нужный TikTok username


async def etl():
    print("🧱 Инициализация БД...")
    init_db()

    print("🧠 Инициализация PlaywrightManager...")
    await manager.startup()

    try:
        # await asyncio.sleep(100000000)
        print(f"🌐 Сканируем профиль @{USERNAME}...")
        video_data = get_video_urls()  # await get_all_video_urls(USERNAME)
        print(f"🔗 Найдено видео: {len(video_data)}")

        # save_video_urls(video_data)

        print("🔁 Извлечение всех комментариев...")
        for video in video_data:
            url = video #['url']
            print(f"➡️  Обработка: {url}")
            try:
                raw = await get_comments(url)
                print(f"🗃️  Комментариев: {len(raw)}")
                cleaned = clean_comments(raw)
                save_comments(cleaned)
            except Exception as e:
                print(f"❌ Ошибка: {e}")

        print("✅ Готово!")

    finally:
        print("🔻 Завершение работы менеджера...")
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(etl())
