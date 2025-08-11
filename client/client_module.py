#!/usr/bin/env python3
"""
Fixed client module for MCP SQL Assistant with XAMPP support
"""

import os
import re
import json
import asyncio
import logging
import subprocess
import sys
from typing import Dict, List, Any, Optional
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPSQLClient:
    """Client for interacting with MCP SQL Server"""
    
    def __init__(self, server_script_path: str = None):
        """Initialize the MCP SQL client"""
        if server_script_path is None:
            # Default path relative to current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            server_script_path = os.path.join(os.path.dirname(current_dir), "server", "mcp_server.py")
        
        self.server_script_path = server_script_path
        self.process = None
        
    async def start_server(self):
        """Start the MCP server process"""
        try:
            # Check if server file exists
            if not os.path.exists(self.server_script_path):
                logger.error(f"Server script not found: {self.server_script_path}")
                return False
            
            # Use Python executable from current environment
            python_exe = sys.executable
            cmd = [python_exe, self.server_script_path]
            
            logger.info(f"Starting MCP server with command: {' '.join(cmd)}")
            
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()  # Pass current environment
            )
            
            # Wait a moment and check if process is still running
            await asyncio.sleep(1)
            if self.process.returncode is not None:
                # Process died
                stderr_output = await self.process.stderr.read()
                error_msg = stderr_output.decode() if stderr_output else "Unknown error"
                logger.error(f"MCP server failed to start: {error_msg}")
                return False
            
            logger.info("MCP server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.process:
            logger.error("MCP server not started")
            return {"error": True, "result": "MCP server not started"}
        
        if parameters is None:
            parameters = {}
        
        # Create MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parameters
            }
        }
        
        try:
            # Send request to server
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(), 
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                return {"error": True, "result": "Request timeout"}
            
            if not response_line:
                return {"error": True, "result": "No response from server"}
            
            response = json.loads(response_line.decode())
            
            if "error" in response:
                return {"error": True, "result": str(response["error"])}
            else:
                # Handle both simple string responses and complex structures
                result = response.get("result", {})
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        return {"error": False, "result": content[0].get("text", "")}
                    else:
                        return {"error": False, "result": str(content)}
                else:
                    return {"error": False, "result": str(result)}
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from server: {e}")
            return {"error": True, "result": "Invalid response from server"}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": True, "result": str(e)}
    
    async def close(self):
        """Close the MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
                logger.info("MCP server closed")
            except asyncio.TimeoutError:
                logger.warning("MCP server did not close gracefully, killing process")
                self.process.kill()
                await self.process.wait()

class GroqLLMClient:
    """Client for interacting with GROQ LLM"""
    
    def __init__(self):
        """Initialize the GROQ client"""
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama3-8b-8192"  # Default model
    
    def extract_sql_queries(self, text: str) -> List[str]:
        """Extract SQL queries from text"""
        # Look for SQL code blocks
        sql_blocks = re.findall(r'```sql\n(.*?)\n```', text, re.DOTALL | re.IGNORECASE)
        
        # Also look for common SQL patterns
        sql_patterns = [
            r'\b(SELECT\b.*?(?=;|\n\n|\Z))',
            r'\b(INSERT\b.*?(?=;|\n\n|\Z))',
            r'\b(UPDATE\b.*?(?=;|\n\n|\Z))',
            r'\b(DELETE\b.*?(?=;|\n\n|\Z))',
            r'\b(CREATE\b.*?(?=;|\n\n|\Z))',
            r'\b(ALTER\b.*?(?=;|\n\n|\Z))',
            r'\b(DROP\b.*?(?=;|\n\n|\Z))',
            r'\b(SHOW\b.*?(?=;|\n\n|\Z))',
            r'\b(DESCRIBE\b.*?(?=;|\n\n|\Z))',
        ]
        
        queries = sql_blocks.copy()
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            queries.extend(matches)
        
        # Clean up queries
        cleaned_queries = []
        for query in queries:
            query = query.strip()
            if query and len(query) > 10:  # Filter out very short matches
                # Remove trailing semicolon and whitespace
                query = query.rstrip(';').strip()
                if query not in cleaned_queries:
                    cleaned_queries.append(query)
        
        return cleaned_queries
    
    async def generate_response(self, user_query: str, context: str = "") -> Dict[str, Any]:
        """Generate a response using GROQ LLM"""
        try:
            # Create system prompt specifically for XAMPP/MySQL database
            system_prompt = """You are an intelligent SQL database assistant for a MySQL database running on XAMPP. 

Based on the database schema provided, you have:
- inventory table: id, product_name, quantity, price
- sales table: sell_id, product_name, price, date

You help users by:
1. Understanding their natural language questions about the database
2. Suggesting appropriate SQL queries for MySQL/MariaDB
3. Providing clear explanations of database operations
4. Generating DDL statements when needed

When suggesting SQL queries, use MySQL/MariaDB syntax. Always provide helpful context and explanations."""

            # Add context if provided
            if context:
                system_prompt += f"\n\nCurrent Database Context:\n{context}"
            
            # Create the chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            
            response_text = response.choices[0].message.content
            
            # Extract SQL queries from the response
            sql_queries = self.extract_sql_queries(response_text)
            
            return {
                "error": False,
                "response": response_text,
                "sql_queries": sql_queries
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return {
                "error": True,
                "response": f"Error generating response: {str(e)}",
                "sql_queries": []
            }

async def run_llm_query_enhanced(user_query: str) -> Dict[str, Any]:
    """
    Enhanced function to process user queries with LLM and database integration
    """
    try:
        # Initialize clients
        llm_client = GroqLLMClient()
        mcp_client = MCPSQLClient()
        
        # Start MCP server
        logger.info("Starting MCP server...")
        server_started = await mcp_client.start_server()
        if not server_started:
            return {
                "error": True,
                "output": "Failed to start MCP server. Please ensure:\n1. XAMPP MySQL is running\n2. Database 'mcp_proj1' exists\n3. Server files are in correct locations\n4. Required Python packages are installed",
                "sql_queries": []
            }
        
        # Wait for server to initialize
        await asyncio.sleep(3)
        
        try:
            # Test connection first
            logger.info("Testing database connection...")
            test_result = await mcp_client.call_tool("test_connection")
            if test_result["error"]:
                return {
                    "error": True,
                    "output": f"Database connection failed: {test_result['result']}\n\nPlease ensure:\n1. XAMPP is running\n2. MySQL service is started\n3. Database 'mcp_proj1' exists",
                    "sql_queries": []
                }
            
            # Get database context
            logger.info("Getting database context...")
            context_result = await mcp_client.call_tool("get_table_info")
            database_context = ""
            if not context_result["error"]:
                database_context = f"Available tables and structure:\n{context_result['result']}"
            else:
                database_context = "Unable to retrieve table information"
            
            # Generate LLM response
            logger.info("Generating LLM response...")
            llm_response = await llm_client.generate_response(user_query, database_context)
            
            if llm_response["error"]:
                return {
                    "error": True,
                    "output": llm_response["response"],
                    "sql_queries": []
                }
            
            response_text = llm_response["response"]
            sql_queries = llm_response["sql_queries"]
            
            # Handle common queries directly
            query_lower = user_query.lower()
            
            if "table" in query_lower and ("list" in query_lower or "show" in query_lower):
                result = await mcp_client.call_tool("get_table_info")
                if not result["error"]:
                    response_text += f"\n\n**Current Tables in Database:**\n```\n{result['result']}\n```"
            
            elif "ddl" in query_lower or ("create" in query_lower and "table" in query_lower):
                if "complete" in query_lower or "database" in query_lower or "schema" in query_lower:
                    result = await mcp_client.call_tool("generate_database_schema")
                    if not result["error"]:
                        response_text += f"\n\n**Complete Database Schema:**\n```sql\n{result['result']}\n```"
                else:
                    # Generate DDL for individual tables
                    for table in ["inventory", "sales"]:
                        result = await mcp_client.call_tool("generate_table_ddl", {"table_name": table})
                        if not result["error"]:
                            response_text += f"\n\n**{table} Table DDL:**\n```sql\n{result['result']}\n```"
            
            # Execute suggested SQL queries
            if sql_queries:
                response_text += "\n\n**Executing Suggested Queries:**\n"
                
                for i, sql_query in enumerate(sql_queries, 1):
                    logger.info(f"Executing query {i}: {sql_query}")
                    result = await mcp_client.call_tool("run_query", {"query": sql_query})
                    
                    if not result["error"]:
                        response_text += f"\n**Query {i}:** `{sql_query}`\n"
                        response_text += f"**Result:**\n```\n{result['result']}\n```\n"
                    else:
                        response_text += f"\n**Query {i} (Error):** `{sql_query}`\n"
                        response_text += f"❌ **Error:** {result['result']}\n"
            
            return {
                "error": False,
                "output": response_text,
                "sql_queries": sql_queries
            }
            
        finally:
            # Always close the MCP client
            logger.info("Closing MCP client...")
            await mcp_client.close()
            
    except Exception as e:
        logger.error(f"Error in run_llm_query_enhanced: {e}")
        return {
            "error": True,
            "output": f"Unexpected error: {str(e)}\n\nTroubleshooting steps:\n1. Ensure XAMPP is running\n2. Check MySQL service is started\n3. Verify database 'mcp_proj1' exists\n4. Check GROQ_API_KEY in .env file",
            "sql_queries": []
        }

async def run_simple_query(user_query: str) -> Dict[str, Any]:
    """Simplified version for testing without MCP server"""
    try:
        llm_client = GroqLLMClient()
        response = await llm_client.generate_response(user_query)
        
        return {
            "error": response["error"],
            "output": response["response"] + "\n\n*Note: This is a simple response without database integration. For full functionality, ensure MCP server is running.*",
            "sql_queries": response["sql_queries"]
        }
    except Exception as e:
        return {
            "error": True,
            "output": f"Error: {str(e)}",
            "sql_queries": []
        }

# Test function
async def test_connection():
    """Test the connection and functionality"""
    try:
        print("🧪 Testing GROQ LLM connection...")
        llm_client = GroqLLMClient()
        response = await llm_client.generate_response("List the tables in the database")
        print(f"✅ LLM Response: {response['response'][:100]}...")
        
        print("\n🧪 Testing MCP Server connection...")
        mcp_client = MCPSQLClient()
        started = await mcp_client.start_server()
        if started:
            print("✅ MCP Server started")
            await asyncio.sleep(3)
            
            # Test database connection
            result = await mcp_client.call_tool("test_connection")
            print(f"🔌 Database connection: {result}")
            
            # Test table info
            result = await mcp_client.call_tool("get_table_info")
            print(f"📊 Table info: {result}")
            
            await mcp_client.close()
            print("✅ MCP Server closed")
        else:
            print("❌ Failed to start MCP server")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run test
    print("🚀 Running connection tests...")
    asyncio.run(test_connection())