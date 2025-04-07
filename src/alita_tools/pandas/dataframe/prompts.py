PLAN_CODE_PROMPT = """
<dataframe>
{dataframe}
</dataframe>


Every function will be supplied with datafame as one of the required arguments.

You are already provided with the following functions that you can call:
<function>
def get_dataframe() -> pd.Dataframe
    '''This method returns the dataframe'''
</function>

Update this initial code:
```python
# TODO: import the required dependencies
import pandas as pd

# Write code here 

```

<user_task>
{task}
</user_task>

At the end, declare "result" variable as a dictionary of type and value.
IMPORTANT: Use get_dataframe function to get the dataframe to work with
IMPORTANT: Imporant to add calls of the functions you created and form a result based on results.
IMPORTANT: Avoid using __main__ or __name__ == "__main__" in the code.
IMPORTANT: return dataset as "df" key in the result dictionary.


Generate python code and return full updated code:
"""
import os 

DEFAULT_CHART_DIRECTORY = os.path.join("exports", "charts")