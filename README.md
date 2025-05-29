# 🔍 AI Product Price Search Assistant

An intelligent product price search assistant that helps you find the best prices and deals across multiple websites using AI. Built with **Groq**, **Tavily**, **BeautifulSoup (BS4)**, and **LangGraph** for seamless web scraping, query understanding, and multi-agent orchestration.

---

## ✨ Features

- 🔎 Natural language product price search across multiple e-commerce sites  
- 🌐 Automated web scraping with BeautifulSoup for dynamic price extraction  
- 🤖 Multi-agent orchestration using LangGraph and Groq for robust task management  
- 🧠 AI-powered query interpretation and result summarization  
- ⚡ Fast, real-time price comparison and deal discovery  
- 📄 Detailed source attribution (which website each price comes from)  
- 🔄 Caching of repeated queries to improve performance  

---

## 🧰 Tech Stack

| Component           | Technology                                  |
|---------------------|---------------------------------------------|
| 🤖 Language Model    | [Groq](https://groq.com/) with `ChatGroq`  |
| 🕸️ Web Scraping     | [BeautifulSoup (BS4)](https://www.crummy.com/software/BeautifulSoup/) |
| 🌐 Search API       | [Tavily](https://tavily.com/) for web search results |
| 🔗 Agent Orchestration | [LangGraph](https://langgraph.com/)        |
| 🖥️ UI Framework     | Streamlit (optional for UI)                  |

---

## 🚀 Getting Started

### 1. Clone the Repository

    git clone https://github.com/yourusername/ai-product-price-search.git
    cd ai-product-price-search

### 2. Install Requirements

    pip install -r requirements.txt

### 3. Set Environment Variables

Create a `.env` file with the following keys:

    GROQ_API_KEY=your_groq_api_key
    TAVILY_API_KEY=your_tavily_api_key

Add any other config as needed for your environment.

### 4. Run the App (if applicable)

For example, if you have a Streamlit UI:

    streamlit run app.py

---

## 💬 Usage

- Enter a product name or description in natural language, e.g.,  
  "Find the best price for Apple AirPods Pro 2nd generation."  
- The assistant queries multiple sources via Tavily and scrapes selected websites using BeautifulSoup.  
- Groq and LangGraph orchestrate agents to interpret, fetch, aggregate, and summarize results.  
- View a ranked list of prices with source URLs and timestamps.  
- Optionally cache results for faster repeated queries.  

---

## 🧠 Architecture Overview

    User Query (Text)
            ↓
    LangGraph Orchestrator
            ↓
     ├─ Groq LLM Agent (query interpretation & summarization)
     ├─ Tavily Search Agent (web search API)
     ├─ BS4 Scraping Agent (extract prices from HTML)
            ↓
    Aggregated Results & Ranking
            ↓
    User Output (with source links)

---

## 📁 Project Structure

    ai-product-price-search/
    ├── agents/               # LangGraph and Groq agent logic
    ├── scraping/             # BeautifulSoup scraping utilities
    ├── tavily_api/           # Tavily integration modules
    ├── ui/                   # (Optional) Streamlit or other UI components
    ├── app.py                # Main entry point (UI or CLI)
    ├── requirements.txt
    └── .env.example          # Example environment variables

---

## 🛡️ Security Notice

- Never commit API keys or tokens to version control.  
- Use `.env` files or environment variables securely.  
- Validate and sanitize all web-scraped data before use.  

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

    git checkout -b feature/your-feature-name

---

## 👨‍💻 Author

Built with ❤️ by [Ahmad](https://github.com/malikahmadmukhtar)
