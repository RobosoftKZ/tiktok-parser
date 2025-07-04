import asyncio
import os
import random

from playwright.async_api import async_playwright

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
]
desktop_user_agents = [
    # Windows - Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Windows - Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # macOS - Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    # macOS - Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Linux - Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Linux - Firefox
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

class PlaywrightManager:
    def __init__(self):
        self.browser = None
        self.context = None
        self.lock = asyncio.Lock()

    def _ignore_problematic_files(self, dir, files):
        ignored = []
        for file in files:
            full_path = os.path.join(dir, file)
            try:
                if not os.path.isfile(full_path) and not os.path.isdir(full_path):
                    ignored.append(file)
            except Exception:
                ignored.append(file)
        return ignored

    async def startup(self):
        self.playwright = await async_playwright().start()
        original_profile = "sessions/profile"
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=original_profile,
            headless=False,
            args=["--start-maximized"],
            viewport={"width": 1280, "height": 800},
            user_agent=random.choice(desktop_user_agents),
        )
        print("🌐 Persistent context запущен")

    async def shutdown(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("🌐 Браузер закрыт")

    async def get_page(self):
        async with self.lock:
            try:
                page = await self.context.new_page()
            except Exception as e:
                print("Context is invalid. Пересоздание...")
                self.context = await self.browser.new_context()
                page = await self.context.new_page()

            # Объединённый обработчик запроса
            async def block_unwanted_and_handle_captcha(route, request):
                url = request.url
                resource_type = request.resource_type

                # Проверка на CAPTCHA
                if "captcha.vendors" in url:
                    print("🛑 CAPTCHA-ресурс обнаружен: ", url)

                    # Ожидаем появления CAPTCHA в DOM
                    try:
                        await asyncio.sleep(1000000)
                        # await request.frame.page.wait_for_selector("iframe[src*='recaptcha']", timeout=10000)
                    except Exception:
                        print("⚠️ CAPTCHA iframe не найден за 10 секунд")

                    print("⏸ Пауза для решения CAPTCHA вручную...")
                    # input("🔐 Нажмите Enter после решения CAPTCHA в браузере...")

                # Блокируем ненужные ресурсы
                if resource_type in ["image", "media", "font"]:
                    if "recaptcha" in url or "gstatic.com/recaptcha" in url:
                        await route.continue_()
                    else:
                        await route.abort()
                else:
                    await route.continue_()

            # Применяем роутинг ко всем запросам
            await page.route("**/*", block_unwanted_and_handle_captcha)

            return page


manager = PlaywrightManager()
