from typing import Any, Optional, Union, Dict, List

from pydantic import BaseModel, model_validator, create_model, FieldInfo, PrivateAttr
from sqlalchemy import create_engine, text, inspect, Engine
from sqlalchemy.orm import sessionmaker

from .models import SQLConfig, SQLDialect


class SQLApiWrapper(BaseModel):
    sql_config: SQLConfig
    _engine: Optional[Engine] = PrivateAttr()

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        sql_config = values.get('sql_config')
        if not sql_config:
            raise ValueError("SQL configuration is required.")

        host = sql_config.host
        username = sql_config.username
        password = sql_config.password
        database_name = sql_config.database_name
        port = sql_config.port
        dialect = sql_config.dialect

        if dialect == SQLDialect.POSTGRES:
            connection_string = f'postgresql+psycopg://{username}:{password}@{host}:{port}/{database_name}'
        elif dialect == SQLDialect.MYSQL:
            connection_string = f'mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}'
        else:
            raise ValueError(f"Unsupported database type. Supported types are: {[e.value for e in SQLDialect]}")

        cls._engine = create_engine(connection_string)
        return values

    def execute_sql(self, sql_query: str) -> Union[List[Dict[str, Any]], str]:
        """Executes the provided SQL query and returns the result."""
        maker_session = sessionmaker(bind=self._engine)
        session = maker_session()
        try:
            result = session.execute(text(sql_query))
            session.commit()

            if result.returns_rows:
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                return data
            else:
                return f"Query {sql_query} executed successfully"

        except Exception as e:
            session.rollback()
            raise e

        finally:
            session.close()

    def list_tables_and_columns(self) -> Dict[str, Any]:
        """Lists all tables and their columns in the database."""
        inspector = inspect(self._engine)
        data = {}
        tables = inspector.get_table_names()
        for table in tables:
            columns = inspector.get_columns(table)
            columns_list = []
            for column in columns:
                columns_list.append({
                    'name': column['name'],
                    'type': column['type']
                })
            data[table] = {
                'table_name': table,
                'table_columns': columns_list
            }
        return data

    def get_available_tools(self):
        return [
            {
                "name": "execute_sql",
                "description": self.execute_sql.__doc__,
                "args_schema": create_model(
                    "ExecuteSQLModel",
                    sql_query=(str, FieldInfo(description="The SQL query to execute"))
                ),
                "ref": self.execute_sql,
            },
            {
                "name": "list_tables_and_columns",
                "description": self.list_tables_and_columns.__doc__,
                "args_schema": create_model(
                    "ListTablesAndColumnsModel"
                ),
                "ref": self.list_tables_and_columns,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")