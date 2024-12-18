from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import uvicorn

# API KEY 정보로드
load_dotenv()

app = FastAPI()

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 과목 정보 매핑
SUBJECTS = {
    "1": "소프트웨어 설계",
    "2": "소프트웨어 개발",
    "3": "데이터베이스 구축",
    "4": "프로그래밍 언어 활용",
    "5": "정보시스템 구축 관리",
}

# ChatOpenAI 모델 초기화
llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7)

# 간단한 문제 생성 템플릿
exam_template = PromptTemplate(
    input_variables=["subject", "subject_name", "topic", "difficulty"],
    template="""
    정보처리기사 {subject}과목({subject_name})의 {topic} 관련 {difficulty}난이도 문제를 다음 형식으로 생성해주세요.
    문제는 실제 정보처리기사 시험 수준에 맞게 출제해주세요.

    [문제]
    
    [보기]
    ① 
    ② 
    ③ 
    ④ 
    
    [정답]
    
    [해설]
    각 보기를 하나씩 설명하고 왜 해당 답이 정답인지 명확하게 설명해주세요.
    """,
)


class QuestionRequest(BaseModel):
    subject: str
    topic: str
    difficulty: str


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate-question")
async def generate_question(request: QuestionRequest):
    subject_name = SUBJECTS.get(request.subject, "")

    # 프롬프트 생성
    prompt = exam_template.format(
        subject=request.subject,
        subject_name=subject_name,
        topic=request.topic,
        difficulty=request.difficulty,
    )

    # LLM에 프롬프트 전달
    response = llm.invoke(prompt)

    # 응답 파싱
    content = response.content
    parts = content.split("[문제]")[1].split("[보기]")
    question = parts[0].strip()

    options_and_rest = parts[1].split("[정답]")
    options = [
        opt.strip() for opt in options_and_rest[0].strip().split("\n") if opt.strip()
    ]

    answer_and_explanation = options_and_rest[1].split("[해설]")
    answer = answer_and_explanation[0].strip()
    explanation = answer_and_explanation[1].strip()

    return {
        "question": question,
        "options": options,
        "answer": answer,
        "explanation": explanation,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8800)
