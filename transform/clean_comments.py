import re

def clean_comments(comments: list[str]) -> list[str]:
    cleaned = []
    for comment in comments:
        comment = re.sub(r"http\S+", "", comment)
        comment = re.sub(r"@\w+", "", comment)
        comment = re.sub(r"[^\w\s]", "", comment)
        cleaned.append(comment.strip())
    return cleaned
