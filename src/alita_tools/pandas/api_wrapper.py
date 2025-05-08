# -*- coding: utf-8 -*-
# This one is heavily inspired by the pandasai library
# 

import csv
from io import StringIO
from typing import Any, Optional
import traceback

import chardet
import logging
import pandas as pd
from pydantic import create_model, Field, model_validator

from ..elitea_base import BaseToolApiWrapper
from .dataframe.serializer import DataFrameSerializer
from .dataframe.generator.base import CodeGenerator
from .dataframe.executor.code_executor import CodeExecutor
from langchain_core.callbacks import dispatch_custom_event

logger = logging.getLogger(__name__)

class PandasWrapper(BaseToolApiWrapper):
    alita: Any = None
    llm: Any = None
    bucket_name: str
    file_name: str = None
    df_name: Optional[str] = None
    
    _length_to_sniff: int = 1024
    _df: pd.DataFrame = None
    _df_info: str = None

    def bytes_content(self, content: Any) -> bytes:
        """
        Returns the content of the file as bytes
        """
        if not content:
            content = self.alita.download_artifact(self.bucket_name, self.file_name)
        if isinstance(content, bytes):
            return content
        return content.encode('utf-8')

    def _get_csv_delimiter(self, data: str) -> str:
        """ Get the delimiter of the CSV file. """
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(data[0:self._length_to_sniff])
        return dialect.delimiter
    
    def _get_dataframe(self) -> pd.DataFrame | None:
        """ Get the dataframe from the CSV file. """
        if self._df is not None:
            return self._df
        try:
            _df = self.alita.download_artifact(self.bucket_name, self.df_name)
        except Exception as e:
            _df = None
        if isinstance(_df, bytes):
            from io import BytesIO
            df = pd.read_pickle(BytesIO(_df))
        else:
            df = None
        if df is None and self.file_name:
            bytes_data = self.bytes_content(self.alita.download_artifact(self.bucket_name, self.file_name))
            encoding = chardet.detect(bytes_data)['encoding']
            data = bytes_data.decode(encoding)
            df = pd.read_csv(StringIO(data), sep=self._get_csv_delimiter(data), on_bad_lines='skip')
        if df is not None:
            self._df_info = DataFrameSerializer.serialize(df)
        return df
    
    def _save_dataframe(self, df: pd.DataFrame) -> None:
        """ Save the dataframe to the artifact repo. """
        from io import BytesIO
        bytes_io = BytesIO()
        df.to_pickle(bytes_io)
        respone = self.alita.create_artifact(self.bucket_name, self.df_name, bytes_io.getvalue())
        return respone    
    
    
    def generate_code(self, task_to_solve: str, error_trace: str=None) -> str:
        """Generate pandas code using LLM based on the task to solve."""
        code = CodeGenerator(
            df=self._get_dataframe(),
            df_description=self._df_info,
            llm=self.llm
        ).generate_code(task_to_solve, error_trace)
        return code 
    
    def execute_code(self, code: str) -> str:
        """Execute the generated code and return the result."""
        executor = CodeExecutor()
        executor.add_to_env("get_dataframe", self._get_dataframe)
        return executor.execute_and_return_result(code)
    
    def generate_code_with_retries(self, query: str) -> Any:
        """Execute the code with retry logic."""
        max_retries = 5
        attempts = 0
        try:
            return self.generate_code(query)
        except Exception as e:
            error_trace = traceback.format_exc()
            while attempts <= max_retries:
                try:
                    return self.generate_code(query, error_trace)
                except Exception as e:
                    attempts += 1
                    if attempts > max_retries:
                        logger.info(
                            f"Maximum retry attempts exceeded. Last error: {e}"
                        )
                        raise
                    logger.info(
                        f"Retrying Code Generation ({attempts}/{max_retries})..."
                    )
    
    def process_query(self, query: str) -> str:
        """Analyze and process using query on dataset""" 
        self._df = self._get_dataframe()
        code = self.generate_code_with_retries(query)
        dispatch_custom_event(
                name="thinking_step",
                data={
                    "message": f"Executing generated code... \n\n```python\n{code}\n```",
                    "tool_name": "process_query",
                    "toolkit": "pandas"
                }
            )
        result = self.execute_code(code)
        dispatch_custom_event(
            name="thinking_step",
            data={
                "message": f"Result of code execution... \n\n```\n{result}\n```",
                "tool_name": "process_query",
                "toolkit": "pandas"
            }
        )
        if result.get("df") is not None:
            df = result.pop("df")
            self._save_dataframe(df)
        return result

    def get_available_tools(self):
        return [
            {
                "name": "process_query",
                "ref": self.process_query,
                "description": self.process_query.__doc__,
                "args_schema": create_model(
                    "ProcessQueryModel",
                    query=(str, Field(description="Task to solve")),
                )
            }
        ]