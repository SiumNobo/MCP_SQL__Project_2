#!/usr/bin/env python3
"""
Fixed MCP Server for XAMPP MySQL setup
"""
import sys
import os
import logging
import json

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
    logger.info("Successfully imported FastMCP")
except ImportError as e:
    logger.error(f"Failed to import FastMCP: {e}")
    # Fallback: create a simple server class
    class FastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = {}
            
        def tool(self, name):
            def decorator(func):
                self.tools[name] = func
                return func
            return decorator
            
        def run(self, transport="stdio"):
            logger.info(f"Starting simple MCP server: {self.name}")
            # Simple stdio loop
            while True:
                try:
                    line = input()
                    if line.strip():
                        self.process_request(line)
                except EOFError:
                    break
                except Exception as e:
                    logger.error(f"Error in server loop: {e}")
                    
        def process_request(self, request_line):
            try:
                request = json.loads(request_line)
                method = request.get('method', '')
                
                if method == 'tools/call':
                    tool_name = request['params']['name']
                    args = request['params'].get('arguments', {})
                    
                    if tool_name in self.tools:
                        result = self.tools[tool_name](**args)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get('id'),
                            "result": {
                                "content": [{"type": "text", "text": result}]
                            }
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get('id'),
                            "error": {"code": -1, "message": f"Tool {tool_name} not found"}
                        }
                        
                    print(json.dumps(response))
                    
            except Exception as e:
                logger.error(f"Error processing request: {e}")

# Import SQL tools
try:
    from tools.sql_tools import SQLQueryTool
    logger.info("Successfully imported SQLQueryTool")
except ImportError as e:
    logger.error(f"Failed to import SQLQueryTool: {e}")
    sys.exit(1)

# Create the MCP server
mcp = FastMCP("sql")

# Initialize SQL tool with XAMPP MySQL connection
try:
    # XAMPP MySQL connection string
    # db_uri = "mysql+pymysql://root:@localhost/mcp_proj1"
    # sql_tool = SQLQueryTool(db_uri=db_uri)
    # logger.info("SQL tool initialized successfully with XAMPP MySQL")        
    sql_tool = SQLQueryTool(db_uri="mysql+pymysql://root:@localhost/mcp_proj1")
    logger.info("SQL tool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SQL tool: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize SQL tool: {e}")
    # Try alternative connection strings
    alternative_uris = [
        "mysql+pymysql://root@localhost:3306/mcp_proj1",
        "mysql+pymysql://root:@127.0.0.1:3306/mcp_proj1",
        "mysql+pymysql://root@127.0.0.1:3306/mcp_proj1"
    ]
    
    for uri in alternative_uris:
        try:
            logger.info(f"Trying alternative URI: {uri}")
            sql_tool = SQLQueryTool(db_uri=uri)
            logger.info(f"Successfully connected with URI: {uri}")
            break
        except Exception as e2:
            logger.error(f"Failed with URI {uri}: {e2}")
            continue
    else:
        logger.error("All connection attempts failed")
        sys.exit(1)

@mcp.tool(name="run_query")
def run_query(query: str) -> str:
    """Execute a SQL query and return the results"""
    try:
        logger.info(f"Executing query: {query}")
        result = sql_tool.run_query(query)
        logger.info("Query executed successfully")
        return str(result)
    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool(name="get_table_info")
def get_table_info(table_name: str = None) -> str:
    """Get information about database tables"""
    try:
        if table_name:
            result = sql_tool.get_table_info(table_name)
        else:
            result = sql_tool.get_all_tables()
        return str(result)
    except Exception as e:
        error_msg = f"Error getting table info: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool(name="get_last_query")
def get_last_query() -> str:
    """Get the last executed SQL query and its result"""
    try:
        query_info = sql_tool.get_last_query()
        return f"Last Query: {query_info['query']}\n\nResult: {query_info['result']}"
    except Exception as e:
        error_msg = f"Error getting last query: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool(name="generate_table_ddl")
def generate_table_ddl(table_name: str) -> str:
    """Generate CREATE TABLE DDL statement for a specific table"""
    try:
        logger.info(f"Generating DDL for table: {table_name}")
        result = sql_tool.generate_table_ddl(table_name)
        logger.info("DDL generated successfully")
        return str(result)
    except Exception as e:
        error_msg = f"Error generating table DDL: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool(name="generate_database_schema")
def generate_database_schema(database_name: str = None) -> str:
    """Generate complete database schema DDL for all tables"""
    try:
        logger.info(f"Generating database schema DDL")
        result = sql_tool.generate_database_schema(database_name)
        logger.info("Database schema DDL generated successfully")
        return str(result)
    except Exception as e:
        error_msg = f"Error generating database schema: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool(name="test_connection")
def test_connection() -> str:
    """Test database connection"""
    try:
        result = sql_tool.run_query("SELECT 1 as test")
        return f"Connection successful: {result}"
    except Exception as e:
        return f"Connection failed: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting MCP SQL server for XAMPP...")
    try:
        # Test connection first
        test_result = test_connection()
        logger.info(f"Connection test result: {test_result}")
        
        # Start the server
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)