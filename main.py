from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json
import random
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


# JSON 데이터 로드
def load_question_data():
    try:
        with open("gisa_questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {str(e)}")
        return {}


question_data = load_question_data()

# ChatOpenAI 모델 초기화
llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7)

# 문제 생성 템플릿
exam_template = PromptTemplate(
    input_variables=[
        "subject",
        "subject_name",
        "topic",
        "difficulty",
        "reference",
        "example",
    ],
    template="""
    정보처리기사 {subject}과목({subject_name})의 {topic} 관련 {difficulty}난이도 문제를 생성해주세요.

    {reference}

    예시 문제:
    {example}

    위 내용을 참고하여 새로운 문제를 다음 형식으로 생성해주세요:
    
    ##[문제]
    
    ##[보기]
    ① 
    ② 
    ③ 
    ④ 
    
    ##[정답]
    
    ##[해설]
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

    # 참고 내용과 예시 문제 찾기
    reference_text = ""
    example_text = ""

    if request.subject in question_data:
        subject_data = question_data[request.subject]
        if request.topic in subject_data["topics"]:
            topic_sets = subject_data["topics"][request.topic]["sets"]
            if topic_sets:
                # 난이도에 맞는 세트 찾기
                matching_sets = [
                    s
                    for s in topic_sets
                    if s["example"]["difficulty"] == request.difficulty
                ]
                if matching_sets:  # 매칭되는 세트가 있는 경우에만 선택
                    selected_set = random.choice(matching_sets)

                reference_text = (
                    "참고 내용:\n" + selected_set["reference"]
                    if selected_set["reference"]
                    else ""
                )
                example_text = f"""
난이도: {selected_set['example']['difficulty']}
문제: {selected_set['example']['question']}
보기:
{''.join(f'①{selected_set["example"]["options"][0]}' if len(selected_set["example"]["options"]) > 0 else '')}
{''.join(f'②{selected_set["example"]["options"][1]}' if len(selected_set["example"]["options"]) > 1 else '')}
{''.join(f'③{selected_set["example"]["options"][2]}' if len(selected_set["example"]["options"]) > 2 else '')}
{''.join(f'④{selected_set["example"]["options"][3]}' if len(selected_set["example"]["options"]) > 3 else '')}
정답: {selected_set['example']['answer']}
해설: {selected_set['example']['explanation']}
"""

    # 프롬프트 생성
    prompt = exam_template.format(
        subject=request.subject,
        subject_name=subject_name,
        topic=request.topic,
        difficulty=request.difficulty,
        reference=reference_text if reference_text else "참고 내용이 없습니다.",
        example=example_text if example_text else "예시 문제가 없습니다.",
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
