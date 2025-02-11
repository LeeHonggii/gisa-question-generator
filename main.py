from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json
import os
import uvicorn

# API KEY 정보로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

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
    """모든 난이도의 예시 문제를 찾되, 선택된 난이도를 마지막에 배치하고 랜덤하게 선택"""
    import random  # 함수 상단에 추가
    
    examples = []
    difficulties = ["하", "중", "상"]
    available_difficulties = set()
    
    if subject in data and topic in data[subject]["topics"]:
        sets = data[subject]["topics"][topic]["sets"]
        # 각 난이도별로 문제 선택
        for diff in difficulties:
            diff_examples = [s["example"] for s in sets if s["example"]["difficulty"] == diff]
            if diff_examples:
                # 해당 난이도의 문제들 중 랜덤하게 하나 선택
                selected_example = random.choice(diff_examples)
                examples.append(selected_example)
                available_difficulties.add(diff)
    
    return examples, available_difficulties

def format_example_questions(examples, target_difficulty, available_difficulties):
    """예시 문제들을 난이도 표시와 함께 프롬프트용 텍스트로 변환"""
    if not examples:
        return "예시 문제가 없습니다."
    
    formatted = "예시 문제들:\n\n"
    for i, example in enumerate(examples, 1):
        formatted += f"[난이도: {example['difficulty']}]\n"
        formatted += f"문제: {example['question']}\n"
        formatted += "보기:\n"
        for j, option in enumerate(example['options'][:4], 1):
            marker = ['①', '②', '③', '④'][j-1]
            formatted += f"{marker} {option}\n"
        formatted += f"정답: {example['answer']}\n"
        formatted += f"해설: {example['explanation']}\n\n"
    
    # 누락된 난이도 메시지 추가
    missing_difficulties = set(["하", "중", "상"]) - available_difficulties
    if missing_difficulties:
        missing_msg = ", ".join(sorted(missing_difficulties))
        formatted += f"\n※ {missing_msg} 난이도의 예시 문제가 없습니다. "
        formatted += "위 예시들을 참고하여 요청하신 난이도에 맞게 문제를 생성하겠습니다."
    
    return formatted

# 문제 생성 템플릿 
exam_template = PromptTemplate(
    input_variables=["subject_name", "topic", "difficulty", "examples"],
    template="""
    정보처리기사 {subject_name}의 {topic} 관련 {difficulty}난이도 문제를 생성해주세요.

    {examples}

    위 예시들을 참고하여 비슷한 난이도와 형식으로 새로운 문제를 생성해주세요.
    반드시 아래 형식을 정확하게 지켜주세요:

    # [문제]
    문제 내용을 여기에 작성하세요.

    # [보기]
    ① 첫 번째 보기
    ② 두 번째 보기
    ③ 세 번째 보기
    ④ 네 번째 보기

    # [정답]
    정답 번호를 여기에 작성하세요.

    # [해설]
    각 보기를 하나씩 설명하고 왜 해당 답이 정답인지 명확하게 설명해주세요.
    """
)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/get-topics")
async def get_topics():
    """JSON 파일에서 과목별 토픽 정보를 가져옴"""
    question_data = load_question_data()
    return question_data

@app.post("/generate-question")
async def generate_question(request: QuestionRequest):
    try:
        # 데이터 로드
        question_data = load_question_data()
        
        # 과목명 가져오기
        subject_name = question_data[request.subject]["name"]
        
        # 예시 문제 찾기
        examples, available_difficulties = find_example_questions(
            question_data, 
            request.subject, 
            request.topic,
            request.difficulty
        )
        
        # 예시 문제 포맷팅
        formatted_examples = format_example_questions(
            examples, 
            request.difficulty,
            available_difficulties
        )
        
        # ChatGPT 초기화
        llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
        
        # 프롬프트 생성
        prompt = exam_template.format(
            subject_name=subject_name,
            topic=request.topic,
            difficulty=request.difficulty,
            examples=formatted_examples
        )

        # LLM에 프롬프트 전달
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        try:
            # [문제] 파싱
            parts = content.split("# [문제]")
            if len(parts) < 2:
                raise ValueError("문제 형식이 올바르지 않습니다.")
            
            question_parts = parts[1].split("# [보기]")
            if len(question_parts) < 2:
                raise ValueError("보기 형식이 올바르지 않습니다.")
            
            question = question_parts[0].strip()
            
            # 보기와 정답 파싱
            options_parts = question_parts[1].split("# [정답]")
            if len(options_parts) < 2:
                raise ValueError("정답 형식이 올바르지 않습니다.")
            
            # 보기 파싱 및 정제
            options_text = options_parts[0].strip()
            options = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
            # 원문자와 번호 제거하고 내용만 추출
            options = [opt[1:].strip() if opt.startswith(("①", "②", "③", "④")) else opt for opt in options]
            
            # 정답과 해설 파싱
            answer_parts = options_parts[1].split("# [해설]")
            if len(answer_parts) < 2:
                raise ValueError("해설 형식이 올바르지 않습니다.")
            
            answer = answer_parts[0].strip()
            explanation = answer_parts[1].strip()

            # 보기 검증
            if len(options) < 4:
                raise ValueError("보기가 4개 미만입니다.")
            
            # 4개로 제한
            options = options[:4]
            
            return {
                "question": question,
                "options": options,
                "answer": answer,
                "explanation": explanation,
            }
            
        except Exception as parsing_error:
            print(f"Parsing error: {str(parsing_error)}")
            print(f"Raw content: {content}")
            raise ValueError(f"응답 파싱 중 오류 발생: {str(parsing_error)}")
    
    except Exception as e:
        print(f"Error generating question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)