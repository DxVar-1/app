from json.decoder import JSONDecodeError  # Import JSONDecodeError from json.decoder
import streamlit as st
import requests
from groq import Groq
import pandas as pd
from bs4 import BeautifulSoup
import re  # For regex matching

parts = []

# Set page configuration
st.set_page_config(page_title="DxVar", layout="centered")

st.markdown("""
    <style>
        .justified-text {
            text-align: justify;
        }
        .results-table {
            margin-left: auto;
            margin-right: auto;
        }
    </style>
""", unsafe_allow_html=True)

st.title("DxVar")

# Initialize Groq API client
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "GeneBe_results" not in st.session_state:
    st.session_state.GeneBe_results = ['-','-','-','-','-','-','-','-']
if "InterVar_results" not in st.session_state:
    st.session_state.InterVar_results = ['-','','-','']
if "disease_classification_dict" not in st.session_state:
    st.session_state.disease_classification_dict = {"No diseases found"}
if "flag" not in st.session_state:
    st.session_state.flag = False
if "reply" not in st.session_state:
    st.session_state.reply = ""
if "variant_parts" not in st.session_state:
    st.session_state.variant_parts = None
if "assistant_response" not in st.session_state:
    st.session_state.assistant_response = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_input" not in st.session_state:
    st.session_state.last_input = ""

# Define the initial system message
initial_messages = [
    {
        "role": "system",
        "content": (
            "You are a clinician assistant chatbot specializing in genomic research and variant analysis. "
            "Your task is to interpret user-provided genetic variant data, identify possible Mendelian diseases linked to genes, "
            "and provide concise responses. If the user enters variants, you are to respond in a CSV format as such: "
            "chromosome,position,ref base,alt base,and if no genome is provided, assume hg38. Example: "
            "User input: chr6:160585140-T>G. You respond: 6,160585140,T,G,hg38. This response should be standalone with no extra texts. "
            "Remember bases can be multiple letters (e.g., chr6:160585140-T>GG). If the user has additional requests with the message "
            "including the variant (e.g., 'tell me about diseases linked with the variant: chr6:160585140-T>G'), "
            "ask them to enter only the variant first. They can ask follow-up questions afterward. "
            "The user can enter the variant in any format, but it should be the variant alone with no follow-up questions."
            "If the user enters an rs value simply return the rs value, example:"
            "User input: tell me about rs1234. You respond: rs1234"
            "if both rs and chromosome,position,ref base,alt base are given, give priority to the chromosome, position,ref base,alt base"
            "and only return that, however if any info is missing from chromosome,position,ref base,alt base, just use rs value and return rs"
            "Example: rs124234 chromosome:3, pos:13423. You reply: rs124234. since the ref base and alt base are missing"
        ),
    }
]

file_url = 'https://github.com/wah644/streamlit_app.py/blob/main/Clingen-Gene-Disease-Summary-2025-01-03.csv?raw=true'
df = pd.read_csv(file_url)


# ALL FUNCTIONS

def fetch_alleles(snp_id):
    url = f"https://www.ncbi.nlm.nih.gov/snp/{snp_id}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find the allele section
        allele_section = soup.find(string="Alleles")
        if allele_section:
            parent_element = allele_section.find_parent()
            if parent_element:
                allele_text = parent_element.find_next_sibling().text
                alleles = [allele.strip() for allele in allele_text.split('/') if allele.strip()]
                return alleles
    return None

# New function to fetch variant information from an SNP page
def fetch_variant_info(snp_id):
    url = f"https://www.ncbi.nlm.nih.gov/snp/{snp_id}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=" ", strip=True)
        # Look for a pattern like "chr6:160585140" (case-insensitive)
        match = re.search(r"chr(\w+):(\d+)", text, re.IGNORECASE)
        if match:
            chromosome = match.group(1)
            position = match.group(2)
        else:
            chromosome, position = None, None
        alleles = fetch_alleles(snp_id)
        ref = alleles[0] if alleles and len(alleles) > 0 else None
        return {"chr": chromosome, "pos": position, "ref": ref}
    return None

def find_gene_match(gene_symbol, hgnc_id):
    if 'GENE SYMBOL' in df.columns and 'GENE ID (HGNC)' in df.columns:
        matching_rows = df[(df['GENE SYMBOL'] == gene_symbol) & (df['GENE ID (HGNC)'] == hgnc_id)]
        if not matching_rows.empty:
            selected_columns = matching_rows[['DISEASE LABEL', 'MOI', 'CLASSIFICATION', 'DISEASE ID (MONDO)']]
            styled_table = selected_columns.style.apply(highlight_classification, axis=1)
            st.dataframe(styled_table, use_container_width=True)
            st.session_state.disease_classification_dict = dict(zip(matching_rows['DISEASE LABEL'], matching_rows['CLASSIFICATION']))
        else:
            st.markdown("<p style='color:red;'>No match found.</p>", unsafe_allow_html=True)
    else:
        st.write("No existing gene-disease match found")
        
def get_color(result):
    if result == "Pathogenic":
        return "red"
    elif result == "Likely_pathogenic":
        return "red"
    elif result == "Uncertain_significance":
        return "orange"
    elif result == "Likely_benign":
        return "lightgreen"
    elif result == "Benign":
        return "green"
    else:
        return "black"  # Default color if no match
        
def highlight_classification(row):
    color_map = {
        "Definitive": "color: rgba(66, 238, 66)",
        "Disputed": "color: rgba(255, 0, 0)",
        "Moderate": "color: rgba(144, 238, 144)",
        "Limited": "color: rgba(255, 204, 102)",
        "No Known Disease Relationship": "",
        "Strong": "color: rgba(66, 238, 66)",
        "Refuted": "color: rgba(255, 0, 0)"
    }
    classification = row['CLASSIFICATION']
    return [color_map.get(classification, "")] * len(row)

def get_assistant_response_initial(user_input):
    groq_messages = [{"role": "user", "content": user_input}]
    for message in initial_messages:
        groq_messages.insert(0, {"role": message["role"], "content": message["content"]})
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=groq_messages,
        temperature=1,
        max_completion_tokens=512,
        top_p=1,
        stream=False,
        stop=None,
    )
    return completion.choices[0].message.content

SYSTEM = [
    {
        "role": "system",
        "content": (
            "You are a clinician assistant chatbot specializing in genomic research and variant analysis. "
            "Your task is to interpret user-provided genetic variant data, identify possible Mendelian diseases linked to genes."
        ),
    }
]

def get_assistant_response_1(user_input):
    full_message = SYSTEM + [{"role": "user", "content": user_input}]
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_message,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    assistant_reply = completion.choices[0].message.content
    return assistant_reply

def get_assistant_response(chat_history):
    full_conversation = SYSTEM + chat_history  
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_conversation,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    assistant_reply = completion.choices[0].message.content
    return assistant_reply

###################################################

# Function to parse variant information from the assistant's CSV response
def get_variant_info(message):
    try:
        parts = message.split(',')
        if len(parts) == 5 and parts[1].isdigit():
            return parts
        else:
            return []
    except Exception as e:
        st.write(f"Error while parsing variant: {e}")
        return []

# ---------------------------
user_input = st.text_input("Enter a genetic variant (ex: chr6:160585140-T>G)")
# Process input regardless of whether it changed
if user_input:
    # If the input starts with 'rs', run the SNP branch.
    if user_input.lower().startswith("rs"):
        snp_id = user_input.split()[0]  # e.g., rs121913514
        variant_info = fetch_variant_info(snp_id)
        if variant_info and variant_info["chr"] and variant_info["pos"] and variant_info["ref"]:
            alleles = fetch_alleles(snp_id)
            if alleles:
                st.success(f"Found alleles for {snp_id}: {', '.join(alleles)}")
                selected_allele = st.selectbox("Select an allele:", alleles)
                if st.button("Proceed with Variant Interpretation"):
                    st.session_state.variant_parts = [variant_info["chr"], variant_info["pos"], variant_info["ref"], selected_allele, "hg38"]
                    st.session_state.flag = True
                    with st.chat_message("assistant"):
                        st.write(f"Interpreting variant {snp_id} with allele {selected_allele}...")
                    st.session_state.messages.append({"role": "assistant", "content": f"Interpreting {snp_id} with allele {selected_allele}..."})
    else:
        # For non-SNP input, only process when the input changes.
        if user_input != st.session_state.last_input:
            st.session_state.last_input = user_input
            assistant_response = get_assistant_response_initial(user_input)
            st.session_state.assistant_response = assistant_response
            st.write(f"Assistant: {assistant_response}")
            parts = get_variant_info(assistant_response)
            if parts:
                st.session_state.variant_parts = parts
                st.session_state.flag = True

# ---------------------------
# If a valid variant is set (either from SNP or normal input), perform API calls.
if st.session_state.flag and st.session_state.variant_parts:
    parts = st.session_state.variant_parts
    # GENEBE API call
    url = "https://api.genebe.net/cloud/api-public/v1/variant"
    params = {
        "chr": parts[0],
        "pos": parts[1],
        "ref": parts[2],
        "alt": parts[3],
        "genome": parts[4]
    }
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        try:
            data = response.json()
            variant = data["variants"][0]  # Get the first variant
            st.session_state.GeneBe_results[0] = variant.get("acmg_classification", "Not Available")
            st.session_state.GeneBe_results[1] = variant.get("effect", "Not Available")
            st.session_state.GeneBe_results[2] = variant.get("gene_symbol", "Not Available")
            st.session_state.GeneBe_results[3] = variant.get("gene_hgnc_id", "Not Available")
            st.session_state.GeneBe_results[4] = variant.get("dbsnp", "Not Available")
            st.session_state.GeneBe_results[5] = variant.get("frequency_reference_population", "Not Available")
            st.session_state.GeneBe_results[6] = variant.get("acmg_score", "Not Available")
            st.session_state.GeneBe_results[7] = variant.get("acmg_criteria", "Not Available")
        except JSONDecodeError:
            pass

    # INTERVAR API call
    url = "http://wintervar.wglab.org/api_new.php"
    params = {
        "queryType": "position",
        "chr": parts[0],
        "pos": parts[1],
        "ref": parts[2],
        "alt": parts[3],
        "build": parts[4]
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        try:
            results = response.json()
            st.session_state.InterVar_results[0] = results.get("Intervar", "Not Available")
            st.session_state.InterVar_results[2] = results.get("Gene", "Not Available")
        except JSONDecodeError:
            st.session_state.InterVar_results = ['-','','-','']
    
    # Display ACMG results with appropriate color
    result_color = get_color(st.session_state.GeneBe_results[0])
    st.markdown(f"### ACMG Results: <span style='color:{result_color}'>{st.session_state.GeneBe_results[0]}</span>", unsafe_allow_html=True)
    data = {
        "Attribute": ["Classification", "Effect", "Gene", "HGNC ID", "dbsnp", "freq. ref. pop.", "acmg score", "acmg criteria"],
        "GeneBe Results": [st.session_state.GeneBe_results[0], st.session_state.GeneBe_results[1],
                             st.session_state.GeneBe_results[2], st.session_state.GeneBe_results[3],
                             st.session_state.GeneBe_results[4], st.session_state.GeneBe_results[5],
                             st.session_state.GeneBe_results[6], st.session_state.GeneBe_results[7]],
        "InterVar Results": [st.session_state.InterVar_results[0], st.session_state.InterVar_results[1],
                             st.session_state.InterVar_results[2], st.session_state.InterVar_results[3],
                             '', '', '', ''],
    }
    acmg_results = pd.DataFrame(data)
    acmg_results.set_index("Attribute", inplace=True)
    st.dataframe(acmg_results, use_container_width=True)
    
    st.write("### ClinGen Gene-Disease Results")
    find_gene_match(st.session_state.GeneBe_results[2], 'HGNC:' + str(st.session_state.GeneBe_results[3]))
    
    user_input_1 = (f"The following diseases were found to be linked to the gene in interest: "
                    f"{st.session_state.disease_classification_dict}. Explain these diseases in depth, announce if a disease "
                    f"has been refuted, no need to explain that disease. If no diseases found reply with: No linked diseases found")
    st.session_state.reply = get_assistant_response_1(user_input_1)
    st.markdown(
        f"""
        <div class="justified-text">
            Assistant: {st.session_state.reply}
        </div>
        """,
        unsafe_allow_html=True,
    )

# FINAL CHATBOT
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
if chat_message := st.chat_input("I can help explain diseases!"):
    st.session_state["messages"].append({"role": "user", "content": chat_message})
    with st.chat_message("user"):
        st.write(chat_message)
    with st.chat_message("assistant"):
        with st.spinner("Processing your query..."):
            response = get_assistant_response(st.session_state["messages"])
            st.write(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})
