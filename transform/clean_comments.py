import re

def clean_comments(comments: list[dict]) -> list[dict]:
    cleaned = []
    for comment in comments:
        text = comment.get("content", "")
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"@\w+", "", text)
        text = re.sub(r"[^\w\s]", "", text)
        cleaned.append({
            "content": text.strip(),
            "video_url": comment.get("video_url", "")
        })
    return cleaned
