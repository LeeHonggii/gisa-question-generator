import os
import json
from pathlib import Path
import re

def parse_markdown_file(file_path):
    """마크다운 파일을 파싱하여 문제 데이터로 변환"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 개별 문제들을 분리 (--- 구분자 사용)
    questions = content.split('---')
    parsed_questions = []

    for question in questions:
        if not question.strip():
            continue

        question_data = {
            "difficulty": "",
            "category": "",
            "question": "",
            "options": [],
            "answer": "",
            "explanation": ""
        }

        # 난이도 파싱
        difficulty_match = re.search(r'\*\*난이도\*\*:\s*(.*)', question)
        if difficulty_match:
            stars = difficulty_match.group(1).count('⭐')
            if stars == 1:
                question_data["difficulty"] = "하"
            elif stars == 2:
                question_data["difficulty"] = "중"
            else:
                question_data["difficulty"] = "상"

        # 카테고리 파싱
        category_match = re.search(r'\*\*카테고리\*\*:\s*(.*)', question)
        if category_match:
            question_data["category"] = category_match.group(1).strip()

        # 문제 파싱
        question_match = re.search(r'\*\*문제\*\*\s*([\s\S]*?)\s*\*\*보기\*\*', question)
        if question_match:
            question_data["question"] = question_match.group(1).strip()

        # 보기 파싱 - 수정된 부분
        options_section = re.search(r'\*\*보기\*\*\s*([\s\S]*?)\s*\*\*정답\*\*', question)
        if options_section:
            options_text = options_section.group(1)
            # 1. 2. 3. 4. 형식의 보기를 찾음
            options = re.findall(r'\d\.\s*(.*?)(?=(?:\d\.|$|\*\*정답\*\*))', options_text, re.DOTALL)
            question_data["options"] = [opt.strip() for opt in options if opt.strip()]

        # 정답 파싱
        answer_match = re.search(r'\*\*정답\*\*:\s*(\d+)', question)
        if answer_match:
            question_data["answer"] = answer_match.group(1).strip()

        # 해설 파싱
        explanation_match = re.search(r'\*\*해설\*\*\s*([\s\S]*?)(?=---|$)', question)
        if explanation_match:
            question_data["explanation"] = explanation_match.group(1).strip()

        # 데이터 검증
        if all([
            question_data["difficulty"],
            question_data["category"],
            question_data["question"],
            question_data["options"],  # 보기가 비어있지 않은지 확인
            question_data["answer"],
            question_data["explanation"]
        ]):
            parsed_questions.append(question_data)
        else:
            print(f"Warning: Incomplete question data in {file_path}")
            print("Missing fields:", {k: v for k, v in question_data.items() if not v})

    return parsed_questions

def create_dataset(base_dir):
    """디렉토리 구조를 순회하며 데이터셋 생성"""
    data = {}
    
    # 각 과목 폴더 처리
    for subject_num in range(1, 6):
        subject_dir = Path(base_dir) / f"{subject_num}과목"
        if not subject_dir.exists():
            print(f"Warning: Subject directory {subject_num}과목 not found")
            continue

        subject_data = {
            "name": SUBJECTS.get(str(subject_num), ""),
            "topics": {}
        }

        # 각 md 파일(토픽) 처리
        for md_file in subject_dir.glob("*.md"):
            print(f"Processing file: {md_file}")
            topic_name = md_file.stem  # 파일 이름이 토픽명
            questions = parse_markdown_file(md_file)
            
            if not questions:
                print(f"Warning: No valid questions found in {md_file}")
                continue

            # 문제들을 세트로 변환
            sets = []
            for q in questions:
                set_data = {
                    "reference": "",  # 참고 내용은 현재 없음
                    "example": {
                        "difficulty": q["difficulty"],
                        "question": q["question"],
                        "options": q["options"],
                        "answer": q["answer"],
                        "explanation": q["explanation"]
                    }
                }
                sets.append(set_data)

            if sets:
                subject_data["topics"][topic_name] = {"sets": sets}

        if subject_data["topics"]:
            data[str(subject_num)] = subject_data

    return data

def main():
    # 과목 정보
    global SUBJECTS
    SUBJECTS = {
        "1": "소프트웨어 설계",
        "2": "소프트웨어 개발",
        "3": "데이터베이스 구축",
        "4": "프로그래밍 언어 활용",
        "5": "정보시스템 구축 관리"
    }

    # 기본 디렉토리 경로
    base_dir = Path(r"C:\Users\cava2\Desktop\study\정보처리기사")
    output_file = "gisa_questions.json"

    # 디버깅: 실제 폴더 구조 확인
    print("현재 경로:", base_dir)
    print("존재하는 폴더들:")
    for item in base_dir.glob("*"):
        if item.is_dir():
            print(f"- {item.name}")

    try:
        # 데이터셋 생성
        data = create_dataset(base_dir)

        if not data:
            print("Error: No valid data generated")
            return

        # JSON 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"데이터셋이 성공적으로 생성되었습니다: {output_file}")
        
        # 통계 출력
        for subject_num, subject_data in data.items():
            total_questions = sum(len(topic["sets"]) for topic in subject_data["topics"].values())
            print(f"과목 {subject_num} ({subject_data['name']}): {total_questions}개 문제")

    except Exception as e:
        print(f"데이터셋 생성 중 오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()