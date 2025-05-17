from typing import Any, Optional

import pandas as pd
import statsmodels.api as sm
import sklearn
import factor_analyzer
from ..dataframe.utils import send_thinking_step
from .base_stats import _prepare_dataset, _test_a_model

def linear_regression(df: pd.DataFrame, feature_columns: str, formula: str, target_column: str, model=None):
    """ Build model to predict a dependent variable using two or more predictor variables
    Args:
        df (pd.DataFrame): DataFrame to operate on
        feature_columns (str): "Column names for linear regression | . Should be full list of colums used withing R formula"
        formula (str): "R formula for representing relationship between dependent and independent variables"
        target_column (str): "target column we will be predicting"
        model: Optional model object where the trained model will be stored
    """
    
    _df, feature_columns, target_column = _prepare_dataset(df, feature_columns, target_column)
    trained_model = sm.formula.api.ols(formula, data=_df).fit()
    if model is not None:
        model = trained_model
    accuracy = _test_a_model(trained_model, _df[feature_columns], _df[target_column])
    message = f"""#### Linear regression model summary ({accuracy}):\n\n```\n\n"""
    message += trained_model.summary().as_text().replace('\n', '\n\n')
    message += "\n\n```\n\n"""
    
    send_thinking_step(func="linear_regression", content=message)
    return f"{accuracy}\n\n{trained_model.summary().as_text()}"


def logistic_regression(df: pd.DataFrame, feature_columns: str, formula: str, target_column: str, model=None):
    """ Build model to predict of probability of occurrence of an event
    Args:
        df (pd.DataFrame): DataFrame to operate on
        feature_columns (str): "Column names for logistic regression | . Should be full list of colums used withing R formula"
        formula (str): "R formula for representing relationship between dependent and independent variables"
        target_column (str): "target column we will be predicting"
        model: Optional model object where the trained model will be stored
    """
    
    _df, feature_columns, target_column = _prepare_dataset(df, feature_columns, target_column)
    trained_model = sm.formula.api.logit(formula, data=_df).fit()
    if model is not None:
        model = trained_model
    accuracy = _test_a_model(trained_model, _df[feature_columns], _df[target_column])
    message = f"""#### Logistic regression model summary ({accuracy}):\n\n```\n\n"""
    message += trained_model.summary().as_text().replace('\n', '\n\n')
    message += "\n\n```\n\n"""
    
    send_thinking_step(func="logistic_regression", content=message)
    return f"{accuracy}\n\n{trained_model.summary().as_text()}"


def mixed_effect_lm(df: pd.DataFrame, feature_columns:str, formula: str, group_column:str, target_column:str, model=None):
    """ Build a mixed effect model for regresion analysis involving dependent data, random effects must be independently-realized for responses in different groups
    Args:
        df (pd.DataFrame): DataFrame to operate on
        feature_columns (str): "Column names with one sample per column separated by | . Should be full list of colums used withing R formula"
        formula (str): "R formula for representing relationship between variables"
        group_column (str): "column name with group values"
        target_column (str): "target column, to be used in testing of model"
        model: Optional model object where the trained model will be stored
    """
    _df, feature_columns, target_column = _prepare_dataset(df, f'{feature_columns}|{group_column}', target_column)
    feature_columns = feature_columns[:-1] # remove group column from feature columns
    trained_model = sm.formula.api.mixedlm(formula, _df, groups=_df[group_column]).fit()
    if model is not None:
        model = trained_model
    accuracy = _test_a_model(trained_model, _df[feature_columns], _df[target_column])
    message = f"""#### Mixed effect model summary ({accuracy}):\n\n```\n\n"""
    message += trained_model.summary().as_text().replace('\n', '\n\n')
    message += "\n\n```\n\n"""
    
    send_thinking_step(func="mixed_effect_lm", content=message)
    return f"{accuracy}\n\n{trained_model.summary().as_text()}"
    


def predict(df: pd.DataFrame, feature_columns: str, feature_values: str, model=None):
    """ Predict target column values using trained model
    Args:
        df (pd.DataFrame): DataFrame to operate on
        feature_columns (str): "one or more feature columns separated by |"
        feature_values (str): "one or more int or float feature values separated by |"
        model: Trained model object to use for prediction
    """
    feature_columns = [x.strip() for x in feature_columns.split("|")]
    feature_values = [float(x.strip()) for x in feature_values.split("|")]
    predict_ds = pd.DataFrame([feature_values], columns=feature_columns)
    if model is None:
        return "ERROR: Model is not trained yet. Please use one of the model training actions first"

    predictions = model.predict(predict_ds)
    message = f"""#### Predictions for:\n\n {', '.join(feature_columns)}: {', '.join([str(round(x, 4)) for x in predictions])}"""
    message += f"""##### Results:\n\n {', '.join([str(round(x, 4)) for x in predictions])}"""
    
    send_thinking_step(func="predict", content=message)
    return f"Predictions: {', '.join([str(round(x, 4)) for x in predictions])}"



def factorAnalysis(df: pd.DataFrame, columns:str):
    """ Factor analysis used to describe variability among observed, correlated variables in terms of a potentially lower number of unobserved variables called factors; KMO calculation included and score less than 0.6 is considered inadequate
    Args:
        df (pd.DataFrame): DataFrame to operate on
        columns (str): "Columns names separated by | "
    """
    _df, _, _ = _prepare_dataset(df, columns)
    _, kmo_model = factor_analyzer.factor_analyzer.calculate_kmo(_df)
    if kmo_model < 0.6:
        result = f"WARNING: KMO score is {kmo_model}, which is less than 0.6, so factor analysis is not recommended"
        send_thinking_step(func="factorAnalysis", content=result)
        return result
        
    fa = factor_analyzer.FactorAnalyzer()
    # Identify number of factors using eigenvalues
    fa.analyze(_df, 25, rotation=None)
    ev, v = fa.get_eigenvalues()
    max_factors = 0
    for i in range(len(ev)):
        if ev[i] < 1:
            break
        else:
            max_factors = i + 1
    
    # Running analysis
    fa.analyze(_df, max_factors, rotation="varimax")
    statistics= fa.get_factor_variance()
    
    # Interpreting results
    result = "| | "+" | ".join([f"Factor {i}" for i in range(1, max_factors + 1)]) + " | \n"
    result += "| SS Loadings | " + " | ".join([str(round(x, 4)) for x in statistics[0].tolist()]) + " |\n"
    result += "| Proportion Var | " + " | ".join([str(round(x, 4)) for x in statistics[1].tolist()]) + " |\n"
    result += "| Cumulative Var | " + " | ".join([str(round(x, 4)) for x in statistics[2].tolist()]) + " |\n"
    # Formatting message to markdown
    message = f"""#### Factor analysis results:\n\n{result}"""
    
    send_thinking_step(func="factorAnalysis", content=message)
    return result


def principal_component_analysis_2D(df: pd.DataFrame, feature_columns: str, target_column: str):
    """ Principal component analysis (PCA) to decreases dementiality of data to 2 dimentions, very usefull in 2D data visualization. Adds new columns to dataset.
    Args:
        df (pd.DataFrame): DataFrame to operate on
        feature_columns (str): "Column names contains features separated by |"
        target_column (str): "Column name with target values"
    """
    feature_columns = [x.strip() for x in feature_columns.split("|")]
    
    _df = df.loc[:, feature_columns].values
    _df = sklearn.preprocessing.StandardScaler().fit_transform(_df)
    
    pca = sklearn.decomposition.PCA(n_components=2)

    principalComponents = pca.fit_transform(_df)
    df[f"pc_x"] = principalComponents[:, 0]
    df[f"pc_y"] = principalComponents[:, 1]
    
    result = f"Added new columns with principal components values: pc_x, pc_y from features columns {', '.join(feature_columns)}. Data sample: {df[['pc_x', 'pc_y', target_column]].head(5).to_string()}"
    send_thinking_step(func="principal_component_analysis_2D", content=result)
    return result
