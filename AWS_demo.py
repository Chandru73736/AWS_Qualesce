import streamlit as st
import boto3
 
# ---------------- Page setup ----------------
st.set_page_config(
    page_title="Internal Knowledge Assistant",
    layout="wide"
)
 
# ---------------- Custom CSS (Blue & White Theme) ----------------
st.markdown(
    """
<style>
        .stApp {
            background-color: #f5f9ff;
        }
 
        h1, h2, h3 {
            color: #0b3c6d;
        }
 
        section[data-testid="stSidebar"] {
            background-color: #e6f0ff;
        }
 
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
</style>
    """,
    unsafe_allow_html=True
)
 
# ---------------- Header with Logo (Top Right) ----------------
col1, col2 = st.columns([6, 1.6])
 
with col1:
    st.title("🤖 Qualesce Knowledge Assistant")
    st.write("Ask questions:")
 
with col2:
    st.image(
        "Qualesce Logo.png",
       width=350
    )
 
# ---------------- Load AWS credentials ----------------
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_DEFAULT_REGION = st.secrets["AWS_DEFAULT_REGION"]
 
# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []
 
if "topic" not in st.session_state:
    st.session_state["topic"] = "UiPath"
 
# ---------------- Sidebar Topic Selection ----------------
st.sidebar.header("📚 Topics")
 
topics = ["UiPath", "Worksoft", "HR Policies"]
selected_topic = st.sidebar.radio(
    "Select a Topic to Chat About:",
    topics
)
 
st.session_state["topic"] = selected_topic
st.sidebar.success(f"Selected Topic: {selected_topic}")
 
# ---------------- Chat Header ----------------
st.subheader(f"💬 Chat about {st.session_state['topic']}")
 
# ---------------- Display Previous Messages ----------------
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
 
# ---------------- User Input ----------------
if prompt := st.chat_input("Ask your question here..."):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state["messages"].append(
        {"role": "user", "content": prompt}
    )
 
    # Build contextual question
    question = f"Topic: {st.session_state['topic']}. Question: {prompt}"
 
    # ---------------- AWS Bedrock Client ----------------
    client = boto3.client(
        "bedrock-agent-runtime",
        region_name=AWS_DEFAULT_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
 
    # ---------------- Retrieve & Generate ----------------
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
 
    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(answer)
 
    st.session_state["messages"].append(
        {"role": "assistant", "content": answer}
    )
 
