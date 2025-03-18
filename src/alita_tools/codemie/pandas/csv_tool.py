from io import StringIO
from typing import Type, Any, Optional

import chardet
import clevercsv
import pandas as pd
from pydantic import BaseModel, Field

from ..base.codemie_tool import CodeMieTool
from ..pandas.tool_vars import CSV_TOOL


def get_csv_delimiter(data: str, length_to_sniff: int) -> str:
    """ Get the delimiter of the CSV file. """
    dialect = clevercsv.Sniffer().sniff(data[:length_to_sniff])
    return dialect.delimiter


class Input(BaseModel):
    method_name: str = Field(
        description="Method to be called on the padnas dataframe object generated from the file"
    )
    method_args: dict = Field(
        description="Pandas dataframe arguments to be passed to the method",
        default={}
    )
    column: Optional[str] = Field(
        description="Column to be used for the operation",
        default=None
    )


class CSVTool(CodeMieTool):
    """ Tool for working with data from CSV files. """
    args_schema: Type[BaseModel] = Input
    name: str = CSV_TOOL.name
    label: str = CSV_TOOL.label
    description: str = CSV_TOOL.description
    csv_content: Any = Field(exclude=True)

    def execute(self, method_name: str, method_args=None, column: Optional[str] = None):
        if method_args is None:
            method_args = {}
        bytes_data = self.bytes_content()
        encoding = chardet.detect(bytes_data)['encoding']
        data = bytes_data.decode(encoding)
        df = pd.read_csv(StringIO(data), sep=get_csv_delimiter(data, 128), on_bad_lines='skip')

        if column:
            col = df[column]
            result = getattr(col, method_name)
        else:
            result = getattr(df, method_name)

        if len(method_args):
            result = result(**method_args)

        return str(result)

    def bytes_content(self) -> bytes:
        """
        Returns the content of the file as bytes
        """
        if self.csv_content is None:
            raise ValueError("CSV content is not set")
        if isinstance(self.csv_content, bytes):
            return self.csv_content

        return self.csv_content.encode('utf-8')
