MCP SQL Assistant
Ask your MySQL database questions in plain English. Get back optimized SQL and live results in your browser.

Natural language → SQL using a Groq LLM

Works with MySQL/XAMPP out of the box

MCP server for safe SQL execution

Streamlit UI for a quick, friendly experience

Project Overview
MCP SQL Assistant is an intelligent SQL assistant that combines a large language model (LLM) with live MySQL database querying.
It is built as a Streamlit web app that lets you ask natural language questions about your MySQL database and get immediate answers.

The app uses:

A Groq LLM backend (via API key) to understand your query and generate SQL.

A local MCP (Model Context Protocol) server to execute SQL on a MySQL database (e.g., XAMPP instance) in real time.

This means the LLM doesn’t just suggest SQL — it runs it on your data and shows the results.

What this does
You type:

"Show me all products with less than 10 in stock"

The app:

Reads your question

Asks the Groq LLM to generate MySQL-safe SQL

Runs it via the MCP server

Shows both the answer and the SQL used

Who this is for
Users who want to explore a MySQL database without writing SQL

Teams needing a quick UI for ad-hoc questions

Developers looking for an MCP + LLM + MySQL example


# 1) Clone the repo
git clone https://github.com/<your-username>/mcp_sql_assistant.git
cd mcp_sql_assistant

# 2) Create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure your keys and DB
cp .env.example .env
# Edit .env with:
# GROQ_API_KEY=your_groq_api_key
# DB_HOST=localhost
# DB_PORT=3306
# DB_NAME=mcp_proj1
# DB_USER=root
# DB_PASSWORD=

# 5) Make sure MySQL is running
# If using XAMPP, start Apache + MySQL and create the DB:
# CREATE DATABASE mcp_proj1;

# 6) Run the web app
streamlit run main.py
Example queries
"What tables are available in the database?"

"Show schema for inventory table"

"Generate DDL for all tables"

Requirements
Python 3.12+

MySQL (tested with XAMPP)

Valid GROQ_API_KEY

