import csv
from io import StringIO
from typing import Any, Optional

import chardet
import pandas as pd
from pydantic import create_model, Field

from ..elitea_base import BaseToolApiWrapper


class CSVToolApiWrapper(BaseToolApiWrapper):
    csv_content: Any
    _length_to_sniff: int = 1024

    def bytes_content(self, content: Any) -> bytes:
        """
        Returns the content of the file as bytes
        """
        if content is None:
            raise ValueError("CSV content is not set")
        if isinstance(content, bytes):
            return content

        return content.encode('utf-8')

    def _get_csv_delimiter(self, data: str) -> str:
        """ Get the delimiter of the CSV file. """
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(data[0:self._length_to_sniff])
        return dialect.delimiter

    def execute(self, method_name: str, method_args: dict = {}, column: Optional[str] = None, csv_content: Optional[Any] = None):
        """
        Tool for working with data from CSV files.
        IMPORTANT:
        Don't request csv_content from user if he hasn't provided it - it is expected to extract data from artifact
        """
        bytes_data = self.bytes_content(csv_content if csv_content else self.csv_content)
        encoding = chardet.detect(bytes_data)['encoding']
        data = bytes_data.decode(encoding)
        df = pd.read_csv(StringIO(data), sep=self._get_csv_delimiter(data), on_bad_lines='skip')

        if column:
            col = df[column]
            result = getattr(col, method_name)
        else:
            result = getattr(df, method_name)

        return str(result(**method_args))

    def get_available_tools(self):
        return [
            {
                "name": "execute",
                "ref": self.execute,
                "description": self.execute.__doc__,
                "args_schema": create_model(
                    "ExecuteModel",
                    method_name=(str, Field(description="Method to be called on the pandas dataframe object generated from the file")),
                    method_args=(Optional[dict], Field(description="Pandas dataframe arguments to be passed to the method", default={})),
                    column=(Optional[str], Field(description="Column to be used for the operation", default=None)),
                    csv_content=(Optional[Any], Field(default=None, description="CSV content to be processed. "
                                                                                "Can be None when user defined artifact's path in configuration"))
                ),
            }
        ]