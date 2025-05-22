import requests
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 불러오기
load_dotenv()

TOKEN = os.getenv("TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# 요청 헤더 구성
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Notion Database 조회 URL
url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

# POST 요청 전송
response = requests.post(url, headers=HEADERS)

# 응답 상태 코드와 JSON 결과 출력
print("Status Code:", response.status_code)
try:
    print("Response JSON:", response.json())
except Exception as e:
    print("Response could not be parsed as JSON:", e)
