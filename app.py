import streamlit as st
import replicate
import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App title and description
st.set_page_config(page_title="DxVar: Genomic Analysis Assistant")
st.title("DxVar")

# Hide Streamlit branding
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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
    "Your task is to interpret user-provided genetic variant data, identify possible Mendelian diseases, and provide concise responses. "
    "If the user enters variants, respond in CSV format: chromosome,position,ref base,alt base,genome. "
    "For example: chr6:160585140-T>G should be 6,160585140,T,G,hg38."
)

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

        if isinstance(output, list):
            return "".join(output).strip()
        return output or "No response generated."
    except Exception as e:
        return f"Error: {str(e)}"

# Function to query genomic variant API
def query_variant_api(variant_input):
    url = "https://api.genebe.net/cloud/api-public/v1/variant"
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, params=variant_input)
        if response.status_code == 200:
            data = response.json()
            if "variants" in data and len(data["variants"]) > 0:
                return data["variants"][0]
            else:
                return {"error": "No variant information found."}
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Handle user input
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Welcome to DxVar! How can I assist you with genomic research and variant analysis?"}
    ]

# Display chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input := st.chat_input("Enter genetic variant information (e.g., chr1:12345(A>T)):"):
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Processing your query..."):
            response = generate_response(user_input)
            st.write(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

            # Parse variant information
            try:
                parts = response.split(",")
                if len(parts) == 5:
                    variant_input = {
                        "chr": parts[0],
                        "pos": parts[1],
                        "ref": parts[2],
                        "alt": parts[3],
                        "genome": parts[4]
                    }

                    # Query GeneBe API
                    variant_result = query_variant_api(variant_input)

                    if "error" in variant_result:
                        st.error(variant_result["error"])
                    else:
                        st.write("### GeneBe API Results")
                        st.json(variant_result)

                        # Display additional results if available
                        acmg_classification = variant_result.get("acmg_classification", "Not Available")
                        effect = variant_result.get("effect", "Not Available")
                        gene_symbol = variant_result.get("gene_symbol", "Not Available")
                        hgnc_id = variant_result.get("gene_hgnc_id", "Not Available")

                        st.write("### ACMG Classification")
                        st.write(f"ACMG Classification: {acmg_classification}")
                        st.write(f"Effect: {effect}")
                        st.write(f"Gene Symbol: {gene_symbol}")
                        st.write(f"HGNC ID: {hgnc_id}")

                        # Add AI follow-up
                        follow_up_query = f"Tell me about possible Mendelian diseases linked to {gene_symbol} ({hgnc_id})."
                        follow_up_response = generate_response(follow_up_query)

                        st.write("### Follow-up Analysis")
                        st.write(follow_up_response)

            except Exception as e:
                st.error(f"Error parsing response: {str(e)}")

# Sidebar functionality
st.sidebar.header("Genomic Variant Query")
variant_input = st.sidebar.text_input("Enter variant details (e.g., chr=1, pos=12345, ref=A, alt=T, genome=hg38):", "")
if st.sidebar.button("Query Variant"):
    try:
        variant_dict = dict(item.split("=") for item in variant_input.split(",") if "=" in item)
        result = query_variant_api(variant_dict)
        st.sidebar.json(result)
    except Exception as e:
        st.sidebar.error(f"Invalid input format: {str(e)}")

if st.sidebar.button("Clear Chat History"):
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Welcome to DxVar! How can I assist you with genomic research and variant analysis?"}
    ]
