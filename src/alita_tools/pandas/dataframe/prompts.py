import os 

PLAN_CODE_PROMPT = """
<dataframe>
{dataframe}
</dataframe>

You are already provided with the following functions that you can call:

{prompt_addon}

---- 

Update this initial code:
```python
# You can use all these libraries in your code
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as ss
import statsmodels
import statsmodels.api as sm
import factor_analyzer
import sklearn
import base64
from io import BytesIO

df = get_dataframe()

# Write code here 

```

<user_task>
{task}
</user_task>

CHART GENERATION INSTRUCTIONS:
When creating a chart, provide base64 encoded image as a string in the result dictionary with key "chart" and explanation what it is in result dictionary with key "result".
To save charts you must use BytesIO() buffers
Delete file after transforming it to base64 string.
If you need to have multiple charts, put them as a list in the result dictionary with key "chart" and explanation what they are in result dictionary with key "result".

IMPORTANT: Avoid using comments in code, they may cause validation errors.
IMPORTANT: Avoid using __main__ or __name__ == "__main__" in the code.
IMPORTANT: return dataset as "df" key in the result dictionary.
IMPORTANT: last link of the code should start with `result = dict(df = df, result=<result of user task computation>)`

Generate python code and return full updated code:
"""

DEFAULT_CHART_DIRECTORY = os.path.join("charts")
if not os.path.exists(DEFAULT_CHART_DIRECTORY):
    os.makedirs(DEFAULT_CHART_DIRECTORY)