import requests
import json
import os
from datetime import datetime, timedelta, timezone
# from dotenv import load_dotenv

# load_dotenv()

TOKEN = os.environ["TOKEN"]
DATABASE_ID = os.environ["DATABASE_ID"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_unprocessed_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    payload = {
        "filter": {
            "property": "notified",
            "checkbox": {
                "equals": False
            }
        }
    }

    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    return res.json()["results"]

def mark_as_processed(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "notified": {
                "checkbox": True
            }
        }
    }

    res = requests.patch(url, headers=headers, json=payload)
    res.raise_for_status()

def send_to_discord(page):
    
    title = page["properties"]["이름"]["title"][0]["plain_text"]
    url = page["url"]
    created = page["created_time"]
    page_id = page["id"]

    embed = {
        "title": f"새로운 페이지 : {title}",
        "description": f"[페이지 열기]({url})",
        "color": 0x00ffcc,
        "timestamp": created
    }

    data = {
        "embeds": [embed]
    }
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        response.raise_for_status()
        mark_as_processed(page_id)
    except requests.exceptions.RequestException as e:
        print(f"❌ Discord 전송 실패: {e}")

def send_next_update_notice():
    next_update = datetime.now(timezone.utc) + timedelta(minutes=10)
    next_update_kst = next_update.astimezone(timezone(timedelta(hours=9)))  # KST (UTC+9)
    embed = {
        "title": "페이지 업데이트 알림",
        "description": f"다음 업데이트 예상 시간 :{next_update_kst.strftime('%Y-%m-%d %H:%M:%S')}",
        "color": 0x00ffcc,
    }

    data = {
        "embeds": [embed]
    }
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 알림 전송 실패: {e}")
     
if __name__ == "__main__":
    new_pages = get_unprocessed_pages()
    print(f"🧾 Found {len(new_pages)} new pages.")

    cnt = 0
    for page in new_pages:
        send_to_discord(page)
        print(f"✅ Sent: {page['url']}")
        cnt += 1

    if cnt != 0:
        send_next_update_notice()