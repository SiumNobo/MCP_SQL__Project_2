#new code
    
import logging
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool, InfoSQLDatabaseTool, ListSQLDatabaseTool
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class SQLQueryTool:
    def __init__(self, db_uri: str):
        """Initialize SQL query tool with database connection"""
        try:
            self.db_uri = db_uri
            self.db = SQLDatabase.from_uri(db_uri)
            self.executed_queries = []  # Track executed queries
            self.last_query = None      # Store the last executed query
            self.last_result = None     # Store the last query result
            
            # Test the connection
            self._test_connection()
            logger.info(f"Successfully connected to database: {db_uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to database {db_uri}: {e}")
            raise

    def _test_connection(self):
        """Test database connection"""
        try:
            # Simple test query
            with self.db._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
        except SQLAlchemyError as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    def run_query(self, query: str) -> str:
        """Execute a SQL query and return results"""
        try:
            # Store the query for tracking
            self.last_query = query.strip()
            logger.info(f"Executing SQL query: {self.last_query}")
            
            tool = QuerySQLDataBaseTool(db=self.db)
            result = tool.run(query)
            
            # Store the result
            self.last_result = result
            
            # Add to executed queries list
            self.executed_queries.append({
                'query': self.last_query,
                'result': result,
                'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                    name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
                ))
            })
            
            # Keep only last 10 queries to avoid memory issues
            if len(self.executed_queries) > 10:
                self.executed_queries = self.executed_queries[-10:]
                
            logger.info("Query executed successfully")
            return result
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            logger.error(error_msg)
            self.last_query = query.strip()
            self.last_result = error_msg
            return error_msg

    def get_table_info(self, table_name: str) -> str:
        """Get information about a specific table"""
        try:
            tool = InfoSQLDatabaseTool(db=self.db)
            result = tool.run(table_name)
            return result
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return f"Error getting table info: {str(e)}"

    def get_all_tables(self) -> str:
        """Get list of all tables in the database"""
        try:
            tool = ListSQLDatabaseTool(db=self.db)
            result = tool.run("")
            return result
        except Exception as e:
            logger.error(f"Failed to get table list: {e}")
            return f"Error getting table list: {str(e)}"

    def get_schema_info(self) -> str:
        """Get comprehensive schema information"""
        try:
            # Get all tables
            tables = self.get_all_tables()
            
            # Get schema for each table
            schema_info = f"Database Tables:\n{tables}\n\nTable Schemas:\n"
            
            # Extract table names and get their info
            table_lines = tables.split('\n')
            for line in table_lines:
                if line.strip() and not line.startswith('Database Tables'):
                    table_name = line.strip()
                    if table_name:
                        table_info = self.get_table_info(table_name)
                        schema_info += f"\n--- {table_name} ---\n{table_info}\n"
            
            return schema_info
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return f"Error getting schema info: {str(e)}"

    # NEW DDL GENERATION METHODS
    def generate_table_ddl(self, table_name: str) -> str:
        """Generate CREATE TABLE DDL for a specific table"""
        try:
            query = f"SHOW CREATE TABLE {table_name}"
            result = self.run_query(query)
            
            # Extract the CREATE TABLE statement from the result
            if "CREATE TABLE" in result:
                # The result typically contains the table name and create statement
                lines = result.split('\n')
                create_statement = ""
                for line in lines:
                    if 'CREATE TABLE' in line:
                        # Find the actual CREATE statement
                        parts = line.split('\t')
                        if len(parts) > 1:
                            create_statement = parts[1]
                        break
                
                if create_statement:
                    return f"-- DDL for table: {table_name}\n{create_statement};"
                else:
                    return result
            else:
                return result
                
        except Exception as e:
            error_msg = f"Error generating DDL for table {table_name}: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def generate_database_schema(self, database_name: str = None) -> str:
        """Generate complete database schema DDL"""
        try:
            if not database_name:
                # Extract database name from connection URI
                database_name = self.db_uri.split('/')[-1]
            
            schema_ddl = f"-- Complete Database Schema for: {database_name}\n"
            schema_ddl += f"-- Generated DDL Statements\n\n"
            
            # Get all tables
            tables_result = self.get_all_tables()
            table_names = []
            
            # Parse table names from the result
            for line in tables_result.split('\n'):
                line = line.strip()
                if line and not line.startswith('Database Tables') and line != '':
                    table_names.append(line)
            
            # Generate DDL for each table
            for table_name in table_names:
                if table_name:
                    ddl = self.generate_table_ddl(table_name)
                    schema_ddl += f"\n{ddl}\n"
            
            return schema_ddl
            
        except Exception as e:
            error_msg = f"Error generating database schema: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def create_table_like(self, source_table: str, new_table: str) -> str:
        """Create a new table with the same structure as an existing table"""
        try:
            query = f"CREATE TABLE {new_table} LIKE {source_table}"
            result = self.run_query(query)
            return f"Table '{new_table}' created successfully with structure like '{source_table}'"
        except Exception as e:
            error_msg = f"Error creating table {new_table} like {source_table}: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def get_all_tables_detailed_info(self, database_name: str = None) -> str:
        """Get detailed information about all tables in the database"""
        try:
            if not database_name:
                database_name = self.db_uri.split('/')[-1]
            
            query = f"""
            SELECT 
                TABLE_NAME,
                TABLE_ROWS,
                DATA_LENGTH,
                INDEX_LENGTH,
                CREATE_TIME,
                UPDATE_TIME,
                ENGINE,
                TABLE_COLLATION
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = '{database_name}'
            ORDER BY TABLE_NAME
            """
            
            result = self.run_query(query)
            return f"Detailed Table Information for database '{database_name}':\n{result}"
            
        except Exception as e:
            error_msg = f"Error getting detailed table info: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def export_database_structure(self, include_data: bool = False) -> str:
        """Export complete database structure and optionally data"""
        try:
            export_script = "-- Database Export Script\n"
            export_script += f"-- Connection: {self.db_uri}\n"
            export_script += "-- " + "="*50 + "\n\n"
            
            # Get schema DDL
            schema_ddl = self.generate_database_schema()
            export_script += schema_ddl
            
            if include_data:
                export_script += "\n-- DATA EXPORT\n"
                export_script += "-- " + "="*30 + "\n\n"
                
                # Get all tables
                tables_result = self.get_all_tables()
                table_names = []
                
                for line in tables_result.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Database Tables') and line != '':
                        table_names.append(line)
                
                # Generate INSERT statements for each table
                for table_name in table_names:
                    if table_name:
                        data_query = f"SELECT * FROM {table_name} LIMIT 100"  # Limit to avoid huge exports
                        data_result = self.run_query(data_query)
                        export_script += f"\n-- Data for table: {table_name}\n"
                        export_script += f"-- Query: {data_query}\n"
                        export_script += f"{data_result}\n"
            
            return export_script
            
        except Exception as e:
            error_msg = f"Error exporting database structure: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def get_last_query(self) -> dict:
        """Get the last executed query and its result"""
        return {
            'query': self.last_query,
            'result': self.last_result
        }

    def get_query_history(self) -> list:
        """Get the history of executed queries"""
        return self.executed_queries.copy()

