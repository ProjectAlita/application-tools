import csv
from io import StringIO
from typing import Any, Optional

import chardet
import pandas as pd
from pydantic import BaseModel, create_model, FieldInfo, model_validator, PrivateAttr


class CSVToolApiWrapper(BaseModel):
    csv_content: Any
    _length_to_sniff: int = 1024

    def bytes_content(self) -> bytes:
        """
        Returns the content of the file as bytes
        """
        if self.csv_content is None:
            raise ValueError("CSV content is not set")
        if isinstance(self.csv_content, bytes):
            return self.csv_content

        return self.csv_content.encode('utf-8')

    def _get_csv_delimiter(self, data: str) -> str:
        """ Get the delimiter of the CSV file. """
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(data[0:self._length_to_sniff])
        return dialect.delimiter

    def execute(self, method_name: str, method_args: dict = {}, column: Optional[str] = None):
        """ Tool for working with data from CSV files. """
        bytes_data = self.bytes_content()
        encoding = chardet.detect(bytes_data)['encoding']
        data = bytes_data.decode(encoding)
        df = pd.read_csv(StringIO(data), sep=self._get_csv_delimiter(data), on_bad_lines='skip')

        if column:
            col = df[column]
            result = getattr(col, method_name)
        else:
            result = getattr(df, method_name)

        if len(method_args):
            result = result(**method_args)

        return str(result)

    def get_available_tools(self):
        return [
            {
                "name": "execute",
                "ref": self.execute,
                "description": self.execute.__doc__,
                "args_schema": create_model(
                    "ExecuteModel",
                    method_name=(str, FieldInfo(description="Method to be called on the pandas dataframe object generated from the file")),
                    method_args=(dict, FieldInfo(description="Pandas dataframe arguments to be passed to the method", default={})),
                    column=(Optional[str], FieldInfo(description="Column to be used for the operation", default=None))
                ),
            }
        ]