import streamlit as st
import replicate
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App title and description
st.set_page_config(page_title="DxVar: Genomic Analysis Assistant")
st.title("DxVar")
st.write("Powered by Llama-3 and Replicate API")

# Ensure API token is available
API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not API_TOKEN:
    st.error("API token not found! Please set `REPLICATE_API_TOKEN` in your environment.")
    st.stop()
os.environ['REPLICATE_API_TOKEN'] = API_TOKEN

# Model configuration
MODEL_NAME = "meta/meta-llama-3-70b-instruct"  # Llama model via Replicate API
TEMPERATURE = 0.7
TOP_P = 0.95
MAX_TOKENS = 1000

# System prompt for the assistant
SYSTEM_PROMPT = (
    "You are a clinician assistant chatbot specializing in genomic research and variant analysis. "
    "Your task is to interpret user-provided genetic variant data, identify possible Mendelian diseases, and provide concise responses."
)

# Store chat history in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Welcome to DxVar! How can I assist you with genomic research and variant analysis?"}
    ]

# Display chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Function to generate response using Replicate API
def generate_response(user_input):
    full_prompt = f"""
    {SYSTEM_PROMPT}

    User Query: {user_input}

    Assistant's Response:
    """
    try:
        output = replicate.run(
            MODEL_NAME,
            input={
                "prompt": full_prompt,
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
            },
        )

        # Process the output
        if isinstance(output, list):
            return "".join(output).strip()
        return output or "No response generated."
    except Exception as e:
        return f"Error: {str(e)}"

# Handle user input
if user_input := st.chat_input("Enter genetic variant information (e.g., chr1:12345(A>T)) and any query about it..."):
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Processing your query..."):
            response = generate_response(user_input)
            st.write(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

# Clear chat history button
if st.sidebar.button("Clear Chat History"):
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Welcome to DxVar! How can I assist you with genomic research and variant analysis?"}
    ]
