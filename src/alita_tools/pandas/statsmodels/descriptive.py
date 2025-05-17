from typing import Any, Optional
import pandas as pd
from ..dataframe.utils import send_thinking_step

def set_of_column_values(df: pd.DataFrame, column_name: str):
    """Unique set of values from column with list elements
    Args:
        column_name (str): "Column name"
    """
    values = set()
    for x in df[column_name]:
        if type(x) == list:
            for y in x:
                values.add(y if type(y) == str else str(y))
        else:
            values.add(x if type(x) == str else str(x))
    send_thinking_step(func="set_of_column_values", content=f"#### Unique values for column {column_name}:\n\n{', '.join(list(values))}")
    return ", ".join(list(values))


def calculate_skewness_and_kurtosis(df: pd.DataFrame, columns:str, group_by: Optional[str]=None):
    """Calculate skewness and kurtosis for a colum or list of columns, if group_by is provided, calculate the statistics per group.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): single column or list of columns separated by |
        group_by (Optional[str], optional): group by column or list of columns separated by | defaults value to None.
    """
    columns = [c.strip() for c in columns.split('|')]
    result = f"#### Calculated skewness and kurtosis\n\n" + f"**Columns**: {', '.join(columns)}\n\n"
    if group_by is None or group_by == "":
        result += f"**Skewness**: {df[columns].skew().to_string()} \n\n**Kurtosis**: {df[columns].kurt().to_string()}"
    else:
        group_by = [g.strip() for g in group_by.split('|')]
        _df = df.groupby(group_by)[columns]
        result += f"**Grouped by**: {', '.join(group_by)}\n\n"
        result += f"**Skewness**: {_df.skew().to_string()} \n\n**Kurtosis**: {_df.kurt().to_string()}"
    send_thinking_step(func="calculate_skewness_and_kurtosis", content=result)
    return result

def calculate_mode(df: pd.DataFrame, columns: str, group_by: Optional[str]=None):
    """Calculate mode for a colum or list of columns, if group_by is provided, calculate the statistics per group
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): single column or list of columns separated by | in case of group_by every colum will be used as value and mode will be calculated for each column
        group_by (Optional[str], optional): group by column or list of columns separated by | defaults value to None.
    """
    res = {}
    columns = [c.strip() for c in columns.split('|')]
    message = f"#### Calculated mode for columns {', '.join(columns)}:\n\n"
    if group_by is None  or group_by == "":
        for column in columns:
            res[column] = df[column].mode()[0]
        result = pd.DataFrame(res, index=[0])
        message += result.to_markdown()
    else:
        group_by = [g.strip() for g in group_by.split('|')]
        for column in columns:
            mode = df.groupby(group_by)[column].apply(lambda x: x.mode().iloc[0])
            res[column] = mode
        result = pd.DataFrame(res)
        message = f"Groupped by {', '.join(group_by)}\n\n{result.to_markdown()}" 
    
    send_thinking_step(func="calculate_mode", content=message)
    return result.to_markdown()

def calculate_range(df: pd.DataFrame, columns:str, group_by: Optional[str]=None):
    """Calculate the range for a colum or list of columns, if group_by is provided, calculate the range for each group.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): single column or list of columns separated by |
        group_by (Optional[str], optional): group by column or list of columns separated by | defaults value to None.
    """
    columns = [c.strip() for c in columns.split('|')]
    message = f"#### Calculated range for columns {', '.join(columns)}:\n\n"
    if group_by is None:
        result = df[columns].apply(lambda x: x.max() - x.min())
        message += result.to_markdown()
    else:
        group_by = [g.strip() for g in group_by.split('|')]
        result = df.groupby(group_by)[columns].apply(lambda x: x.max() - x.min())
        message = f"Groupped by {', '.join(group_by)}\n\n{result.to_markdown()}"
    
    send_thinking_step(func="calculate_range", content=message)
    return result.to_markdown()

def calculate_variance(df: pd.DataFrame, columns: str, group_by: Optional[str]=None):
    """Calculate the variance for a colum or list of columns, if group_by is provided, calculate the variance for each group.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): single column or list of columns separated by |
        group_by (Optional[str], optional): group by column or list of columns separated by | defaults value to None.
    """
    columns = [c.strip() for c in columns.split('|')]
    message = f"#### Calculated variance for columns {', '.join(columns)}:\n\n"
    if group_by is None:
        result = df[columns].var()
        message += str(result)
    else:
        result = df.groupby(group_by)[columns].var()
        message = f"Groupped by {', '.join(group_by)}\n\n{result.to_markdown()}"
    
    send_thinking_step(func="calculate_variance", content=message)
    return result.to_markdown()
    
def pairwise_correlation(df: pd.DataFrame, columns_for_df1: str, columns_for_df2: str, method: Optional[str]="pearson"):
    """ Pairwise correlation between one set of columns and another set of columns.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns_for_df1 (str): "Master list of columns to be correlated against, separated by | 
        columns_for_df2 (str): "Columns to to be correlated by, values is a sting separated by | 
        method (str, optional): "Correlation method, allowed methods pearson, kendall, spearman , default is pearson"
    """
    columns_for_df1 = [column.strip() for column in columns_for_df1.split("|")]
    columns_for_df2 = [column.strip() for column in columns_for_df2.split("|")]
    df1 = df[columns_for_df1]
    df2 = df[columns_for_df2]
    result = df1.corrwith(df2, method=method)
    message = f"#### Pairwise correlation between {', '.join(columns_for_df1)} and {', '.join(columns_for_df2)}\n\n"
    message += result.to_markdown()
    
    send_thinking_step(func="pairwise_correlation", content=message)
    return result.to_string()

def explode(df: pd.DataFrame, column_name: str):
    """Transform each element of a list-like to a row, replicating index values.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_name (str): "Column name"
    """
    try:
        df = df.explode(column_name)
        return f"Exploded column: {column_name}."
    except KeyError as e:
        return f"ERROR: The '{column_name}' column does not exist, verify the name. Use get_column_names to see all columns."

def delimitred_column_values_to_list(df: pd.DataFrame, column_name:str, delimiter=";"):
    """Convert delimiter separated string column values to list colum values, delimeters can be comma, semicolon, space, etc. make sure you use the right one
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_name (str): "Column name"
        delimiter (str, optional): "Delimiter of values in column". Defaults to ";".
    """
    for i, value in enumerate(df[column_name]):  
        new_col = []
        if not value:
            new_col = []
        elif type(value) == str and delimiter in value:
            for val in value.split(delimiter):
                if val.strip():
                    new_col.append(val.strip())
        else:
            new_col.append(str(value))
        if not df.columns.str.contains(f"{column_name}_list").any():
            df[f"{column_name}_list"] = ""
        
        df.at[i, f"{column_name}_list"] = new_col
    result = f"Added new column {column_name}_list as a list of values from {column_name} column"
    return f"{result}. Here is set of values: " + set_of_column_values(df, f"{column_name}_list").get("result")

def covariance(df: pd.DataFrame, columns: Optional[str]=None):
    """Calculate covariance for dataset or subset of selected columns
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str, optional): two or more columns separated by | , if not provided, all columns will be used. Defaults to None.
    """
    if columns:
        columns = [c.strip() for c in columns.split('|')]
        result = df[columns].cov()
        message = f"#### Calculated covariance for columns {', '.join(columns)}:\n\n{result.to_markdown()}"
        
    else:
        result = df.cov()
        message = f"#### Calculated covariance for all columns:\n\n{result.to_markdown()}"
    
    send_thinking_step(func="covariance", content=message)
    return result.to_string()

def correlation(df: pd.DataFrame, column_names: str, method: Optional[str]="pearson"):
    """ Correlate data by columns - quantifies the degree to which variables are related
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_names (str): "Columns list to correlate, values is a sting separated by | 
        method (str, optional): "Correlation method, allowed methods pearson, kendall, spearman , default is pearson"
    """
    column_names = [column.strip() for column in column_names.split("|")]
    result = df[column_names].corr(method=method)
    message = f"#### Correlation between {', '.join(column_names)}\n\n{result.to_markdown()}"
    
    send_thinking_step(func="correlation", content=message)
    return result.to_string()
