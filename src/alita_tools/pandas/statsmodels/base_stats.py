import pandas as pd
from typing import List, Optional
import sklearn

def convert_str_column_to_categorical(df: pd.DataFrame, column_name: str):
    """ Convert string column to categorical column with numeric reprenrarion - adds new column to dataset.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_name (str): "Column name"
    """
    df[column_name] = pd.Categorical(df[column_name])
    return convert_categorical_colum_to_numeric(df, column_name)

def convert_categorical_colum_to_numeric(df: pd.DataFrame, column_name: str):
    """ Convert categorical column to numeric column - adds new column to dataset.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_name (str): "Column name"
    """
    categories = df[column_name].cat
    df[f'{column_name}_numeric'] = categories.codes
    result = f'{column_name} categorical colums values corresponds to {column_name}_numeric values: '
    for index, value in enumerate(categories.categories):
        result += f'Value: {value} corresponds to {categories.codes[index]} |'
    return result


def label_based_on_bins(df: pd.DataFrame, column_name: str, bins: List[float], labels: List[str]):
    """ Categorize column based on integer or float bins and add new column with labels culumns needs to be numeric or categorical before binning
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_name (str): "Column name"
        bins (List[float]): "List of bin values"
        labels (List[str]): "List of labels for each bin"
    """
    if len(bins) != len(labels)+1:
        return f"ERROR: Number of bins should be equal to number of labels + 1."
    df[f'{column_name}_labeled'] = pd.cut(df[column_name], bins=bins, labels=labels)
    convert_categorical_colum_to_numeric(df, f'{column_name}_labeled')
    return f'Added new column: {column_name}_labeled and {column_name}_labeled_numberic that is labeled represetation of {column_name} and numeric representation of labels.'


def descriptive_statistics(df: pd.DataFrame, columns: List[str], 
                           metrics: Optional[List[str]]=None, 
                           group_by: Optional[List[str]]=None, 
                           group_by_value: Optional[str]=None,
                           order_by: Optional[List[str]]=None,
                           n_limit: Optional[int]=None):
    """Calculate the descriptive statistics for single or list of columns, if group_by is provided, calculate the statistics per group
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (List[str]): list of columns to calculate statistics for
        metrics (List[str], optional): list of metrics to calculate, available metrics are mean, median, std, min, max, count, 25%, 50%, 75%, Ignored when group_by is provided.
        group_by (List[str], optional): list of columns to group by, defaults to None.
        group_by_value (str, optional): could used when there is only one column to group by applies as filter defaults value to None.
        order_by (List[str], optional): list of columns to order by, defaults to None.
        n_limit (int, optional): limit the number of rows returned, defaults to None.
    """
    if n_limit:
        n_limit = int(n_limit) if isinstance(n_limit, str) else n_limit
    if metrics is None:
        metrics = ['mean', 'std', 'min', 'max', 'count', '25%', '50%', '75%']
    if group_by is None:
        result = df[columns].describe()
    else:
        if group_by_value and len(group_by) == 1:
            try:
                group_by_value = float(group_by_value)
            except ValueError:
                pass
            result = df[df[group_by[0]] == group_by_value][columns].describe()
        else:
            result = df.groupby(group_by)[columns].describe()
    return result.to_string()
    

def standardize(df: pd.DataFrame, column_names: List[str]):
    """standardize the dataset features onto unit scale (mean = 0 and variance = 1) which is a requirement for the optimal performance of many machine learning algorithm. Adds new columns to dataset.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_names (List[str]): List of column names containing features to standardize
    """
    _df = df.loc[:, column_names].values
    _df = sklearn.preprocessing.StandardScaler().fit_transform(_df)
    new_columns = []
    for i, c in enumerate(column_names):
        new_columns.append(f"{c}_std")
        df[f"{c}_std"] = _df[:, i]
    
    return f"Added new columns with standatrized values: {', '.join(new_columns)}, Sample of data stored there: {df[new_columns].head(5).to_string()}" 


def crosstab(df: pd.DataFrame, columns: List[str]):
    """Compute a simple cross tabulation between multiple categorical or numeric columns.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (List[str]): list of columns where first column is used as index, other columns are used as columns
    """
    index_col = columns[0]
    cols = [df[c] for c in columns[1:]]
    result = pd.crosstab(index=df[index_col], columns=cols)
    return result.to_csv()


def _test_a_model(model, features, target):
    pred = model.predict(features)
    prediction = list(map(round, pred)) 
    _accuracy = sklearn.metrics.accuracy_score(target, prediction)
    return f"Model accuracy: {_accuracy}"

def _prepare_dataset(df: pd.DataFrame, columns_set_one: List[str], columns_set_two: Optional[List[str]]=None):
    """Prepare dataset for model training by selecting columns and handling missing values
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns_set_one (List[str]): First set of columns
        columns_set_two (List[str], optional): Second set of columns, defaults to None
    """
    if columns_set_two is None:
        columns_set_two = []
    
    _df = df[columns_set_one + columns_set_two]
    _df = _df.dropna()
    if len(columns_set_one) == 1:
        columns_set_one = columns_set_one[0]
    if len(columns_set_two) == 1:
        columns_set_two = columns_set_two[0]
    return _df, columns_set_one, columns_set_two