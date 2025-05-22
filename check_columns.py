import requests
import os
from dotenv import load_dotenv

# .env 파일 경로에 맞게 수정
load_dotenv(dotenv_path="C:/Users/Developer/Downloads/GitClone/Notion-Discord-Webhook/.env")

TOKEN = os.getenv("TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def read_database(database_id, headers):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=headers, json={})
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    return response.json()

def print_column_names(data):
    if not data or "results" not in data or len(data["results"]) == 0:
        print("No data or empty results")
        return
    first_page = data["results"][0]
    properties = first_page.get("properties", {})
    print("데이터베이스 컬럼명 목록:")
    for col_name in properties.keys():
        print("-", col_name)

if __name__ == "__main__":
    data = read_database(DATABASE_ID, HEADERS)
    print_column_names(data)