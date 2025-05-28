import streamlit as st
import os
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from tavily import TavilyClient
import json
import re
from urllib.parse import urlparse
from langchain_groq import ChatGroq
from bs4 import BeautifulSoup
import requests
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()

# --- Setup ---
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not TAVILY_API_KEY:
    st.error("TAVILY_API_KEY environment variable not set!")
    st.stop()
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY environment variable not set!")
    st.stop()

try:
    groq_llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama3-70b-8192")
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    st.error(f"Error initializing Groq or Tavily: {e}")
    st.stop()

price_extraction_parser = JsonOutputParser()
price_extraction_prompt_template = ChatPromptTemplate.from_messages([
    ("human", "From the following text and source URL, identify a product name, its numerical price, and the website URL where it is listed. Return ONLY a valid JSON object with the keys: 'name' (string), 'price' (number or null), and 'url' (string). The 'url' should be the specific link to buy or view the product. If the direct product URL isn't found in the text, use the provided source URL if it seems relevant. If no price is found, set 'price' to null. Do not include any extra text or comments."),
    ("human", "Text: '{text}'"),
    ("human", "Source URL: '{source_url}'"),
])
price_extraction_prompt = price_extraction_prompt_template.partial(format_instructions=price_extraction_parser.get_format_instructions())

specification_extraction_parser = JsonOutputParser()
specification_extraction_prompt_template = ChatPromptTemplate.from_messages([
    ("human", "From the following HTML content, extract the key specifications of the product like ram, storage, camera, battery, processor and prices with different specs. Structure any information about different storage and RAM configurations with their corresponding prices as a list of JSON objects under the key 'prices'. Each object in the list should have keys like 'Storage', 'RAM', and 'Price'. For other specifications, use key-value pairs. If a specification value contains a nested structure or multiple key-value pairs, format it as a valid JSON string within the main JSON value. If no specific product details are found, return an empty JSON object."),
    ("human", "HTML Content: '{html_content}'"),
])
specification_extraction_prompt = specification_extraction_prompt_template.partial(format_instructions=specification_extraction_parser.get_format_instructions())

def scrape_product_details(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return str(soup.get_text(separator='\n', strip=True)[:5000]) # Limit content to avoid overwhelming the LLM
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not retrieve content from {url}: {e}")
        return None

def find_json_in_string(text):
    main_match = re.search(r"\{.*\}", text, re.DOTALL)
    if main_match:
        try:
            main_json = json.loads(main_match.group(0))
            for key, value in main_json.items():
                if isinstance(value, str):
                    if (value.strip().startswith('{') and value.strip().endswith('}')) or \
                       (value.strip().startswith('[') and value.strip().endswith(']')):
                        try:
                            main_json[key] = json.loads(value)
                        except json.JSONDecodeError:
                            cleaned_value = value.replace("'", '"')
                            try:
                                main_json[key] = json.loads(cleaned_value)
                            except json.JSONDecodeError:
                                pass
                elif isinstance(value, list) and key.lower() == 'prices':
                    for item in value:
                        if isinstance(item, dict) and 'Price' in item:
                            price_str = item['Price']
                            if 'Not specified' in price_str:
                                item['Price'] = None  # Set price to None when "Not specified" is found
                            elif ' or ' in price_str:
                                prices = price_str.split(' or ')
                                for p in prices:
                                    numerical_match = re.search(r'(\d[\d,.]+)', p)
                                    if numerical_match:
                                        item['Price'] = numerical_match.group(1)
                                        break
                            else:
                                numerical_match = re.search(r'(\d[\d,.]+)', price_str)
                                if numerical_match:
                                    item['Price'] = numerical_match.group(1)
            return main_json
        except json.JSONDecodeError:
            return None
    return None

# --- LangGraph Definition ---
class AgentState(dict):
    product_name: str = None
    search_results: list = None
    extracted_data: list = None
    processed_results: list = None
    final_results: list = None

def search_products(state: AgentState):
    st.sidebar.info("Searching in Tavily")
    exclude_domains_list = ["olx.com.pk", "msn.com", "mistore.pk", "mobilegeeks.pk", "hamariweb.com", "daraz.pk"]
    include_domains_list = ["priceoye.pk"]
    st.info(f"Searching Tavily for '{state['product_name']}'...")
    search_results = tavily_client.search(query=f"{state['product_name']} buy pakistan best price",
                                          search_depth="advanced",
                                          exclude_domains=exclude_domains_list,
                                          # include_domains=include_domains_list
                                          )
    return {"search_results": search_results.get('results', [])}

def extract_price_data(state: AgentState):
    st.sidebar.info("Beautifying the results..")

    extracted_data = []
    if state.get("search_results"):
        st.info("Extracting price information...")
        for result in state['search_results']:
            try:
                chain = price_extraction_prompt | groq_llm | JsonOutputParser()
                output = chain.invoke({"text": result['content'], "source_url": result.get('url', '')})
                if isinstance(output, list):
                    # Handle the case where the parser returns a list (e.g., a JSON array)
                    if output:
                        extracted_data.append(output[0])
                    else:
                        extracted_data.append({}) # Append an empty dict if the list is empty
                else:
                    extracted_data.append(output)
            except Exception as e:
                st.warning(f"Could not process price from LLM for Tavily result: {e}")
    return {"extracted_data": extracted_data}

def process_and_sort_data(state: AgentState):
    priced_products = [
        item for item in state.get("extracted_data", [])
        if item.get("price") is not None and isinstance(item.get("price"), (int, float)) and item.get("url")
    ]
    # Filter out items with None prices before sorting
    valid_priced_products = [item for item in priced_products if item.get("price") is not None]
    valid_priced_products.sort(key=lambda x: x["price"])
    return {"processed_results": valid_priced_products}

def fetch_and_extract_specs(state: AgentState):
    final_results = []
    top_n_prices = state.get("processed_results", [])[:st.session_state.top_n]
    st.subheader(f"Top {len(top_n_prices)} Products with Prices and Specifications:")
    if top_n_prices:
        for item in top_n_prices:
            product_url = item['url']
            product_name_from_price = item['name']
            product_price = item['price']

            with st.spinner(f"Fetching specifications for '{product_name_from_price}' from {urlparse(product_url).netloc}..."):
                scraped_content = scrape_product_details(product_url)
                specifications = {}
                if scraped_content:
                    try:
                        specification_chain = specification_extraction_prompt | groq_llm
                        specification_output = specification_chain.invoke({"html_content": scraped_content})
                        specification_output_str = specification_output.content
                        specifications = find_json_in_string(specification_output_str) or {}
                    except Exception as e:
                        st.warning(f"Could not process specifications for '{urlparse(product_url).netloc}': {e}")
                else:
                    st.warning(f"Could not retrieve or process content for specifications from {product_url}")

                final_results.append({
                    "name": product_name_from_price,
                    "url": product_url,
                    "price": product_price,
                    "specifications": specifications
                })
    return {"final_results": final_results}

def display_results(state: AgentState):
    def display_specification_item(key, value, level=0):
        indent = "  " * level
        if key.lower() == 'prices' and isinstance(value, list):
            st.markdown(f"{indent}<li><strong>Prices:</strong></li>", unsafe_allow_html=True)
            st.markdown(f"{indent}<ul>", unsafe_allow_html=True)
            for price_config in value:
                if isinstance(price_config, dict):
                    details = []
                    for k, v in price_config.items():
                        if k.lower() == 'price' and v is None:
                            details.append(f"<strong>{k}:</strong> Not specified")
                        else:
                            details.append(f"<strong>{k}:</strong> {v}")
                    price_details = ", ".join(details)
                    st.markdown(f"{indent}  <li>{price_details}</li>", unsafe_allow_html=True)
                else:
                    st.markdown(f"{indent}  <li>{price_config}</li>", unsafe_allow_html=True) # Handle cases where the list might contain non-dicts
            st.markdown(f"{indent}</ul>", unsafe_allow_html=True)
        elif isinstance(value, dict):
            st.markdown(f"{indent}<li><strong>{key}:</strong></li>", unsafe_allow_html=True)
            st.markdown(f"{indent}<ul>", unsafe_allow_html=True)
            for k, v in value.items():
                display_specification_item(k, v, level + 1)
            st.markdown(f"{indent}</ul>", unsafe_allow_html=True)
        elif isinstance(value, list):
            st.markdown(f"{indent}<li><strong>{key}:</strong></li>", unsafe_allow_html=True)
            st.markdown(f"{indent}<ul>", unsafe_allow_html=True)
            for item in value:
                st.markdown(f"{indent}  <li>{item}</li>", unsafe_allow_html=True)
            st.markdown(f"{indent}</ul>", unsafe_allow_html=True)
        else:
            st.markdown(f"{indent}<li><strong>{key}:</strong> {value}</li>", unsafe_allow_html=True)

    if state.get("final_results"):
        for item in state['final_results']:
            st.markdown(
                f"<div style='border: 1px solid #e0e0e0; padding: 10px; margin-bottom: 10px; border-radius: 5px;'>"
                f"<strong>Product:</strong> {item['name']}<br>"
                f"<strong>Website:</strong> <a href='{item['url']}' target='_blank'>{item['url']}</a><br>"
                f"<strong>Price:</strong> <span style='color: green;'>Rs. {item['price']:.2f}</span><br>"
                f"<strong>Specifications:</strong>"
                f"<ul>",
                unsafe_allow_html=True
            )
            if item['specifications']:
                for key, value in item['specifications'].items():
                    display_specification_item(key, value)
            else:
                st.markdown("  <li>No specific details found.</li>", unsafe_allow_html=True)
            st.markdown(f"</ul></div>", unsafe_allow_html=True)
    else:
        st.info("Could not find relevant price and specification information.")
    return {}

# --- LangGraph Workflow ---
workflow = StateGraph(AgentState)
workflow.add_node("search", search_products)
workflow.add_node("extract_price", extract_price_data)
workflow.add_node("process_sort", process_and_sort_data)
workflow.add_node("fetch_specs", fetch_and_extract_specs)
workflow.add_node("display", display_results)

workflow.set_entry_point("search")
workflow.add_edge("search", "extract_price")
workflow.add_edge("extract_price", "process_sort")
workflow.add_edge("process_sort", "fetch_specs")
workflow.add_edge("fetch_specs", "display")
workflow.add_edge("display", END) # End the graph after displaying results

agent = workflow.compile()

# --- Streamlit UI ---
st.title("Find the best Prices With the help of AI")
st.sidebar.header("Search Options")
product_name = st.sidebar.text_input("Enter the product you are looking for:")
top_n=10
# top_n = st.sidebar.slider("Number of Top Results to Display:", min_value=1, max_value=10, value=6) # Reduced top_n for demonstration
st.session_state.top_n = top_n # Store top_n in session state for LangGraph

if product_name:
    with st.spinner(f"Searching for '{product_name}' in Pakistan..."):
        result = agent.invoke({"product_name": product_name})
        st.sidebar.subheader("Websites Searched:")
        searched_websites = set(urlparse(res['url']).netloc for res in result.get('search_results', []) if 'url' in res)
        if searched_websites:
            for website in sorted(list(searched_websites)):
                st.sidebar.markdown(f"- {website}")
        else:
            st.sidebar.info("No websites were searched.")
else:
    st.info("Enter a product name in the sidebar to start searching.")