from json.decoder import JSONDecodeError  # Import JSONDecodeError from json.decoder
import streamlit as st
import requests
from groq import Groq
import pandas as pd

disease_classification_dict = {"No diseases found"}
parts = []
GeneBe_results = ['-','-','-','-']
InterVar_results = ['-','-','-','-']
disease_labels = ['No disease found']
flag = False


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
        ),
    }
]


# Function to interact with Groq API for assistant responses
def get_assistant_response_initial(user_input):
    groq_messages = [{"role": "user", "content": user_input}]
    for message in initial_messages:
        groq_messages.insert(0, {"role": message["role"], "content": message["content"]})

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=groq_messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )

    return completion.choices[0].message.content

# Function to interact with Groq API for assistant responses
# Initialize the conversation history
SYSTEM = [
    {
        "role": "system",
        "content": (
            "You are a clinician assistant chatbot specializing in genomic research and variant analysis. "
            "Your task is to interpret user-provided genetic variant data, identify possible Mendelian diseases linked to genes."
        ),
    }
]

# Function to interact with Groq API for assistant responses
def get_assistant_response_1(user_input):
    # Add user input to conversation history
    full_message = SYSTEM + [{"role": "user", "content": user_input}]

    # Send conversation history to API
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
    

# Function to interact with Groq API for assistant responses
def get_assistant_response(user_input):
    # Add user input to conversation history
    full_message = SYSTEM + [{"role": "user", "content": user_input}]

    # Send conversation history to API
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


###################################################

# Function to parse variant information
def get_variant_info(message):
    global flag
    try:
        parts = message.split(',')
        if len(parts) == 5 and parts[1].isdigit():
            flag = True
            return parts
        else:
            #st.write("Message does not match a variant format, please try again by entering a genetic variant.")
            flag = False
            return []
    except Exception as e:
        st.write(f"Error while parsing variant: {e}")
        return []

# Main Streamlit interaction loop
user_input = st.text_input("Enter a genetic variant:")

if user_input:
    # Get assistant's response
    assistant_response = get_assistant_response_initial(user_input)
    st.write(f"Assistant: {assistant_response}")
    
    # Parse the variant if present
    parts = get_variant_info(assistant_response)
    
    if flag == True:

        #ACMG
        #GENEBE API
        # Define the API URL and parameters
        url = "https://api.genebe.net/cloud/api-public/v1/variant"
        params = {
                "chr": parts[0],
                "pos": parts[1],
                "ref": parts[2],
                "alt": parts[3],
                "genome": parts[4]
            }
    
        # Set the headers
        headers = {
                "Accept": "application/json"
            }
    
            # Make API request
        
        response = requests.get(url, headers=headers, params=params)
        
        
        if response.status_code == 200:
            try:
                data = response.json()
                variant = data["variants"][0]  # Get the first variant
                GeneBe_results[0] = variant.get("acmg_classification", "Not Available")
                GeneBe_results[1] = variant.get("effect", "Not Available")
                GeneBe_results[2] = variant.get("gene_symbol", "Not Available")
                GeneBe_results[3] = variant.get("gene_hgnc_id", "Not Available")
            except JSONDecodeError as E:
                pass
                    
        
        #INTERVAR API
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
                # Assuming the results contain ACMG classification and other details
                InterVar_results[0] = results.get("Intervar", "Not Available")
                InterVar_results[2] = results.get("Gene", "Not Available")
            except JSONDecodeError as E:
                pass

        #color of acmg classification
        def get_color(result):
            if result == "Pathogenic":
                return "red"
            elif result == "Likely pathogenic":
                return "red"
            elif result == "Uncertain significance":
                return "orange"
            elif result == "Likely benign":
                return "lightgreen"
            elif result == "Benign":
                return "green"
            else:
                return "black"  # Default color if no match
        
        # Get the color for the result
        result_color = get_color(GeneBe_results[0])
        
        # Display the ACMG results with the appropriate color
        st.markdown(f"### ACMG Results: <span style='color:{result_color}'>{GeneBe_results[0]}</span>", unsafe_allow_html=True)

        data = {
                     "Attribute": ["ACMG Classification", "Effect", "Gene Symbol", "Gene HGNC ID"],
                    "GeneBe Results": [GeneBe_results[0], GeneBe_results[1], GeneBe_results[2], GeneBe_results[3]],
                    "InterVar Results": [InterVar_results[0], InterVar_results[1], InterVar_results[2], InterVar_results[3]],
                    }
        st.table(data)


    
        #GENE-DISEASE DATABASE
        st.write("### ClinGen Gene-Disease Results")
        # Load the CSV file

        file_url = 'https://github.com/wah644/streamlit_app.py/blob/main/Clingen-Gene-Disease-Summary-2025-01-03.csv?raw=true'

        df = pd.read_csv(file_url)

            
       # Function to highlight the rows based on classification with 65% transparency
        def highlight_classification(row):
            color_map = {
                "Definitive": "color: rgba(66, 238, 66)",  # Green
                "Disputed": "color: rgba(255, 0, 0)",  # Red 
                "Moderate": "color: rgba(144, 238, 144)",  # Light Green 
                "Limited": "color: rgba(255, 204, 102)",  # Orange 
                "No Known Disease Relationship": "",
                "Strong": "color: rgba(66, 238, 66)",  #  Green 
                "Refuted": "color: rgba(255, 0, 0)"  # Red 
            }
            classification = row['CLASSIFICATION']
            return [color_map.get(classification, "")] * len(row)
            
        # Function to find matching gene symbol and HGNC ID
        def find_gene_match(gene_symbol, hgnc_id):
            global disease_labels
            global disease_classification_dict
            
            # Check if the gene symbol and HGNC ID columns exist in the data
            if 'GENE SYMBOL' in df.columns and 'GENE ID (HGNC)' in df.columns:
                # Filter rows matching the gene symbol and HGNC ID
                matching_rows = df[(df['GENE SYMBOL'] == gene_symbol) & (df['GENE ID (HGNC)'] == hgnc_id)]
                if not matching_rows.empty:
                    st.write(matching_rows.style.apply(highlight_classification, axis=1))
                    disease_classification_dict = dict(zip(matching_rows['DISEASE LABEL'], matching_rows['CLASSIFICATION']))
                else:
                    #st.write("No match found.")
                    st.markdown("<p style='color:red;'>No match found.</p>", unsafe_allow_html=True)
        
            else:
                st.write("No existing gene-disease match found")
        
        # Find and display the matching rows
        find_gene_match(GeneBe_results[2], 'HGNC:'+str(GeneBe_results[3]))
        
        # AI Tells me more
        user_input_1 = f"The following diseases were found to be linked to the gene in interest: {disease_classification_dict}. Explain these diseases in depth, announce if a disease has been refuted, no need to explain that disease.if no diseases found reply with: No linked diseases found "
        assistant_response_1 = get_assistant_response_1(user_input_1)
        st.markdown(
            f"""
            <div class="justified-text">
                Assistant: {assistant_response_1}
            </div>
            """,
            unsafe_allow_html=True,
        )

        
        #FINAL CHATBOT
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        # Display chat history
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        
        if chat_message := st.chat_input("I can help explain diseases!"):
            st.session_state["messages"].append({"role": "user", "content": chat_message})
            with st.chat_message("user"):
                st.write(chat_message)
        
            with st.chat_message("assistant"):
                with st.spinner("Processing your query..."):
                    response = get_assistant_response(chat_message)
                    st.write(response)
                    st.session_state["messages"].append({"role": "assistant", "content": response})
        
                
