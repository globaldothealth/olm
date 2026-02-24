"Avian Influenza outbreak specific functions"

import pandas as pd

from ..plots import stacked_barchart


def plot_avian_influenza_age_gender(df: pd.DataFrame) -> pd.DataFrame:
    color_column = "Gender"
    y_axis = "Age"

    df = df[df[y_axis].notnull()]

    # Age-Gender plot specific
    df[color_column] = df[color_column].fillna(value="unknown")
    df = df.infer_objects(copy=False).replace('>65', '>=18')  # Person above 65 years of age is also older than 18
    df = df.sort_values(by=[color_column])
    return stacked_barchart(df, y_axis, color_column, "Case Count", "Age Group")

def plot_avian_influenza_genomics(df: pd.DataFrame) -> pd.DataFrame:
    color_column = "Animal Exposure"
    y_axis = "Genomics_Genotype"

    df = df[df[y_axis].notnull()]

    # Genomics plot specific
    df[color_column] = df["Contact_animal"] + ' ' + df["Contact_animal_species"]
    df = df.replace({color_column: {
        'COMMERCIAL Cow': "Cattle",
        "COMMERCIAL Poultry": "Poultry",
        "BACKYARD Birds": "Other",
        "BACKYARD Poultry": "Other"
    }})

    return stacked_barchart(df, y_axis, color_column, "Case Count", "Genomics Genotype")


def table_avian_influenza_exposure(df: pd.DataFrame, case_status_value: str, groupby_col: str, groupby_col_name: str,
                                   change_since_last_report: dict[str, int]):
    cattle_column = 'Exposure from Commercial Cattle'
    poultry_column = 'Exposure from Commercial Poultry'
    other_column = 'Other Animal Exposure'
    unknown_column = 'Exposure Source Unknown'
    total_column = 'Total'
    change_column = 'Change Since Last Report'

    # Extract details for exposure source over location
    df = df[df['Case_status'] == case_status_value]
    total_count = df[groupby_col].value_counts()
    additional_counts = [
        {'column_name': cattle_column, 'data': df[df['Contact_animal_species'] == 'Cow'][groupby_col].value_counts()},
        {'column_name': poultry_column,
         'data': df[(df['Contact_animal'] == 'COMMERCIAL') & (df['Contact_animal_species'] == 'Poultry')][
             groupby_col].value_counts()},
        {'column_name': other_column, 'data': df[df['Contact_animal'] == 'BACKYARD'][groupby_col].value_counts()},
        {'column_name': unknown_column, 'data': df[df['Contact_animal'].isna()][groupby_col].value_counts()},
        {'column_name': change_column, 'data': change_since_last_report},
    ]

    # Generate dataframe
    table = pd.DataFrame({groupby_col_name: total_count.index, total_column: total_count.values})
    for additional_count in additional_counts:
        table[additional_count['column_name']] = table[groupby_col_name].map(additional_count['data'])

    # Reorder dataframe columns
    table = table.loc[
        :, [groupby_col_name, cattle_column, poultry_column, other_column, unknown_column, total_column,
            change_column]]

    # Replace float values with int and fill empty cells with zeros
    pd.options.display.float_format = '{:,.0f}'.format
    return table.fillna(int(0))