import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def rate_submission(course_name, day_number, topic_title, assignment_title, assignment_description, submission_text, submission_file):
    prompt = f"""
You are an expert evaluator for a learning platform called Ramskon.

Evaluate this student submission fairly and strictly.

Course: {course_name}
Day: {day_number}
Topic: {topic_title}
Assignment Title: {assignment_title}
Assignment Description: {assignment_description}
Student Note: {submission_text}
Uploaded File Name: {submission_file}

Return only valid JSON in this exact format:
{{
  "score": 0,
  "verdict": "Poor",
  "strengths": ["point 1", "point 2"],
  "missing_parts": ["point 1", "point 2"],
  "improvement_tip": "one short tip",
  "teacher_comment": "one short paragraph"
}}

Scoring guide:
0-2 = unrelated or missing proof
3-4 = weak or incomplete
5-6 = basic completion
7-8 = good work
9-10 = excellent and clearly matches assignment
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a strict but fair assignment evaluator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "score": 5,
            "verdict": "Average",
            "strengths": ["Submission received"],
            "missing_parts": ["AI response was not in perfect JSON format"],
            "improvement_tip": "Review the submission manually.",
            "teacher_comment": content
        }


def explain_topic(course_name, day_number, topic_title, topic_description, assignment_title, assignment_description):
    prompt = f"""
You are an AI mentor for a learning platform called Ramskon.

Explain this topic for a beginner in very simple language.

Course: {course_name}
Day: {day_number}
Topic: {topic_title}
Topic Description: {topic_description}
Assignment Title: {assignment_title}
Assignment Description: {assignment_description}

Return only valid JSON in this exact format:
{{
  "simple_explanation": "short beginner-friendly explanation",
  "why_it_matters": "why this topic is important",
  "beginner_tips": ["tip 1", "tip 2", "tip 3"],
  "practice_steps": ["step 1", "step 2", "step 3"],
  "youtube_search_queries": ["query 1", "query 2", "query 3"],
  "mini_practice_task": "one small practice task"
}}

Important:
- youtube_search_queries must be highly specific to the exact topic.
- Make them Telugu-friendly.
- Do NOT give direct YouTube links.
- Do NOT give generic queries.
- Queries must include the topic name clearly.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful beginner-friendly AI teacher."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "simple_explanation": content,
            "why_it_matters": "This topic is important for building strong fundamentals.",
            "beginner_tips": ["Practice slowly", "Focus on basics first", "Repeat once more"],
            "practice_steps": ["Read the topic", "Try the assignment", "Revise your work"],
            "youtube_search_queries": [
                f"{topic_title} Telugu tutorial",
                f"{course_name} {topic_title} Telugu",
                f"{topic_title} for beginners Telugu"
            ],
            "mini_practice_task": "Try a small beginner-level practice task based on this topic."
        }