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

class QuestionRequest(BaseModel):
    subject: str
    topic: str
    difficulty: str

def load_question_data():
    try:
        with open("gisa_questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {str(e)}")
        return {}

def find_example_questions(data, subject, topic, difficulty):
    """선택된 과목, 토픽, 난이도에 맞는 예시 문제들을 찾음"""
    examples = []
    
    if subject in data and topic in data[subject]["topics"]:
        sets = data[subject]["topics"][topic]["sets"]
        for set_data in sets:
            if set_data["example"]["difficulty"] == difficulty:
                examples.append(set_data["example"])
    
    return examples

def format_example_questions(examples):
    """예시 문제들을 프롬프트용 텍스트로 변환"""
    if not examples:
        return "선택한 난이도의 예시 문제가 없습니다."
    
    formatted = "예시 문제들:\n\n"
    for i, example in enumerate(examples, 1):
        formatted += f"예시 {i})\n"
        formatted += f"문제: {example['question']}\n"
        formatted += "보기:\n"
        for j, option in enumerate(example['options'], 1):
            formatted += f"①{option}\n"
        formatted += f"정답: {example['answer']}\n"
        formatted += f"해설: {example['explanation']}\n\n"
    
    return formatted

# 문제 생성 템플릿 수정
exam_template = PromptTemplate(
    input_variables=["subject_name", "topic", "difficulty", "examples"],
    template="""
    정보처리기사 {subject_name}의 {topic} 관련 {difficulty}난이도 문제를 생성해주세요.

    {examples}

    위 예시들을 참고하여 비슷한 난이도와 형식으로 새로운 문제를 생성해주세요.
    생성할 때는 다음 형식을 지켜주세요:
    
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
@app.get("/get-topics")
async def get_topics():
    """JSON 파일에서 과목별 토픽 정보를 가져옴"""
    question_data = load_question_data()
    return question_data


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-question")
async def generate_question(request: QuestionRequest):
    # 데이터 로드
    question_data = load_question_data()
    
    # 과목명 가져오기
    subject_name = question_data[request.subject]["name"]
    
    # 예시 문제 찾기
    examples = find_example_questions(
        question_data, 
        request.subject, 
        request.topic,
        request.difficulty
    )
    
    # 예시 문제 포맷팅
    formatted_examples = format_example_questions(examples)
    
    # ChatGPT 초기화
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)
    
    # 프롬프트 생성
    prompt = exam_template.format(
        subject_name=subject_name,
        topic=request.topic,
        difficulty=request.difficulty,
        examples=formatted_examples
    )

    # LLM에 프롬프트 전달
    response = llm.invoke(prompt)
    
    # 응답 파싱
    content = response.content
    parts = content.split("[문제]")[1].split("[보기]")
    question = parts[0].strip()
    
    options_and_rest = parts[1].split("[정답]")
    options = [opt.strip() for opt in options_and_rest[0].strip().split("\n") if opt.strip()]
    
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)