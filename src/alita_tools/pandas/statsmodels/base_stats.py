import pandas as pd
from typing import Any, Optional
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


def label_based_on_bins(df: pd.DataFrame, column_name: str, bins: str, labels: str):
    """ Categorize column based on integer or float bins and add new column with labels culumns needs to be numeric or categorical before binning
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_name (str): "Column name"
        bins (str): "Bins list, values is a sting separated by | "
        labels (str): "Labels list, values is a sting separated by | "
    """
    bins = [float(b.strip()) for b in bins.split("|")]
    labels = [l.strip() for l in labels.split("|")]
    if len(bins) != len(labels)+1:
        return f"ERROR: Number of bins should be equal to number of labels + 1."
    df[f'{column_name}_labeled'] = pd.cut(df[column_name], bins=bins, labels=labels)
    convert_categorical_colum_to_numeric(df, f'{column_name}_labeled')
    return f'Added new column: {column_name}_labeled and {column_name}_labeled_numberic that is labeled represetation of {column_name} and numeric representation of labels.'


def descriptive_statistics(df: pd.DataFrame, columns: str, 
                           metrics: Optional[str]=None, 
                           group_by: Optional[str]=None, 
                           group_by_value: Optional[str]=None,
                           order_by: Optional[str]=None,
                           n_limit: Optional[str]=None):
    """Calculate the descriptive statistics for signle or list of columns, if group_by is provided, calculate the statistics per group
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): single column or list of columns separated by |
        metrics (str, optional): single or list of metrics to calculate separated by |, available metrics are mean, median, std, min, max, count, 25%, 50%, 75%, Ignored when group_by is provided.
        group_by (str, optional): group by column or list of columns separated by | defaults value to None.
        group_by_value (str, optional): could used when there is only one colum to group by applies as filter defaults value to None.
    """
    columns = [c.strip() for c in columns.split('|')]
    if order_by:
        order_by = [o.strip() for o in order_by.split('|')]
    if n_limit:
        n_limit = int(n_limit)
    if metrics is None:
        metrics = ['mean', 'std', 'min', 'max', 'count', '25%', '50%', '75%']
    else:
        metrics = [m.strip() for m in metrics.split('|')]
    if group_by is None:
        result = df[columns].describe()
    else:
        group_by = [g.strip() for g in group_by.split('|')]
        if group_by_value and len(group_by) == 1:
            try:
                group_by_value = float(group_by_value)
            except ValueError:
                pass
            result = df[df[group_by[0]] == group_by_value][columns].describe()
        else:
            result = df.groupby(group_by)[columns].describe()
    return result.to_string()
    

def standardize(df: pd.DataFrame, column_names: str):
    """standardize the dataset features onto unit scale (mean = 0 and variance = 1) which is a requirement for the optimal performance of many machine learning algorithm. Adds new columns to dataset.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        column_names (str): "Column names contains features separated by |"
    """
    column_names = [c.strip() for c in column_names.split("|")]
    _df = df.loc[:, column_names].values
    _df = sklearn.preprocessing.StandardScaler().fit_transform(_df)
    new_columns = []
    for i, c in enumerate(column_names):
        new_columns.append(f"{c}_std")
        df[f"{c}_std"] = _df[:, i]
    
    return f"Added new columns with standatrized values: {', '.join(new_columns)}, Sample of data stored there: {df[new_columns].head(5).to_string()}" 


def crosstab(df: pd.DataFrame, columns: str):
    """Compute a simple cross tabulation between multiple categorical or numeric columns.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): list of columns separated by | First column is used as index, other columns is used as columns
    """
    columns = [c.strip() for c in columns.split('|')]
    index_col = columns.pop(0)
    cols = [df[c] for c in columns]
    result = pd.crosstab(index=df[index_col], columns=cols)
    return result.to_csv()


def _test_a_model(model, features, target):
    pred = model.predict(features)
    prediction = list(map(round, pred)) 
    _accuracy = sklearn.metrics.accuracy_score(target, prediction)
    return f"Model accuracy: {_accuracy}"

def _prepare_dataset(df: pd.DataFrame, columns_set_one: str, columns_set_two: Optional[str]=''):
    columns_set_one = [c.strip() for c in columns_set_one.split("|")]
    if columns_set_two:
        columns_set_two = [c.strip() for c in columns_set_two.split("|")]
    else:
        columns_set_two = []
    
    _df = df[columns_set_one + columns_set_two]
    _df = _df.dropna()
    if len(columns_set_one) == 1:
        columns_set_one = columns_set_one[0]
    if len(columns_set_two) == 1:
        columns_set_two = columns_set_two[0]
    return _df, columns_set_one, columns_set_two