import streamlit as st
import boto3
 
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
 
        /* 🔽 Make Topic History header slightly smaller */
        div[data-testid="column"]:last-child h3 {
            font-size: 16px !important;   /* default ~20px */
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
        st.session_state["messages"][st.session_state["topic"]].append(
            {"role": "user", "content": prompt}
        )
 
        question = f"Topic: {st.session_state['topic']}. Question: {prompt}"
 
        client = boto3.client(
            "bedrock-agent-runtime",
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
 
        response = client.retrieve_and_generate(
            input={"text": question},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": "HGWSAMUGCM",
                    "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
                }
            }
        )
 
        answer = response["output"]["text"]
 
        st.session_state["messages"][st.session_state["topic"]].append(
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
                        st.markdown(f"**Q{i+1}:** {m['content'][:80]}...")
