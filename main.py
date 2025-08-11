import streamlit as st
import asyncio
import os
import sys
import traceback
from dotenv import load_dotenv

# Debug info
st.write("🐛 Debug Info:")
st.write(f"Working directory: {os.getcwd()}")

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
st.write(f"✅ Added to Python path: {current_dir}")

# Load environment variables
try:
    load_dotenv()
    st.write("✅ Environment variables loaded")
except Exception as e:
    st.error(f"❌ Failed to load .env: {e}")

# Create __init__.py files if they don't exist
init_files = [
    os.path.join(current_dir, "client", "__init__.py"),
    os.path.join(current_dir, "server", "__init__.py"),
    os.path.join(current_dir, "tools", "__init__.py")
]

for init_file in init_files:
    if not os.path.exists(init_file):
        try:
            os.makedirs(os.path.dirname(init_file), exist_ok=True)
            with open(init_file, 'w') as f:
                f.write("# This file makes Python treat the directory as a package\n")
            st.write(f"✅ Created: {init_file}")
        except Exception as e:
            st.error(f"❌ Failed to create {init_file}: {e}")

# Check required files
required_files = {
    "client_module.py": os.path.join(current_dir, "client", "client_module.py"),
    "mcp_server.py": os.path.join(current_dir, "server", "mcp_server.py"),
    "sql_tools.py": os.path.join(current_dir, "tools", "sql_tools.py")
}

missing_files = []
for file_name, file_path in required_files.items():
    exists = os.path.exists(file_path)
    st.write(f"{file_name} exists: {exists}")
    if not exists:
        missing_files.append(file_name)

if missing_files:
    st.error(f"❌ Missing required files: {', '.join(missing_files)}")
    st.info("Please ensure all required files are in place before running the application.")

# Try to import the function
run_llm_query_enhanced = None
run_simple_query = None

try:
    # Import the enhanced query function
    from client.client_module import run_llm_query_enhanced, run_simple_query
    st.write("✅ Successfully imported LLM query functions")
except ImportError as e:
    st.error(f"❌ Failed to import functions: {e}")
    
    # Try alternative import methods
    try:
        import importlib.util
        client_file_path = os.path.join(current_dir, "client", "client_module.py")
        spec = importlib.util.spec_from_file_location("client_module", client_file_path)
        if spec and spec.loader:
            client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(client_module)
            run_llm_query_enhanced = getattr(client_module, 'run_llm_query_enhanced', None)
            run_simple_query = getattr(client_module, 'run_simple_query', None)
            st.write("✅ Imported using importlib")
        else:
            raise ImportError("Could not create module spec")
    except Exception as e2:
        st.error(f"❌ Alternative import also failed: {e2}")
        st.info("Please check that the client_module.py file contains the required functions.")

# Page configuration
st.set_page_config(
    page_title="MCP SQL Assistant",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 MCP SQL Assistant")
st.markdown("Ask questions about your database and get intelligent answers!")

# Check environment variables
groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    st.error("⚠️ GROQ_API_KEY not found! Please set it in your .env file.")
    st.code("GROQ_API_KEY=your_groq_api_key_here")
else:
    st.success("✅ GROQ_API_KEY configured")

# Database connection info
with st.sidebar:
    st.header("🔗 Connection Status")
    
    # Check if functions are available
    if run_llm_query_enhanced:
        st.success("✅ Enhanced query function available")
    elif run_simple_query:
        st.warning("⚠️ Only simple query function available")
    else:
        st.error("❌ No query functions available")
    
    st.header("Database Info")
    st.info("📊 Database: mysql://localhost/mcp_proj1")
    
    st.header("💡 Sample Questions")
    st.markdown("""
    **Basic Questions:**
    - What tables are available in the database?
    - Show me the schema of any table
    
    **DDL Generation:**
    - Generate CREATE TABLE statement for a table
    - Generate complete database schema DDL
    
    **Data Analysis:**
    - What data is available in the database?
    - Show me sample data from tables
    """)

# Main query interface
st.header("Ask Your Question")

# Initialize session state
if 'query' not in st.session_state:
    st.session_state.query = ''

# Predefined questions for quick testing
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📋 List Tables"):
        st.session_state.query = "What tables are available in the database?"
with col2:
    if st.button("📊 Table Schema"):
        st.session_state.query = "Show me the schema information for all tables"
with col3:
    if st.button("🔍 Sample Data"):
        st.session_state.query = "Show me a few sample records from the database"
with col4:
    if st.button("🏗️ Generate DDL"):
        st.session_state.query = "Generate complete database schema DDL for all tables"

# Text input for custom queries
query = st.text_input(
    "Or ask your own question:",
    value=st.session_state.query,
    placeholder="e.g., What tables do I have in my database?",
    key="query_input"
)

# Update session state
if query != st.session_state.query:
    st.session_state.query = query

# Process query if available
if query and (run_llm_query_enhanced or run_simple_query):
    with st.spinner("🤔 Processing your question..."):
        try:
            # Choose which function to use
            if run_llm_query_enhanced and groq_key:
                st.info("🚀 Using enhanced LLM query with database integration")
                result = asyncio.run(run_llm_query_enhanced(query))
            elif run_simple_query and groq_key:
                st.info("⚡ Using simple LLM query (no database integration)")
                result = asyncio.run(run_simple_query(query))
            else:
                st.error("❌ No suitable query function available or API key missing")
                st.stop()
            
            if result["error"]:
                st.error(f"❌ Error occurred:")
                st.code(result['output'])
                
                # Show debugging information
                with st.expander("🔧 Troubleshooting"):
                    st.markdown("**Possible solutions:**")
                    st.markdown("""
                    1. **Database Connection**: Ensure MySQL is running on localhost
                    2. **MCP Server**: Check if the MCP server script exists and is executable
                    3. **Dependencies**: Verify all Python packages are installed
                    4. **API Key**: Ensure GROQ_API_KEY is valid and has credits
                    """)
                    
                    st.markdown("**Quick fixes:**")
                    st.code("""
# Install dependencies
pip install groq langchain-community sqlalchemy pymysql python-dotenv

# Check database connection
mysql -u root -p -h localhost

# Verify file structure
ls -la client/
ls -la server/
ls -la tools/
                    """)
            else:
                # Display successful results
                st.success("✅ Query processed successfully!")
                
                # Create tabs for organized display
                if result.get("sql_queries"):
                    tab1, tab2, tab3 = st.tabs(["🤖 AI Response", "🔍 SQL Queries", "📊 Summary"])
                else:
                    tab1, tab2 = st.tabs(["🤖 AI Response", "📊 Summary"])
                
                with tab1:
                    st.markdown("### AI Assistant Response:")
                    st.markdown(result["output"])
                
                if result.get("sql_queries"):
                    with tab2:
                        st.markdown("### Generated SQL Queries:")
                        for i, sql_query in enumerate(result["sql_queries"], 1):
                            st.markdown(f"**Query {i}:**")
                            st.code(sql_query, language="sql")
                
                # Summary tab
                summary_tab = tab3 if result.get("sql_queries") else tab2
                with summary_tab:
                    st.markdown("### Processing Summary:")
                    st.info(f"✅ Query processed successfully")
                    st.info(f"🔢 SQL queries generated: {len(result.get('sql_queries', []))}")
                    st.info(f"📝 Response length: {len(result['output'])} characters")
                    
                    # Show function used
                    if run_llm_query_enhanced and groq_key:
                        st.info("🎯 Used: Enhanced LLM + Database integration")
                    else:
                        st.info("🎯 Used: Simple LLM query")
                
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            
            # Show detailed error information
            with st.expander("🔍 Error Details"):
                st.code(traceback.format_exc())
                
            # Suggest solutions
            st.markdown("**Try these solutions:**")
            st.markdown("""
            1. Restart the Streamlit application
            2. Check that all files are in the correct directories
            3. Verify your .env file contains GROQ_API_KEY
            4. Ensure database server is running
            """)

elif query:
    st.warning("⚠️ Cannot process query: Required functions not available")
    st.info("Please check the import errors shown above and ensure all files are properly configured.")

# System information and testing
with st.expander("🔧 System Information & Testing"):
    st.header("Environment Check")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Python Environment")
        st.write(f"Python version: {sys.version}")
        st.write(f"Working directory: {os.getcwd()}")
        
        # Check required packages
        required_packages = ['streamlit', 'groq', 'sqlalchemy', 'pymysql', 'python-dotenv', 'langchain-community']
        st.write("**Package Status:**")
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                st.write(f"✅ {package}")
            except ImportError:
                st.write(f"❌ {package} (not installed)")
    
    with col2:
        st.subheader("File Structure")
        if st.button("Show Directory Structure"):
            st.write("**Project Structure:**")
            try:
                for root, dirs, files in os.walk(current_dir):
                    # Only show first 2 levels to avoid clutter
                    level = root.replace(current_dir, '').count(os.sep)
                    if level < 3:
                        indent = '  ' * level
                        st.write(f"{indent}{os.path.basename(root)}/")
                        subindent = '  ' * (level + 1)
                        for file in files[:10]:  # Limit files shown
                            st.write(f"{subindent}{file}")
                        if len(files) > 10:
                            st.write(f"{subindent}... and {len(files) - 10} more files")
            except Exception as e:
                st.error(f"Error listing files: {e}")
    
    # Test functions if available
    if st.button("🧪 Test Functions"):
        st.write("**Function Availability Test:**")
        
        if run_llm_query_enhanced:
            st.write("✅ run_llm_query_enhanced available")
        else:
            st.write("❌ run_llm_query_enhanced not available")
            
        if run_simple_query:
            st.write("✅ run_simple_query available")
        else:
            st.write("❌ run_simple_query not available")
        
        # Test GROQ connection
        if groq_key:
            try:
                st.write("Testing GROQ API connection...")
                # This would be a simple test - for now just check if key exists
                st.write("✅ GROQ API key found")
            except Exception as e:
                st.write(f"❌ GROQ API test failed: {e}")

# Footer
st.markdown("---")
st.markdown("💡 **Tip**: If you're experiencing issues, try restarting the application or checking the troubleshooting section above.")