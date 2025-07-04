import asyncio
from datetime import datetime, timedelta

from manager import manager  # это твой PlaywrightManager


def parse_relative_or_absolute_date(date_str):
    now = datetime.now()
    try:
        if "дн." in date_str:
            days = int(re.search(r"(\d+)", date_str).group(1))
            return int((now - timedelta(days=days)).timestamp())
        elif "ч." in date_str:
            hours = int(re.search(r"(\d+)", date_str).group(1))
            return int((now - timedelta(hours=hours)).timestamp())
        elif "нед." in date_str:
            weeks = int(re.search(r"(\d+)", date_str).group(1))
            return int((now - timedelta(weeks=weeks)).timestamp())
    except:
        pass
    return None


async def get_all_video_urls(username: str) -> list[dict]:
    page = await manager.get_page()

    profile_url = f"https://www.tiktok.com/@{username}"
    await page.goto(profile_url)
    await page.wait_for_selector('a[href*="/video/"]', timeout=60000)

    previous_height = 0
    for _ in range(100):  # ограничение по количеству скроллов
        current_height = await page.evaluate('document.body.scrollHeight')
        if current_height == previous_height:
            break
        previous_height = current_height
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(1500)

    anchors = await page.query_selector_all('a[href*="/video/"]')
    seen = set()
    results = []

    for anchor in anchors:
        href = await anchor.get_attribute("href")
        if not href or href in seen:
            continue
        seen.add(href)

        container = await anchor.evaluate_handle("el => el.closest('div[class*=\"DivItemContainerV2\"]')")
        if not container:
            continue

        # Просмотры
        views_el = await container.query_selector('strong[data-e2e="video-views"]')
        views = await views_el.inner_text() if views_el else None

        # Описание
        img_el = await container.query_selector("img[alt]")
        description = await img_el.get_attribute("alt") if img_el else None

        # Дата (не доступна на preview, только внутри видео, можно позже дорасширить)
        date = None

        results.append({
            "url": href,
            "views": views,
            "description": description,
            "date": date,
            "author": username,
        })

    await page.close()
    return results


import re


async def get_video_metrics(page) -> dict:
    def extract_number(text):
        return int(re.search(r'\d+', text.replace(' ', '')).group()) if text else 0

    metrics = {"comments": 0, "likes": 0, "shares": 0}

    try:
        comments_text = await page.inner_text('strong[data-e2e="comment-count"]')
        likes_text = await page.inner_text('strong[data-e2e="like-count"]')
        shares_text = await page.inner_text('strong[data-e2e="share-count"]')

        metrics["comments"] = extract_number(comments_text)
        metrics["likes"] = extract_number(likes_text)
        metrics["shares"] = extract_number(shares_text)

        print(f"📊 Метрики: 💬 {metrics['comments']}  ❤️ {metrics['likes']}  🔁 {metrics['shares']}")

    except Exception as e:
        print(f"⚠️ Не удалось извлечь метрики: {e}")

    return metrics

async def get_comments(video_url: str) -> list[dict]:
    print(f"🌐 Открываем страницу: {video_url}")
    page = await manager.get_page()

    try:
        await page.goto(video_url)
        print("✅ Страница загружена")

        print("📊 Извлекаем метрики видео...")
        metrics = await get_video_metrics(page)
        if metrics["comments"] == 0:
            print("0 комментариев")
            return []
        print(f"🎯 Метрики: {metrics}")
        target_count = int(metrics["comments"] * 0.9)
        print(f"🧮 Цель: собрать {target_count} комментариев")

        print("⏳ Ждём загрузки первых комментариев...")
        await page.wait_for_selector('div.css-13wx63w-DivCommentObjectWrapper', timeout=30000)
        print("✅ Комментарии появились на странице")

        comments = []
        seen_texts = set()
        prev_count = 0
        iteration = 0

        while True:
            iteration += 1
            print(f"🔁 Скролл #{iteration}...")

            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(5)

            # 🕐 Ждём возможный лоадер
            try:
                print("⏳ Проверка наличия лоадера...")
                await page.wait_for_selector("div.eps6g9r0", timeout=5000)
                print("⏳ Лоадер найден, ждём завершения загрузки...")
                await page.wait_for_selector("div.eps6g9r0", state="hidden", timeout=10000)
                print("✅ Лоадер исчез")
            except Exception:
                print("⚠️ Лоадер не найден — продолжаем")

            print("🔎 Ищем элементы комментариев...")
            elements = await page.query_selector_all('div.css-13wx63w-DivCommentObjectWrapper')
            print(f"🔍 Найдено элементов: {len(elements)}")

            for el in elements:
                try:
                    # 💬 Текст комментария
                    text_el = await el.query_selector('span[data-e2e^="comment-level-"] p')
                    text = (await text_el.inner_text()).strip() if text_el else None
                    if not text or text in seen_texts:
                        continue
                    seen_texts.add(text)

                    # 👤 Автор
                    author_el = await el.query_selector('div[data-e2e^="comment-username-"] a p')
                    author = (await author_el.inner_text()).strip() if author_el else None

                    # 🕒 Дата
                    date = None
                    try:
                        date_span_elements = await el.query_selector_all(
                            'div.css-1lglotn-DivCommentSubContentWrapper span')
                        if date_span_elements:
                            date = (await date_span_elements[0].inner_text()).strip()
                    except Exception as date_err:
                        print(f"⚠️ Ошибка при извлечении даты: {date_err}")

                    # ❤️ Лайки
                    like_el = await el.query_selector('div.edeod5e0 span')
                    likes = (await like_el.inner_text()).strip() if like_el else "0"

                    comments.append({
                        "content": text,
                        "author": author,
                        "date": date,
                        "likes": likes,
                        "video_url": video_url,
                    })

                except Exception as el_err:
                    print(f"⚠️ Ошибка при парсинге комментария: {el_err}")

            print(f"💬 Собрано комментариев: {len(comments)} / {metrics['comments']}")

            # ✅ Условие выхода
            current_count = len(comments)
            if current_count >= target_count:
                print("🎯 Цель достигнута — достаточно комментариев")
                break
            if current_count == prev_count:
                print("⚠️ Количество не увеличилось — возможно достигнут конец")
                break
            prev_count = current_count

    except Exception as e:
        print(f"❌ Ошибка при получении комментариев для {video_url}: {e}")
        print("🧩 Возможно, CAPTCHA заблокировала страницу?")
        comments = []

    finally:
        print("🧹 Закрываем страницу")
        await page.close()

    print(f"✅ Всего комментариев собрано: {len(comments)}\n")
    return comments
