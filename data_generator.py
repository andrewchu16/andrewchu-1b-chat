import json


def get_multiline_input(
    prompt="Your response (type END on a new line to finish, ctrl+c to end the session):",
):
    print(prompt)
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    questions_file = "data/questions.txt"  # input file: one question per line
    output_file = "data/train.jsonl"  # output file in JSONL format

    with open(questions_file, "r", encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]

    start_index = 0

    with open(output_file, "r", encoding="utf-8") as f:
        start_index = len(f.readlines())

    with open(output_file, "a", encoding="utf-8") as out:
        for question in questions[start_index:]:
            print(f"\nQuestion: {question}")
            response = get_multiline_input()

            record = {
                "messages": [
                    {"role": "assistant", "content": question},
                    {"role": "user", "content": response},
                ]
            }

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(questions)} question-response pairs to {output_file}")


if __name__ == "__main__":
    main()
