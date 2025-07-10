import streamlit as st
import openai
from dotenv import load_dotenv
import os
import json
import pandas as pd
from datetime import datetime
import PyPDF2
import docx

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize session state
if 'quiz_history' not in st.session_state:
    st.session_state['quiz_history'] = []
if 'current_quiz' not in st.session_state:
    st.session_state['current_quiz'] = None
if 'user_answers' not in st.session_state:
    st.session_state['user_answers'] = {}
if 'performance_data' not in st.session_state:
    st.session_state['performance_data'] = []


def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error processing PDF: {str(e)}"


def extract_text_from_docx(docx_file):
    try:
        doc = docx.Document(docx_file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        return f"Error processing DOCX: {str(e)}"


def generate_questions(content, topic, num_questions=5, question_type="MCQ"):
    """Generate questions based on content using OpenAI"""
    try:
        prompt = f"""Create {num_questions} {question_type} questions on the topic '{topic}' from the following content.\nFor each question, provide:\n1. The question\n2. Options (for MCQ)\n3. Correct answer\n4. Explanation\n5. Hint\n\nFormat as JSON with the following structure:\n{{\n    'questions': [\n        {{\n            'question': 'question text',\n            'options': ['option1', 'option2', 'option3', 'option4'] (for MCQ),\n            'correct_answer': 'correct answer',\n            'explanation': 'detailed explanation',\n            'hint': 'helpful hint'\n        }}\n    ]\n}}\n\nContent: {content}"""

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert quiz maker that creates educational questions. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # Get the response content
        response_content = response.choices[0].message.content

        try:
            questions = json.loads(response_content)
            return questions
        except json.JSONDecodeError as e:
            st.error(f"JSON parsing error: {str(e)}")
            st.write("Debug - Raw API Response:", response_content)
            st.write("The response was not valid JSON. Please try again.")
            return {"error": "Failed to parse questions - Invalid JSON format"}
    except Exception as e:
        st.error(f"Error in generate_questions: {str(e)}")
        return {"error": str(e)}


def calculate_score(quiz, answers):
    """Calculate score and performance metrics"""
    correct = 0
    total = len(quiz['questions'])
    for i, q in enumerate(quiz['questions']):
        if answers.get(str(i)) == q['correct_answer']:
            correct += 1

    score = (correct / total) * 100
    return {
        'score': score,
        'correct': correct,
        'total': total,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# Set up the Streamlit interface
st.set_page_config(page_title="AI Quiz Maker", layout="wide")

# Custom CSS for modern card look and centered title
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px; }
    .stButton>button:hover { background-color: #45a049; }
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        margin-top: 1.5rem;
        color: #333;
    }
    .stTextInput>div>div>input, .stFileUploader>div>div>input {
        font-size: 1.1rem;
        padding: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Centered title and description
st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    <h1 style='font-size: 2.8rem; margin-bottom: 0.5rem;'>AI Quiz Maker</h1>
    <div style='font-size: 1.2rem; color: #444;'>Enter a topic OR upload a PDF/DOCX. Set quiz options and generate your quiz!</div>
</div>
""", unsafe_allow_html=True)

# Only two tabs: Create Quiz and Quiz History
quiz_tab, history_tab = st.tabs(["Create Quiz", "Quiz History"])

with quiz_tab:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Step 1: Enter Topic Name</div>",
                unsafe_allow_html=True)
    topic = st.text_input(
        "Topic Name (e.g., Photosynthesis, World War II)", key="topic_input")
    st.markdown("<div class='section-header'>Step 2: Or Upload Study Material (PDF or DOCX)</div>",
                unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload PDF or DOCX", type=[
                                     'pdf', 'docx'], key="file_uploader")
    content = None
    used_source = None
    if uploaded_file:
        if uploaded_file.name.endswith('.pdf'):
            content = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.name.endswith('.docx'):
            content = extract_text_from_docx(uploaded_file)
        if content:
            st.success(
                "File processed successfully! Quiz will be generated from the document.")
            used_source = 'document'
    elif topic:
        content = topic
        used_source = 'topic'
    st.markdown("<div class='section-header'>Step 3: Quiz Settings</div>",
                unsafe_allow_html=True)
    num_questions = st.slider("Number of Questions", 1, 10, 5)
    question_type = st.selectbox(
        "Question Type", ["MCQ", "True/False", "Short Answer"])
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Generate Quiz"):
        if not content:
            st.warning("Please enter a topic or upload a document.")
        else:
            with st.spinner("Generating quiz..."):
                quiz = generate_questions(
                    content, topic if used_source == 'topic' else 'General', num_questions, question_type)
                if "error" not in quiz:
                    st.session_state['current_quiz'] = quiz
                    st.session_state['user_answers'] = {}
                else:
                    st.error(f"Error generating quiz: {quiz['error']}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Always show quiz if available
    if st.session_state.get('current_quiz'):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Your Quiz")
        for i, q in enumerate(st.session_state['current_quiz']['questions']):
            with st.container():
                st.markdown(f"### Question {i+1}")
                st.markdown(
                    f"<div class='question-box'>{q['question']}</div>", unsafe_allow_html=True)
                if question_type == "MCQ":
                    options = q['options']
                    selected = st.radio(
                        f"Select your answer for Question {i+1}",
                        options,
                        key=f"q_{i}",
                        index=None
                    )
                    st.session_state['user_answers'][str(i)] = selected
                elif question_type == "True/False":
                    selected = st.radio(
                        f"Select your answer for Question {i+1}", ["True", "False"], key=f"q_{i}", index=None)
                    st.session_state['user_answers'][str(i)] = selected
                else:  # Short Answer
                    answer = st.text_input(
                        f"Your answer for Question {i+1}", key=f"q_{i}")
                    st.session_state['user_answers'][str(i)] = answer
                with st.expander("Hint"):
                    st.write(q['hint'])
        if st.button("Submit Quiz"):
            if len(st.session_state['user_answers']) == len(st.session_state['current_quiz']['questions']):
                performance = calculate_score(
                    st.session_state['current_quiz'], st.session_state['user_answers'])
                st.session_state['performance_data'].append(performance)
                st.subheader("Quiz Results")
                st.write(f"Score: {performance['score']:.1f}%")
                st.write(
                    f"Correct Answers: {performance['correct']}/{performance['total']}")
                st.subheader("Explanations")
                for i, q in enumerate(st.session_state['current_quiz']['questions']):
                    with st.expander(f"Question {i+1} Explanation"):
                        st.write(
                            f"Your answer: {st.session_state['user_answers'][str(i)]}")
                        st.write(f"Correct answer: {q['correct_answer']}")
                        st.write(f"Explanation: {q['explanation']}")
            else:
                st.warning("Please answer all questions before submitting!")
        st.markdown("</div>", unsafe_allow_html=True)

with history_tab:
    st.subheader("Quiz History")
    if st.session_state['performance_data']:
        df = pd.DataFrame(st.session_state['performance_data'])
        st.dataframe(df)
        st.line_chart(df['score'])
    else:
        st.write("No quiz history yet.")
