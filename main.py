from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# API KEY 정보로드
load_dotenv()

# ChatOpenAI 모델 초기화
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# 음식 레시피 프롬프트 템플릿 예시
recipe_template = PromptTemplate(
    input_variables=["dish_name", "servings"],
    template="""
    {dish_name} {servings}인분 레시피를 다음 형식으로 알려주세요:

    1. 필요한 재료
    2. 조리 시간
    3. 조리 난이도
    4. 상세 조리 방법
    5. 조리 팁

    실제 요리사가 설명하는 것처럼 자세하게 설명해주세요.
    """
)

# 여행 계획 프롬프트 템플릿 예시
travel_template = PromptTemplate(
    input_variables=["destination", "days", "budget"],
    template="""
    {destination}로 {days}일 여행을 가려고 합니다. 예산은 {budget}원 입니다.
    다음 사항을 고려한 여행 일정을 만들어주세요:

    1. 일자별 방문할 관광지
    2. 숙소 추천
    3. 식당 추천
    4. 예산 분배 방안
    5. 현지 교통 정보

    현지 여행 전문가처럼 실용적인 정보를 제공해주세요.
    """
)

# 프롬프트 템플릿 사용 예시
def get_recipe(dish_name: str, servings: int):
    # 프롬프트 생성
    prompt = recipe_template.format(dish_name=dish_name, servings=servings)
    # LLM에 프롬프트 전달
    response = llm.invoke(prompt)
    return response

def get_travel_plan(destination: str, days: int, budget: int):
    # 프롬프트 생성
    prompt = travel_template.format(
        destination=destination,
        days=days,
        budget=budget
    )
    # LLM에 프롬프트 전달
    response = llm.invoke(prompt)
    return response

# 사용 예시
if __name__ == "__main__":
    # 레시피 얻기
    recipe = get_recipe("김치찌개", 4)
    print(recipe)
    
    # 여행 계획 얻기
    travel_plan = get_travel_plan("제주도", 3, 500000)
    print(travel_plan)