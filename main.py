import requests
import json
import schedule
import os
import logging
import time

# 로그 기본 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 환경변수에서 읽기
TOKEN = os.getenv("TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

DB_FILE = "./sample_db.json"

def send_embedded_message(title, description, url, color, fields, author_name):
    """
    디스코드 웹훅에 임베드 메시지 전송 함수
    """
    # 색상은 16진수 문자열 -> 10진수 변환
    color_int = int(color, 16) if isinstance(color, str) else color

    embed = {
        "title": title,
        "description": description,
        "url": url,
        "color": color_int,
        "fields": fields,
        "author": {
            "name": author_name
        },
        "footer": {
            "text": "Notion to Discord Webhook Bot"
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }

    data = {
        "embeds": [embed]
    }

    try:
        res = requests.post(WEBHOOK_URL, json=data)
        if res.status_code == 204:
            logging.info(f"Discord webhook message sent: {title}")
        else:
            logging.error(f"Failed to send webhook message: {res.status_code}, {res.text}")
    except Exception as e:
        logging.error(f"Exception sending webhook: {e}")

def read_database(database_id, headers):
    read_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    logging.info(f"Requesting Notion database at URL: {read_url}")
    try:
        res = requests.post(read_url, headers=headers, json={})
        logging.info(f"Response Status: {res.status_code}")
        if res.status_code != 200:
            logging.error(f"Failed to read database. Response Text: {res.text}")
            return {}
        try:
            data = res.json()
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response: {e}")
            return {}
        return data
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return {}

def get_author_name_from_properties(props):
    author_prop = props.get("생성자")
    if author_prop:
        if author_prop.get("type") == "created_by":
            created_by = author_prop.get("created_by")
            if created_by and isinstance(created_by, dict):
                name = created_by.get("name")
                if name:
                    return name
        elif author_prop.get("type") == "people":
            people = author_prop.get("people", [])
            if people:
                return people[0].get("name", "Unknown")
    return "Unknown"

def get_author_name(task):
    created_by = task.get("created_by")
    if isinstance(created_by, dict):
        name = created_by.get("name")
        if name:
            return name
    elif isinstance(created_by, list):
        if len(created_by) > 0 and isinstance(created_by[0], dict):
            return created_by[0].get("name", "Unknown")
    logging.info(f"created_by 필드가 dict나 list가 아님 또는 빈 값: {created_by}")
    return "Unknown"

def get_data(data):
    tasks = data.get("results", [])
    sample_db = {}

    for task in tasks:
        props = task.get("properties", {})

        author_name = get_author_name_from_properties(props)
        if author_name == "Unknown":
            author_name = get_author_name(task)

        submit = props.get("Submit", {})
        status = props.get("Status", {})
        task_reminder = props.get("Task Reminder", {})
        title_prop = props.get("Name", None)

        checkbox = submit.get("checkbox", False)
        status_name = status.get("status", {}).get("name", "No Status")
        task_reminder_str = task_reminder.get("formula", {}).get("string", "")
        url = task.get("url", "")
        title_text = ""
        if title_prop and "title" in title_prop and len(title_prop["title"]) > 0:
            title_text = title_prop["title"][0].get("plain_text", "")

        sample_db[task["id"]] = {
            "checkbox": checkbox,
            "status": status_name,
            "Task Reminder": task_reminder_str,
            "url": url,
            "title": title_text,
            "created_by": author_name,
        }

    return sample_db

def check_db(old_data, new_data):
    for task_id in new_data.keys():
        task = new_data[task_id]
        fields = [
            {"name": "Task", "value": task["title"]},
            {"name": "Task Reminder", "value": task["Task Reminder"]},
            {"name": "Status", "value": task["status"]},
        ]
        author = task.get("created_by", "Unknown")

        if task_id not in old_data:
            logging.info(f"New Task detected: {task['title']}")
            send_embedded_message(
               title="새 페이지가 생성되었습니다! 👀",
               description="노션에 새 페이지가 생성 되었어요!",
               url=task["url"],
               color="00AAFF",
               fields=fields,
               author_name=author
            )
        # 수정사항 알림은 제거했습니다.

def main():
    logging.info("Starting main check function.")
    current_db = get_data(read_database(DATABASE_ID, HEADERS))

    try:
        with open(DB_FILE, "r", encoding="utf8") as f:
            old_db = json.load(f)
        logging.info("Old database loaded successfully.")
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        old_db = {}
        logging.warning("Old database file not found or corrupted. Starting fresh.")

    check_db(old_db, current_db)

    if old_db != current_db:
        with open(DB_FILE, "w", encoding="utf8") as f:
            json.dump(current_db, f, ensure_ascii=False, indent=4)
        logging.info("Database file updated successfully.")
    else:
        logging.info("No changes detected. Database file not updated.")

    logging.info("Main check function completed.")

if __name__ == "__main__":
    logging.info("Scheduler started: running main() every 1 minute.")
    schedule.every(1).minutes.do(main)

    while True:
        schedule.run_pending()
        time.sleep(1)
