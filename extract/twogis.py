from typing import Any

import dateparser
from playwright.async_api import Locator, Page

from manager import manager

MAIN_BLOCK = "/html/body/div[2]/div/div/div[1]/div[1]/div[3]/div[2]/div/div/div/div/div[2]/div[2]/div/div[1]/div/div/div/div/div[2]"
items_count_path = "".join(
    (
        MAIN_BLOCK,
        "/div[{items_count_div_index}]/div[2]/div/div/div[1]/div[{item_index}]/h2/a/span",
    )
)


async def get_comment_items(comment_block: Locator) -> dict[str, Any]:
    print("📦 Получаем комментарий...")
    await comment_block.scroll_into_view_if_needed()

    comment_author = await comment_block.locator(
        "xpath=div/div/div/div[2]/span/span[1]/span"
    ).text_content()
    print(f"👤 Автор: {comment_author}")

    text_div = await comment_block.locator("xpath=div").count()
    comment_text = await comment_block.locator(
        f"xpath=div[{text_div}]/div[2]/a"
    ).text_content()
    print(f"💬 Текст: {comment_text}")

    commented_at = await comment_block.locator(
        "xpath=/div[1]/div/div[1]/div[2]/div"
    ).text_content()
    print(f"🕒 Время: {commented_at}")

    if commented_at:
        commented_at = dateparser.parse(commented_at, languages=["ru", "en"])

    return {
        "comment_author": comment_author or "",
        "comment_text": comment_text or "",
        "commented_at": commented_at,
    }


async def get_next_page(page: Page, block: Locator, loaded: int) -> int:
    print("🔄 Загружаем следующую страницу...")
    await page.wait_for_timeout(1000)

    await (await block.element_handle()).evaluate(
        "el => el.scrollTo(0, 100000000000000000000)"
    )
    print("📜 Прокрутили вниз")

    last = block.locator("xpath=div").nth(loaded - 1)
    await last.scroll_into_view_if_needed()
    await page.wait_for_timeout(500)

    new_loaded = await block.locator("xpath=div").count()
    print(f"📦 Было загружено: {loaded}, Стало: {new_loaded}")
    await page.wait_for_timeout(500)
    return new_loaded


async def search_2gis_comments(url: str, max_comments_count: int = 20):
    print(f"🔍 Начинаем поиск комментариев по ссылке: {url}")
    res = []
    parts = url.split("?")
    url = "".join((parts[0], "/tab/reviews?", parts[1] if len(parts) > 1 else ""))
    print(f"🧭 Перенаправлено на: {url}")

    page = await manager.get_page()
    try:
        await page.goto(url)
        print("🌐 Страница загружена")

        block = page.locator(f"xpath={MAIN_BLOCK}")
        main_block_index = await block.locator("xpath=div").count()
        print(f"🔢 Индекс основного блока: {main_block_index}")

        block = block.locator(f"xpath=div[{main_block_index}]")

        item_index = 0
        items_text = ""
        category_count = await page.locator(
            f"xpath={MAIN_BLOCK}/div[{main_block_index - 1}]/div[2]/div/div/div[1]/div"
        ).count()
        print(f"📊 Количество категорий: {category_count}")

        while category_count > item_index:
            item_index += 1
            it = "/".join(items_count_path.split("/")[:-1])
            items_text = await page.locator(
                f"xpath={it.format(items_count_div_index=main_block_index - 1, item_index=item_index)}"
            ).text_content()

            print(f"📝 Категория {item_index}: {items_text}")
            if not items_text:
                print("❌ items_text пустой")
                return []
            if "Отзывы" in items_text:
                span_count = await page.locator(
                    f"xpath={it.format(items_count_div_index=main_block_index - 1, item_index=item_index)}"
                ).locator("xpath=span").count()
                print(f"📎 span count: {span_count}")
                if span_count == 0:
                    print("❌ Отзывы есть, но span пустой")
                    return []
                break
        else:
            print("❌ Не найдены блоки отзывов")
            return []

        item_count_str = await page.locator(
            f"xpath={items_count_path.format(items_count_div_index=main_block_index - 1, item_index=item_index)}"
        ).text_content()
        items_count = int(c if (c := item_count_str) else 0)
        print(f"🔢 Всего отзывов: {items_count}")

        comments_count = 0
        i = 1
        loaded = await block.locator("xpath=div").count()
        print(f"🚚 Начальная загрузка блоков: {loaded}")

        while comments_count < max_comments_count and items_count > comments_count:
            if i > loaded:
                print(f"📥 Нужно загрузить больше, i={i}, loaded={loaded}")
                loaded = await get_next_page(page=page, block=block, loaded=loaded)

            maybe_comment_block = block.locator(f"xpath=div[{i}]")
            div_count = await maybe_comment_block.locator(
                "xpath=div[1]/div[1]/div[1]/div[1]/div"
            ).count()
            print(f"🔎 div[{i}]: вложенных блоков: {div_count}")

            if div_count > 0:
                comment = await get_comment_items(maybe_comment_block)
                comment["url"] = url
                res.append(comment)
                comments_count += 1
                print(f"✅ Получено {comments_count} / {max_comments_count}")

            i += 1
        print("✅ Все комментарии:", res)
        return res
    finally:
        print("🧹 Закрытие страницы")
        await page.close()
