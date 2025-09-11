# app.py
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from typing import List

app = FastAPI()
templates = Jinja2Templates(directory="templates")

QUESTIONS_FILE = Path("data/questions.txt")     # one question per line
OUTPUT_FILE = Path("data/train2.jsonl")       # JSONL output

# Load questions and make them mutable
def load_questions() -> List[str]:
    if QUESTIONS_FILE.exists():
        return [q.strip() for q in QUESTIONS_FILE.read_text(encoding="utf-8").splitlines() if q.strip()]
    return []

def save_questions(questions: List[str]) -> None:
    QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with QUESTIONS_FILE.open("w", encoding="utf-8") as f:
        for q in questions:
            f.write(q + "\n")

def load_existing_answers() -> dict:
    """Load existing answers from the JSONL file, keyed by question content."""
    answers = {}
    if OUTPUT_FILE.exists():
        try:
            with OUTPUT_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line.strip())
                        if "messages" in record and len(record["messages"]) >= 2:
                            question = record["messages"][0]["content"]
                            response = record["messages"][1]["content"]
                            answers[question] = response
        except (json.JSONDecodeError, KeyError, IndexError):
            pass  # Handle malformed JSONL gracefully
    return answers

def get_question_answer(question: str) -> str:
    """Get the existing answer for a question, or empty string if none exists."""
    existing_answers = load_existing_answers()
    return existing_answers.get(question, "")

def has_answer(question: str) -> bool:
    """Check if a question already has an answer."""
    return question in load_existing_answers()

def update_or_append_record(question: str, response: str) -> None:
    """Update existing record or append new one."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Load all existing records
    records = []
    existing_answers = {}
    if OUTPUT_FILE.exists():
        try:
            with OUTPUT_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line.strip())
                        records.append(record)
                        if "messages" in record and len(record["messages"]) >= 2:
                            q = record["messages"][0]["content"]
                            existing_answers[q] = len(records) - 1  # Store index
        except (json.JSONDecodeError, KeyError, IndexError):
            records = []
            existing_answers = {}
    
    # Create new record
    new_record = {
        "messages": [
            {"role": "assistant", "content": question},
            {"role": "user", "content": response.strip()},
        ]
    }
    
    # Update existing or append new
    if question in existing_answers:
        records[existing_answers[question]] = new_record
    else:
        records.append(new_record)
    
    # Write all records back
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

questions = load_questions()

def get_questions_sidebar_data(current_index: int = -1):
    """Generate sidebar data for questions with answer status."""
    existing_answers = load_existing_answers()
    questions_data = []
    answered_count = 0
    
    for i, q in enumerate(questions):
        has_answer = q in existing_answers
        if has_answer:
            answered_count += 1
            
        # Create preview (first 50 chars)
        preview = q[:50] + "..." if len(q) > 50 else q
        
        questions_data.append({
            "index": i,
            "question": q,
            "preview": preview,
            "answered": has_answer,
        })
    
    progress_percentage = (answered_count / len(questions) * 100) if questions else 0
    
    return {
        "questions_data": questions_data,
        "current_index": current_index,
        "answered_count": answered_count,
        "total": len(questions),
        "progress_percentage": round(progress_percentage, 1)
    }

# Routes

@app.get("/")
def root():
    return RedirectResponse(url="/edit/0", status_code=303)

@app.get("/edit/{i}")
def edit_question_and_answer(request: Request, i: int):
    if i < 0:
        return RedirectResponse(url="/edit/0", status_code=303)
    if i >= len(questions):
        return templates.TemplateResponse("done.html", {"request": request})
    
    q = questions[i]
    
    # Check if question has been answered
    existing_answer = get_question_answer(q)
    has_existing_answer = bool(existing_answer)
    
    # Prepare template variables
    status_class = "status-answered" if has_existing_answer else "status-unanswered"
    status_text = "Answered" if has_existing_answer else "Not Answered"
    edit_label = " (editing existing)" if has_existing_answer else ""
    save_button_text = "Update Answer" if has_existing_answer else "Save Answer"
    
    # Get sidebar data
    sidebar_data = get_questions_sidebar_data(i)
    
    context = {
        "request": request,
        "question": q,
        "i": i,
        "idx": i + 1,
        "total": len(questions),
        "existing_answer": existing_answer,
        "status_class": status_class,
        "status_text": status_text,
        "edit_label": edit_label,
        "save_button_text": save_button_text,
        **sidebar_data
    }
    
    return templates.TemplateResponse("question_with_sidebar.html", context)

# Legacy route for compatibility
@app.get("/answer/{i}")
def get_question_legacy(i: int):
    return RedirectResponse(url=f"/edit/{i}", status_code=303)

@app.post("/update-answer/{i}")
def update_answer(i: int, response: str = Form(...)):
    if 0 <= i < len(questions):
        update_or_append_record(questions[i], response)
    return RedirectResponse(url=f"/edit/{i}", status_code=303)

@app.post("/update-question/{i}")
def update_question(i: int, question: str = Form(...)):
    if 0 <= i < len(questions):
        old_question = questions[i]
        new_question = question.strip()
        
        # Update the question in the list
        questions[i] = new_question
        save_questions(questions)
        
        # Update any existing answer to use the new question text
        existing_answer = get_question_answer(old_question)
        if existing_answer:
            # Remove old record and add new one
            update_or_append_record(new_question, existing_answer)
            # Remove the old record by rewriting the file without it
            records = []
            if OUTPUT_FILE.exists():
                with OUTPUT_FILE.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line.strip())
                            if record.get("messages", [{}])[0].get("content") != old_question:
                                records.append(record)
                
                with OUTPUT_FILE.open("w", encoding="utf-8") as f:
                    for record in records:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    return RedirectResponse(url=f"/edit/{i}", status_code=303)

# Legacy route for compatibility
@app.post("/answer/{i}")
def post_answer_legacy(i: int, response: str = Form(...)):
    if 0 <= i < len(questions):
        update_or_append_record(questions[i], response)
    next_i = i + 1
    return RedirectResponse(url=f"/edit/{next_i}", status_code=303)

@app.get("/skip/{i}")
def skip_question(i: int):
    next_i = i + 1
    return RedirectResponse(url=f"/edit/{next_i}", status_code=303)

@app.get("/download")
def download_jsonl():
    if not OUTPUT_FILE.exists():
        return PlainTextResponse("qa_pairs.jsonl not found", status_code=404)
    return PlainTextResponse(OUTPUT_FILE.read_text(encoding="utf-8"), media_type="application/x-ndjson")

# Question editing routes
# Legacy routes for compatibility
@app.get("/edit-question/{i}")
def get_edit_question_legacy(i: int):
    return RedirectResponse(url=f"/edit/{i}", status_code=303)

@app.post("/edit-question/{i}")
def post_edit_question_legacy(i: int, question: str = Form(...)):
    if 0 <= i < len(questions):
        questions[i] = question.strip()
        save_questions(questions)
    return RedirectResponse(url=f"/edit/{i}", status_code=303)

@app.get("/delete-question/{i}")
def delete_question(i: int):
    if 0 <= i < len(questions):
        old_question = questions[i]
        questions.pop(i)
        save_questions(questions)
        
        # Remove any existing answer for this question
        if OUTPUT_FILE.exists():
            records = []
            with OUTPUT_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line.strip())
                        if record.get("messages", [{}])[0].get("content") != old_question:
                            records.append(record)
            
            with OUTPUT_FILE.open("w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        # Redirect to the same position or previous if we deleted the last one
        next_i = min(i, len(questions) - 1) if questions else 0
        return RedirectResponse(url=f"/edit/{next_i}", status_code=303)
    return RedirectResponse(url="/manage", status_code=303)

@app.get("/manage")
def manage_questions(request: Request):
    question_items = []
    existing_answers = load_existing_answers()
    
    for i, q in enumerate(questions):
        has_existing_answer = q in existing_answers
        status_class = "status-answered" if has_existing_answer else "status-unanswered"
        status_text = "Answered" if has_existing_answer else "Not Answered"
        action_text = "Edit Answer" if has_existing_answer else "Answer"
        
        question_items.append({
            "index": i,
            "question": q,
            "answered": has_existing_answer,
            "status_class": status_class,
            "status_text": status_text,
            "action_text": action_text
        })
    
    context = {
        "request": request,
        "total": len(questions),
        "question_items": question_items
    }
    
    return templates.TemplateResponse("manage.html", context)

@app.post("/add-question")
def add_question(question: str = Form(...)):
    new_question = question.strip()
    if new_question:
        questions.append(new_question)
        save_questions(questions)
    return RedirectResponse(url="/manage", status_code=303)

# Optional: simple health check
@app.get("/healthz")
def healthz():
    return {"status": "ok", "questions": len(questions)}
