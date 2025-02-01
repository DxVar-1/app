from json.decoder import JSONDecodeError  
import streamlit as st
import requests
from groq import Groq
import pandas as pd
from bs4 import BeautifulSoup

st.set_page_config(page_title="DxVar", layout="centered")
st.title("DxVar")

# Load API Key from Streamlit Secrets
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Function to fetch SNP details (chromosome, position, allele options) from NCBI
def fetch_snp_info(snp_id):
    url = f"https://www.ncbi.nlm.nih.gov/snp/{snp_id}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extracting Alleles
        allele_section = soup.find(string="Alleles")
        if allele_section:
            parent_element = allele_section.find_parent()
            if parent_element:
                allele_text = parent_element.find_next_sibling().text
                alleles = [allele.strip() for allele in allele_text.split('/') if allele.strip()]
        
        # Extracting Chromosome and Position
        position_section = soup.find(string="GRCh38")
        if position_section:
            parent_element = position_section.find_parent()
            if parent_element:
                chrom_pos_text = parent_element.find_next_sibling().text
                chrom, pos = chrom_pos_text.split(':')
                return chrom.strip(), pos.strip(), alleles
    return None

# Function to interact with Groq AI for responses
def get_assistant_response(user_input):
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

# Function to query GeneBe API for variant classification
def fetch_gene_classification(chrom, pos, ref, alt):
    url = "https://api.genebe.net/cloud/api-public/v1/variant"
    params = {
        "chr": chrom,
        "pos": pos,
        "ref": ref,
        "alt": alt,
        "genome": "hg38"
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

# Main Streamlit Interaction
user_input = st.text_input("Enter a genetic variant (ex: chr6:160585140-T>G or rs123456)")

if user_input:
    if user_input.lower().startswith("rs"):  # SNP Handling
        snp_id = user_input.strip()
        snp_data = fetch_snp_info(snp_id)
        
        if snp_data:
            chrom, pos, alleles = snp_data
            st.success(f"Resolved {snp_id} to Chromosome: {chrom}, Position: {pos}, Alleles: {', '.join(alleles)}")
            selected_allele = st.selectbox("Select a reference allele:", alleles)
            alt_allele = st.selectbox("Select an alternate allele:", alleles)

            if st.button("Proceed with Variant Interpretation"):
                formatted_variant = f"{chrom},{pos},{selected_allele},{alt_allele},hg38"
                st.write(f"Proceeding with variant: {formatted_variant}")

                # Fetch classification
                gene_data = fetch_gene_classification(chrom, pos, selected_allele, alt_allele)
                
                if gene_data:
                    st.write("### ACMG Classification Results:")
                    st.table(gene_data)  # Display ACMG classification

                    # AI Explanation
                    ai_input = f"Explain the genetic variant: {formatted_variant}"
                    ai_response = get_assistant_response(ai_input)
                    st.write("### AI Explanation:")
                    st.write(ai_response)
                else:
                    st.error("No classification data found for this variant.")
        else:
            st.error(f"Could not retrieve SNP details for {snp_id}.")
    
    else:  # Direct Variant Handling
        parts = user_input.split(',')
        if len(parts) == 5:
            chrom, pos, ref, alt, genome = parts
            st.write(f"Processing variant: {chrom}-{pos}-{ref}>{alt} ({genome})")

            # Fetch classification
            gene_data = fetch_gene_classification(chrom, pos, ref, alt)
            
            if gene_data:
                st.write("### ACMG Classification Results:")
                st.table(gene_data)  # Display ACMG classification

                # AI Explanation
                ai_input = f"Explain the genetic variant: {chrom},{pos},{ref},{alt},{genome}"
                ai_response = get_assistant_response(ai_input)
                st.write("### AI Explanation:")
                st.write(ai_response)
            else:
                st.error("No classification data found for this variant.")
        else:
            st.warning("Invalid variant format. Please enter a valid variant.")

