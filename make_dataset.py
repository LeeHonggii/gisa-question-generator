import json
from pathlib import Path


def parse_text_file(file_path):
    """텍스트 파일을 파싱하여 구조화된 데이터로 변환"""
    print(f"파싱 시작: {file_path}")

    current_subject = None
    current_topic = None
    data = {}

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 과목과 주제 정보 인식
        if line.startswith("과목"):
            parts = line.split("주제:")
            subject_part = parts[0].strip()
            subject_num = subject_part.split(":")[0].split()[-1]
            subject_name = subject_part.split(":")[-1].strip()

            if subject_num not in data:
                data[subject_num] = {"name": subject_name, "topics": {}}

            if len(parts) > 1:
                current_topic = parts[1].strip()
                if current_topic not in data[subject_num]["topics"]:
                    data[subject_num]["topics"][current_topic] = {"sets": []}
            current_subject = subject_num

        # 세트 처리
        elif line.startswith("===세트 시작==="):
            current_set = {"reference": "", "example": {}}
            in_reference = False
            in_example = False
            example = {
                "difficulty": "",
                "question": "",
                "options": [],
                "answer": "",
                "explanation": "",
            }

            i += 1
            while i < len(lines) and not lines[i].strip().startswith("===세트 끝==="):
                line = lines[i].strip()

                if line.startswith("참고내용:"):
                    in_reference = True
                    in_example = False
                elif line.startswith("예시문제:"):
                    in_reference = False
                    in_example = True
                elif line.startswith("난이도:"):
                    example["difficulty"] = line.split(":")[-1].strip()
                elif line.startswith("문제:"):
                    example["question"] = line.split(":")[-1].strip()
                elif (
                    line.startswith("①")
                    or line.startswith("②")
                    or line.startswith("③")
                    or line.startswith("④")
                ):
                    example["options"].append(line[1:].strip())
                elif line.startswith("정답:"):
                    example["answer"] = line.split(":")[-1].strip()
                elif line.startswith("해설:"):
                    example["explanation"] = line.split(":")[-1].strip()
                elif in_reference and line:
                    current_set["reference"] += line + "\n"

                i += 1

            current_set["example"] = example
            if current_subject and current_topic:
                data[current_subject]["topics"][current_topic]["sets"].append(
                    current_set
                )

        i += 1

    return data


def save_as_json(data, output_file):
    """데이터를 JSON 파일로 저장"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    # 텍스트 파일들이 있는 디렉토리
    input_dir = Path("input_texts")
    # 출력 JSON 파일 경로
    output_file = "gisa_questions.json"

    if not input_dir.exists():
        print(f"입력 디렉토리가 없습니다. {input_dir} 디렉토리를 생성합니다.")
        input_dir.mkdir(parents=True)

    all_data = {}

    # 입력 디렉토리의 모든 .txt 파일 처리
    txt_files = list(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"경고: {input_dir} 디렉토리에 .txt 파일이 없습니다.")
        return

    for text_file in txt_files:
        print(f"처리 중: {text_file}")
        try:
            data = parse_text_file(text_file)
            for subject_num, subject_data in data.items():
                if subject_num not in all_data:
                    all_data[subject_num] = subject_data
                else:
                    # 기존 과목에 새로운 주제 추가
                    all_data[subject_num]["topics"].update(subject_data["topics"])

        except Exception as e:
            print(f"파일 처리 중 오류 발생: {text_file}, 오류: {str(e)}")

    if all_data:
        # JSON 파일로 저장
        save_as_json(all_data, output_file)
        print(f"데이터가 {output_file}로 저장되었습니다.")
    else:
        print("처리된 데이터가 없습니다.")


if __name__ == "__main__":
    main()
