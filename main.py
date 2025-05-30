import requests
import json
import schedule
from discord import send_embedded_message
# from dotenv import load_dotenv
import os
import logging
import time

# 로그 기본 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# env 파일 로드
# load_dotenv(dotenv_path="C:/Users/Developer/Downloads/GitClone/Notion-Discord-Webhook/.env")

# Notion API token and database ID
TOKEN = os.getenv("TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

logging.info(f"DATABASE_ID: {DATABASE_ID}")
logging.info(f"TOKEN: {TOKEN}")

# Headers for API requests
HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# File to store a copy of the database
DB_FILE = "./sample_db.json"

# Read the database with the given ID and headers
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
        # 'type'이 'created_by'일 때 작성자 정보가 'created_by' 키 안에 있음
        if author_prop.get("type") == "created_by":
            created_by = author_prop.get("created_by")
            if created_by and isinstance(created_by, dict):
                name = created_by.get("name")
                if name:
                    return name
        # 기존 people 타입 처리 (혹시 혼용된 경우를 대비)
        elif author_prop.get("type") == "people":
            people = author_prop.get("people", [])
            if people:
                return people[0].get("name", "Unknown")
    return "Unknown"

# 작성자 이름 가져오기 (created_by 우선, 없으면 properties 내부 people 타입 필드 탐색)
# 작성자 이름을 task 메타 데이터의 created_by 필드에서 시도 (dict 또는 list 모두 처리)
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

# Extract certain properties from the database
def get_data(data):
    tasks = data.get("results", [])
    sample_db = {}

    for task in tasks:
        props = task.get("properties", {})

        # 1순위: properties 내 '생성자' 프로퍼티에서 작성자 이름 시도
        author_name = get_author_name_from_properties(props)

        # 2순위: 없으면 created_by 메타 데이터에서 시도
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

# Compare two copies of the database and check if the status of any tasks has changed
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
               title="기본 제목",  # fallback 제목 (fields에 Task가 없으면 이걸 씀)
               description="노션에 새 페이지가 생성 되었어요! 👀",  # 부가 메시지
               url=task["url"],  # 페이지 링크
               color="00AAFF",
               fields=fields,  # Notion에서 받아온 필드 리스트
               author_name=author  # 작성자 이름
            )
        else:
            old_task = old_data[task_id]
            if task != old_task:
                logging.info(f"Task status changed: {task['title']}")

                if "Approved" in task["status"] and "Approved" not in old_task["status"]:
                    send_embedded_message(
                        title="Approved",
                        description="작업이 승인되었어요! ✅",
                        url=task["url"],
                        color="008930",
                        fields=fields,
                        author_name=author
                    )
                elif "Rejected" in task["status"]:
                    if task["checkbox"] and not old_task["checkbox"]:
                        send_embedded_message(
                            title="Rejected Task",
                            description="작업이 반려되었어요 ❌",
                            url=task["url"],
                            color="FF0000",
                            fields=fields,
                            author_name=author
                        )
                else:
                    if task["checkbox"] and not old_task["checkbox"]:
                        send_embedded_message(
                            title="Task in Review",
                            description="작업이 검토 중입니다 🧐",
                            url=task["url"],
                            color="FFA500",
                            fields=fields,
                            author_name=author
                        )


# Main function to check if the database has changed
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
    schedule.every(1).minutes.do(main)  # 1분마다 실행

    while True:
        schedule.run_pending()
        time.sleep(1)  # CPU 과다 사용 방지용으로 1초씩 슬립 추가 권장