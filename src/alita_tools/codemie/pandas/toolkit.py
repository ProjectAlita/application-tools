import io
from typing import Dict, Any, Optional

from ..base.base_toolkit import BaseToolkit
from ..base.models import ToolKit, ToolSet, Tool
from ..pandas.csv_tool import CSVTool, get_csv_delimiter
from ..pandas.tool_vars import CSV_TOOL
import pandas as pd
from langchain_experimental.tools import PythonAstREPLTool

class PandasToolkit(BaseToolkit):
    csv_content: Optional[str] = None
    file_name: Optional[str] = None

    @classmethod
    def get_tools_ui_info(cls, *args, **kwargs):
        return ToolKit(
            toolkit=ToolSet.PANDAS,
            tools=[
                Tool.from_metadata(CSV_TOOL),
            ]
        ).model_dump()

    def get_tools(self):
        data_frame = pd.read_csv(
            io.StringIO(self.csv_content),
            delimiter=get_csv_delimiter(self.csv_content, 128),
        )
        df_locals = {"df": data_frame}
        repl_tool = PythonAstREPLTool(locals=df_locals)
        repl_tool.description = _generate_csv_prompt(self.file_name)

        csv_tool = CSVTool(csv_content=self.csv_content)
        return [repl_tool, csv_tool]

    @classmethod
    def get_toolkit(cls, configs: Dict[str, Any]):
        csv_content = configs.get("csv_content", None)
        file_name = configs.get("file_name", None)
        return cls(csv_content=csv_content, file_name=file_name)

def _generate_csv_prompt(file_name):
    return f"""A CSV file named '{file_name}' has been uploaded by the user,
and it has already been loaded into a Pandas DataFrame called `df`.

 - Whenever you want to run Python code (e.g., to call `df.info()`, `df.describe()`, `df.head()`, etc.),
   you must strictly use the following format in your answer:
Action: python_repl_ast
Action Input:
```python
# your Python code here
```
 - You may ask clarifying questions if something is unclear.
 - In your explanations or final answers, refer to the CSV by its file name '{file_name}' rather than `df`.
Remember:
1) The DataFrame variable is `df`.
2) The file name is '{file_name}'.
"""
