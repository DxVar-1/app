from json.decoder import JSONDecodeError  
import streamlit as st
import requests
from groq import Groq
import pandas as pd

# Set up Streamlit UI
st.set_page_config(page_title="DxVar", layout="centered")

st.title("DxVar")

# Load API key from Streamlit secrets
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Function to fetch SNP information (alleles, chromosome, position) from Ensembl API
def fetch_snp_info(rs_id):
    """
    Fetches SNP allele information from Ensembl REST API.
    Returns: (chromosome, position, ref_allele, alt_allele, genome_build)
    """
    url = f"https://rest.ensembl.org/variation/human/{rs_id}?content-type=application/json"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if "mappings" in data and len(data["mappings"]) > 0:
            mapping = data["mappings"][0]  # Take first mapping result
            chrom = mapping["location"].split(":")[0]
            pos = mapping["location"].split(":")[1]
            alleles = mapping.get("allele_string", "N/A").split("/")
            ref = alleles[0] if len(alleles) > 0 else "N/A"
            alt = alleles[1] if len(alleles) > 1 else "N/A"
            
            return chrom, pos, ref, alt, "hg38"  # Default genome build
    return None  # Return None if no valid data is found


# Function to parse user input (either variant or rsID)
def get_variant_info(message):
    """
    Parses user input for genetic variants.
    Supports:
    - Direct variant input (chr6:160585140-T>G)
    - SNP rsID input (rs123456), which is converted to variant format.
    """
    
    # If input is an rsID (e.g., "rs123456")
    if message.lower().startswith("rs") and message[2:].isdigit():
        snp_data = fetch_snp_info(message)  # Fetch SNP info
        if snp_data:
            st.success(f"SNP {message} resolved to variant: {snp_data}")
            return snp_data  # Process SNP as variant
        else:
            st.error(f"Could not find details for {message}. Try another SNP ID.")
            return None

    # If not rsID, assume it's a direct variant format
    parts = message.split(',')
    if len(parts) == 5 and parts[1].isdigit():
        return parts  # Return variant details if valid format

    st.warning("Invalid input. Please enter a valid genetic variant or SNP ID.")
    return None  # Return None if format is invalid


# Function to interact with Groq API for assistant responses
def get_assistant_response(user_input):
    """
    Uses Groq API to provide genomic explanations and disease associations.
    """
    messages = [
        {"role": "system", "content": "You are an AI assistant specializing in genomic research and variant analysis."},
        {"role": "user", "content": user_input}
    ]
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    return completion.choices[0].message.content


# Function to get variant classification from GeneBe API
def fetch_gene_classification(parts):
    """
    Queries GeneBe API for ACMG classification and variant effect.
    """
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
            variant = data["variants"][0]  
            return {
                "ACMG Classification": variant.get("acmg_classification", "Not Available"),
                "Effect": variant.get("effect", "Not Available"),
                "Gene Symbol": variant.get("gene_symbol", "Not Available"),
                "HGNC ID": variant.get("gene_hgnc_id", "Not Available"),
                "dbSNP": variant.get("dbsnp", "Not Available"),
                "Frequency in Population": variant.get("frequency_reference_population", "Not Available"),
                "ACMG Score": variant.get("acmg_score", "Not Available"),
                "ACMG Criteria": variant.get("acmg_criteria", "Not Available"),
            }
        except JSONDecodeError:
            return None

    return None


# Main Streamlit interaction loop
if "last_input" not in st.session_state:
    st.session_state.last_input = ""

user_input = st.text_input("Enter a genetic variant (ex: chr6:160585140-T>G or rs123456)")

if user_input != st.session_state.last_input:
    st.session_state.last_input = user_input
    parts = get_variant_info(user_input)  # Parse variant
    
    if parts:
        st.write(f"Processing variant: {parts}")
        
        # Fetch variant classification
        gene_data = fetch_gene_classification(parts)
        
        if gene_data:
            st.write("### ACMG Classification Results:")
            st.table(gene_data)  # Display ACMG classification

            # Use AI to explain the variant
            ai_input = f"Explain the genetic variant: {parts}"
            ai_response = get_assistant_response(ai_input)
            st.write("### AI Explanation:")
            st.write(ai_response)
        else:
            st.error("No classification data found for this variant.")
    else:
        st.warning("Please enter a valid variant or SNP ID.")

