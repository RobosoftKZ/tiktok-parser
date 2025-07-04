from lxml.etree import ElementTree
from lxml.html import fromstring
from playwright.async_api import async_playwright


async def find_xpath_by_href(page, href_substring: str = "/tab/reviews") -> str:
    locator = page.locator(f'a[href*="{href_substring}"]')

    try:
        await locator.first.wait_for(state="visible", timeout=10000)
        print("✅ Ссылка найдена")
    except:
        print("❌ Ссылка не найдена")
        return ""

    full_html = await page.content()
    doc = fromstring(full_html)
    tree = ElementTree(doc)

    for el in doc.xpath(f'//a[contains(@href, "{href_substring}")]'):
        xpath = tree.getpath(el)
        print(f"📍 XPATH найден: {xpath}")
        return xpath

    print("⚠️ Не удалось построить XPATH")
    return ""


async def click_by_xpath(page, xpath: str):
    try:
        locator = page.locator(f'xpath={xpath}')
        await locator.scroll_into_view_if_needed()
        await locator.click()
        print("🖱️ Клик выполнен")
    except Exception as e:
        print(f"❌ Ошибка при клике: {e}")


async def find_load_more_button(page, button_text="Загрузить ещё"):
    locator = page.locator("button", has_text=button_text)

    if await locator.count() == 0:
        print("❌ Кнопка 'Загрузить ещё' не найдена")
        return None

    print("✅ Кнопка 'Загрузить ещё' найдена")
    return locator.first


async def get_parent_class_by_text(page, text: str, levels_up: int = 8) -> str:
    locator = page.locator(f"text={text}")
    if await locator.count() == 0:
        print(f"❌ Элемент с текстом '{text}' не найден")
        return ""

    element = await locator.first.element_handle()

    class_name = await element.evaluate(f'''(el) => {{
        let parent = el;
        for (let i = 0; i < {levels_up}; i++) {{
            if (!parent.parentElement) break;
            parent = parent.parentElement;
        }}
        return parent.className;
    }}''')

    print(f"✅ Класс {levels_up}-го родителя: {class_name}")
    return class_name


async def get_parent_class_by_text(page, text: str, levels_up: int = 8, timeout: int = 10000) -> str | None:
    try:
        await page.locator(f"text={text}").first.wait_for(timeout=timeout)
        print(f"✅ Элемент '{text}' появился")
    except:
        print(f"❌ Элемент с текстом '{text}' не появился за {timeout} мс")
        return None

    element = await page.locator(f"text={text}").first.element_handle()
    if not element:
        print("❌ Не удалось получить element_handle()")
        return None

    class_name = await element.evaluate(f'''(el) => {{
        let parent = el;
        for (let i = 0; i < {levels_up}; i++) {{
            if (!parent.parentElement) break;
            parent = parent.parentElement;
        }}
        return parent.className;
    }}''')

    print(f"📦 Класс родителя на {levels_up} уровне: {class_name}")
    return class_name


async def parse_reviews_by_container_class(page, container_class: str, max_count: int | None = None) -> list[dict]:
    reviews = page.locator(f'div.{container_class}')
    count = await reviews.count()
    print(f"🔎 Найдено {count} отзывов с классом '{container_class}'")

    if max_count is not None:
        count = min(count, max_count)

    result = []
    for i in range(count):
        block = reviews.nth(i)

        # Автор
        author = await block.locator('._16s5yj36').first.get_attribute('title') or ""

        # Дата
        date = await block.locator('._a5f6uz').first.text_content() or ""
        date = parse_russian_date(date)

        # Текст отзыва — проверяем наличие
        text = ""
        text_locator = block.locator('a._1msln3t, a._1wlx08h')  # оба класса на всякий случай
        if await text_locator.count() > 0:
            text = await text_locator.first.text_content() or ""

        # Оценка по количеству жёлтых звёзд
        stars = await block.locator('._1fkin5c svg[fill="#ffb81c"]').count()

        # Ответ от компании — если есть
        reply_locator = block.locator('._1wk3bjs')
        reply = await reply_locator.first.text_content() if await reply_locator.count() > 0 else None

        # Лайки — если есть
        likes = 0
        likes_locator = block.locator('._11fxohc span')
        if await likes_locator.count() > 0:
            likes_text = await likes_locator.first.text_content()
            if likes_text and likes_text.strip().isdigit():
                likes = int(likes_text.strip())

        result.append({
            "author": author.strip(),
            "date": date.strip(),
            "content": text.strip(),
            "stars": stars,
            "reply": reply.strip() if reply else None,
            "likes": likes,
            "url": "https://2gis.kz/reviews/70000001066969314"

        })

    return result


async def load_all_reviews_until_no_more_button(page, container_class: str, button_locator):
    previous_count = 0

    while True:
        current_count = await page.locator(f'div.{container_class}').count()

        if button_locator is None or await button_locator.count() == 0:
            print("🛑 Кнопка 'Загрузить ещё' не найдена")
            break

        if current_count == previous_count:
            print("🟡 Количество отзывов не увеличивается — возможно, всё загружено")
            break

        previous_count = current_count

        try:
            await button_locator.click(force=True)
            print("🖱️ Кнопка 'Загрузить ещё' нажата")
        except Exception as e:
            print(f"⚠️ Ошибка при клике по кнопке: {e}")
            break

        await page.wait_for_timeout(2000)


async def main(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        print("🌐 Страница загружена")
        xpath_for_href = await find_xpath_by_href(page, "/tab/reviews")
        await click_by_xpath(page, xpath_for_href)

        container_class = await get_parent_class_by_text(page, "Полезно?", levels_up=8)
        more_button_class = await find_load_more_button(page)
        await load_all_reviews_until_no_more_button(page, container_class, more_button_class)

        if container_class:
            reviews = await parse_reviews_by_container_class(page, container_class)
            save_reviews_to_json(reviews)
            for idx, r in enumerate(reviews, 1):
                print(f"\n📦 Отзыв #{idx}")
                for k, v in r.items():
                    print(f"{k}: {v}")


import asyncio
import json

MONTHS_RU = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
}


def parse_russian_date(date_str: str) -> str:
    # Удаляем запятую и "отредактирован"
    cleaned = date_str.replace(", отредактирован", "").strip()

    # Разбиваем строку
    parts = cleaned.split()
    if len(parts) != 3:
        return None

    day, month_rus, year = parts
    month = MONTHS_RU.get(month_rus.lower())

    if not month:
        return None

    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def save_reviews_to_json(reviews: list[dict], filename: str = "reviews.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    print(f"💾 Отзывы сохранены в {filename}")

if __name__ == "__main__":
    url = "https://2gis.kz/almaty/search/Top%20Tier/page/1/firm/70000001066969314/57.19912,50.280214?m=65.495135,44.841596/6.35"
    xpath = asyncio.run(main(url))
    print(f"📍 XPATH ссылки на отзывы: {xpath}")
