import os
import requests
# from dotenv import load_dotenv

# load_dotenv()  # .env 파일에서 WEBHOOK_URL 변수 로드

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # 하나로 통합

def send_embedded_message(title, description, url, color, fields, author_name=None):
    # 필드 중 Task만 페이지 제목으로 추출, 나머지는 필터링
    page_title = ""
    filtered_fields = []

    for field in fields:
        name = field.get("name")
        value = field.get("value")

        if name == "Task":
            page_title = value
            continue

        if name == "Status" and value == "No Status":
            continue

        if name == "Task Reminder" and (value is None or value.strip() == ""):
            continue

        filtered_fields.append(field)

    # embed의 title에 페이지 제목 넣기 -> 글씨 크게 굵게 표시됨
    embed_title = f"{page_title} 🔗" if page_title else title

    # description에는 부가 문구만 넣기
    embed_description = description or "노션에 새 페이지가 생성 되었어요! 👀"

    embed = {
        "title": embed_title,
        "description": embed_description,
        "url": url,
        "color": int(color, 16),
        "fields": filtered_fields,
    }

    if author_name:
        embed["author"] = {"name": author_name}

    data = {"embeds": [embed]}

    # 'Approved' 단어 포함 여부에 따라 다른 웹훅으로 전송
    requests.post(WEBHOOK_URL, json=data)  # 항상 동일한 웹훅에 전송