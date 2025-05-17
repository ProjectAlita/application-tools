"""
Statistical model tools for pandas dataframes.
This module provides functions for statistical analysis, hypothesis testing, and regression modeling.
"""

from .base_stats import (
    convert_str_column_to_categorical, 
    convert_categorical_colum_to_numeric,
    label_based_on_bins,
    descriptive_statistics,
    standardize,
    crosstab
)

from .descriptive import (
    calculate_skewness_and_kurtosis,
    calculate_mode,
    calculate_range,
    calculate_variance,
    delimitred_column_values_to_list,
    explode,
    correlation,
    covariance,
    pairwise_correlation
)

from .hypothesis_testing import (
    one_sample_t_test,
    two_sample_t_test,
    one_way_ANOVA,
    two_way_ANOVA,
    krushkal_wallis_test,
    chi_square_test,
    chi_square_test_on_data,
    bartlett_test,
    KMO_test,
    mann_whitney_test,
    wilcoxon_test
)

from .regression import (
    linear_regression,
    logistic_regression,
    mixed_effect_lm,
    predict,
    factorAnalysis,
    principal_component_analysis_2D
)

def _generate_function_docs(func, with_examples=True):
    """Generate documentation for a function in the expected format."""
    doc = func.__doc__ or ""
    doc = doc.strip().split('\n')[0]  # Get the first line of docstring
    
    # Add examples for some common functions if requested
    examples = {
        "label_based_on_bins": "label_based_on_bins(df, 'age', '0|18|65|120', 'child|adult|senior')",
        "descriptive_statistics": "descriptive_statistics(df, 'age|height|weight', 'mean|median|std', 'gender')",
        "standardize": "standardize(df, 'height|weight')",
        "crosstab": "crosstab(df, 'gender|age_group')",
        "calculate_skewness_and_kurtosis": "calculate_skewness_and_kurtosis(df, 'height|weight')",
        "calculate_mode": "calculate_mode(df, 'education|occupation')",
        "calculate_range": "calculate_range(df, 'age|salary')",
        "calculate_variance": "calculate_variance(df, 'height|weight')",
        "correlation": "correlation(df, 'height|weight|age', 'pearson')",
        "one_sample_t_test": "one_sample_t_test(df, 'height', '170')",
        "two_sample_t_test": "two_sample_t_test(df, 'male_height', 'female_height')",
        "one_way_ANOVA": "one_way_ANOVA(df, 'weight|group', 'weight ~ C(group)')",
        "linear_regression": "linear_regression(df, 'age|height|weight', 'weight ~ age + height', 'weight')",
        "predict": "predict(df, 'age|height', '30|175')"
    }
    
    if with_examples and func.__name__ in examples:
        doc += f" Example: {examples[func.__name__]}"
    
    return f"<function>\ndef {func.__name__}(df: pd.DataFrame, ...) -> str:\n    '''{doc}'''\n</function>"

# Group functions by category
function_categories = {
    "Basic Statistical Functions": [
        convert_str_column_to_categorical,
        convert_categorical_colum_to_numeric,
        label_based_on_bins,
        descriptive_statistics,
        standardize,
        crosstab
    ],
    "Descriptive Statistics Functions": [
        calculate_skewness_and_kurtosis,
        calculate_mode,
        calculate_range,
        calculate_variance,
        explode,
        delimitred_column_values_to_list,
        covariance,
        correlation,
        pairwise_correlation
    ],
    "Hypothesis Testing Functions": [
        one_sample_t_test,
        two_sample_t_test,
        one_way_ANOVA,
        two_way_ANOVA,
        krushkal_wallis_test,
        chi_square_test,
        chi_square_test_on_data,
        bartlett_test,
        KMO_test,
        mann_whitney_test,
        wilcoxon_test
    ],
    "Regression and Machine Learning Functions": [
        linear_regression,
        logistic_regression,
        mixed_effect_lm,
        predict,
        factorAnalysis,
        principal_component_analysis_2D
    ]
}

# Build the prompt_addon dynamically
prompt_addon_parts = ["The following statistical analysis functions are available in the environment and can be used directly:"]

for category, functions in function_categories.items():
    prompt_addon_parts.append(f"\n--- {category} ---\n")
    for func in functions:
        prompt_addon_parts.append(_generate_function_docs(func))

prompt_addon = "\n\n".join(prompt_addon_parts)

__all__ = [
    # base_stats
    'convert_str_column_to_categorical', 
    'convert_categorical_colum_to_numeric',
    'label_based_on_bins',
    'descriptive_statistics',
    'standardize',
    'crosstab',
    
    # descriptive
    'calculate_skewness_and_kurtosis',
    'calculate_mode',
    'calculate_range',
    'calculate_variance',
    'delimitred_column_values_to_list',
    'explode',
    'correlation',
    'covariance',
    'pairwise_correlation',
    
    # hypothesis_testing
    'one_sample_t_test',
    'two_sample_t_test',
    'one_way_ANOVA',
    'two_way_ANOVA',
    'krushkal_wallis_test',
    'chi_square_test',
    'chi_square_test_on_data',
    'bartlett_test',
    'KMO_test',
    'mann_whitney_test',
    'wilcoxon_test',
    
    # regression
    'linear_regression',
    'logistic_regression',
    'mixed_effect_lm',
    'predict',
    'factorAnalysis',
    'principal_component_analysis_2D',
    
    # prompt addon
    'prompt_addon'
]