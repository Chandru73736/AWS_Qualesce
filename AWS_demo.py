import streamlit as st
import boto3
import json
from enum import Enum

# ---------------- Page setup ----------------
st.set_page_config(
    page_title="Internal Knowledge Assistant",
    layout="wide"
)

# ---------------- Custom CSS ----------------
st.markdown(
    """
<style>
    .stApp {
        background-color: #f5f9ff;
    }

    h1, h2 {
        color: #0b3c6d;
    }

    h3 {
        color: #0b3c6d;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #e6f0ff;
    }

    /* Chat bubbles */
    .stChatMessage.user {
        background-color: #d9e8ff;
        border-radius: 10px;
        padding: 10px;
    }

    .stChatMessage.assistant {
        background-color: #f5f9ff;
        border-radius: 10px;
        padding: 10px;
    }

    /* Make Topic History header slightly smaller */
    div[data-testid="column"]:last-child h3 {
        font-size: 16px !important;
        margin-bottom: 8px !important;
    }
</style>
    """,
    unsafe_allow_html=True
)

# ---------------- Header ----------------
col1, col2 = st.columns([6, 1.6])
with col1:
    st.title("🤖 Qualesce Knowledge Assistant")
    st.write("Ask questions based on internal knowledge")

with col2:
    st.image("Qualesce Logo.png", width=300)

# ---------------- AWS Secrets ----------------
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_DEFAULT_REGION = st.secrets["AWS_DEFAULT_REGION"]

# ---------------- Session State ----------------
if "topic" not in st.session_state:
    st.session_state["topic"] = "UiPath"

if "messages" not in st.session_state:
    st.session_state["messages"] = {
        "UiPath": [],
        "Worksoft": [],
        "HR Policies": []
    }

# ---------------- Topic Match Enum ----------------
class TopicMatch(str, Enum):
    MATCHES = "matches"
    DOES_NOT_MATCH = "does_not_match"
    UNCLEAR = "unclear"

# ---------------- Sidebar ----------------
st.sidebar.header("📚 Topics")

topics = ["UiPath", "Worksoft", "HR Policies"]
selected_topic = st.sidebar.radio(
    "Select Topic",
    topics,
    index=topics.index(st.session_state["topic"])
)

if selected_topic != st.session_state["topic"]:
    st.session_state["topic"] = selected_topic
    st.rerun()

# ---------------- Layout ----------------
chat_col, history_col = st.columns([3, 1])

# ---------------- Chat Section ----------------
with chat_col:
    st.subheader(f"💬 Chat about {st.session_state['topic']}")

    chat_container = st.container()

    with chat_container:
        for msg in st.session_state["messages"][st.session_state["topic"]]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    prompt = st.chat_input("Ask your question here...")

    if prompt:
        current_topic = st.session_state["topic"]

        # Save user message
        st.session_state["messages"][current_topic].append(
            {"role": "user", "content": prompt}
        )

        # ── Step 1: Classify whether question belongs to current topic ──
        classifier_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        classification_prompt = f"""You are a very strict topic classifier.
Respond with **exactly one** of these words — nothing else, no explanation, no punctuation:

matches          ← the question is clearly and directly about {current_topic}
does_not_match   ← the question is clearly about something else
unclear          ← you really cannot tell / ambiguous

Question: {prompt}

Answer:"""

        try:
            cls_response = classifier_client.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 10,
                    "temperature": 0.0,
                    "messages": [{"role": "user", "content": classification_prompt}]
                })
            )
            response_body = json.loads(cls_response["body"].read())
            cls_text = response_body["content"][0]["text"].strip().lower()

            if cls_text in [e.value for e in TopicMatch]:
                match_result = TopicMatch(cls_text)
            else:
                match_result = TopicMatch.UNCLEAR

        except Exception as e:
            st.error(f"Classification error: {str(e)}")
            match_result = TopicMatch.UNCLEAR

        # ── Step 2: Decide action ──
        if match_result == TopicMatch.MATCHES:
            # Proceed with Knowledge Base retrieval + generation
            question = f"Topic: {current_topic}. Question: {prompt}"

            rag_client = boto3.client(
                "bedrock-agent-runtime",
                region_name=AWS_DEFAULT_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )

            try:
                response = rag_client.retrieve_and_generate(
                    input={"text": question},
                    retrieveAndGenerateConfiguration={
                        "type": "KNOWLEDGE_BASE",
                        "knowledgeBaseConfiguration": {
                            "knowledgeBaseId": "HGWSAMUGCM",
                            "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
                        }
                    }
                )
                answer = response["output"]["text"].strip()
            except Exception as e:
                answer = f"Error while querying knowledge base: {str(e)}"

        else:
            # Apology messages
            apologies = {
                "UiPath": "I'm sorry, this question doesn't appear to be related to UiPath. Please ask something about UiPath RPA, Orchestrator, robots, Studio, etc.",
                "Worksoft": "I'm sorry, this question doesn't seem to be about Worksoft Certify or related tools. Please ask a Worksoft-specific question.",
                "HR Policies": "I'm sorry, this doesn't look like a question about our HR policies, benefits, leave, payroll, etc. Please ask an HR-related question."
            }
            answer = apologies.get(current_topic, "Sorry, this question doesn't match the selected topic.")

        # Save assistant response
        st.session_state["messages"][current_topic].append(
            {"role": "assistant", "content": answer}
        )

        st.rerun()

# ---------------- History Panel ----------------
with history_col:
    st.subheader("🕘 Topic History")

    for topic, msgs in st.session_state["messages"].items():
        if msgs:
            with st.expander(f"{topic} ({len(msgs)} messages)"):
                for i, m in enumerate(msgs):
                    if m["role"] == "user":
                        preview = m["content"][:80] + "..." if len(m["content"]) > 80 else m["content"]
                        st.markdown(f"**Q{i//2 + 1}:** {preview}")
