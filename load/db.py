import sqlite3

DB_PATH = "comments.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            author TEXT,
            date TEXT,
            likes INTEGER,
            video_url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            views TEXT,
            description TEXT,
            date INTEGER,
            author TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_comments(comments: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    data = [(c["content"], c["author"], c["date"], c["likes"], c["video_url"]) for c in comments]
    cursor.executemany("""
        INSERT INTO comments (content, author, date, likes, video_url)
        VALUES (?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()



def save_video_urls(videos: list[dict]):
    """
    videos: [{'url': ..., 'views': ..., 'description': ..., 'date': ..., 'author': ...}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for video in videos:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO video_urls (url, views, description, date, author)
                VALUES (?, ?, ?, ?, ?)
            """, (
                video.get("url"),
                video.get("views"),
                video.get("description"),
                video.get("date"),
                video.get("author"),
            ))
        except Exception as e:
            print("❌ Ошибка при сохранении видео:", e)

    conn.commit()
    conn.close()


def get_video_urls() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM video_urls order by id ASC")
    urls = [row[0] for row in cursor.fetchall()]
    conn.close()
    print(urls)
    return urls
