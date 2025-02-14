import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from functools import partial
from util import weather  # Assumes a module `weather` with `estimate_water_needs` is available


def best_matches(list1: list[str], list2: list[str]) -> pd.DataFrame:
    """
    For each string in list1, find the string in list2 with the highest cosine similarity.

    Parameters:
        list1 (list[str]): List of strings to be matched.
        list2 (list[str]): List of candidate strings.

    Returns:
        pd.DataFrame: DataFrame with columns 'name_1', 'name_2', and 'score', sorted in descending order by score.
    """
    # Combine texts to build a common vocabulary and create TF-IDF vectors.
    combined_texts = list1 + list2
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(combined_texts)

    # Split the TF-IDF matrix into vectors for list1 and list2.
    tfidf_list1 = tfidf_matrix[: len(list1)]
    tfidf_list2 = tfidf_matrix[len(list1):]

    # Compute the cosine similarity between each string in list1 and each string in list2.
    similarity_matrix = cosine_similarity(tfidf_list1, tfidf_list2)

    # Find the best match for each string in list1.
    best_match_indices = similarity_matrix.argmax(axis=1)
    best_match_scores = similarity_matrix.max(axis=1)

    results_df = pd.DataFrame({
        "name_1": list1,
        "name_2": [list2[idx] for idx in best_match_indices],
        "score": best_match_scores,
    })
    return results_df.sort_values("score", ascending=False).reset_index(drop=True)


def filter_matches(similarity_df: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
    """
    Filter the similarity DataFrame to include only high-confidence matches.

    Parameters:
        similarity_df (pd.DataFrame): DataFrame containing similarity scores.
        threshold (float): Minimum similarity score to consider a match high-confidence.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    return similarity_df[similarity_df["score"] > threshold].copy()


def merge_green_area_and_matches(green_area_df: pd.DataFrame, similarity_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge the green area DataFrame with the similarity matches.

    Parameters:
        green_area_df (pd.DataFrame): DataFrame with green area information (expects columns 'PARK ADI' and 'ÇİM ALAN').
        similarity_df (pd.DataFrame): Filtered similarity DataFrame (expects columns 'name_1' and 'name_2').

    Returns:
        pd.DataFrame: Merged DataFrame with columns 'PARK ADI', 'grass_area', and 'name_invoice'.
    """
    merged_df = green_area_df[["PARK ADI", "ÇİM ALAN"]].merge(
        similarity_df[["name_1", "name_2"]],
        left_on="PARK ADI",
        right_on="name_1",
        how="inner",
    )
    merged_df.rename(columns={"name_2": "name_invoice", "ÇİM ALAN": "grass_area"}, inplace=True)
    return merged_df


def compute_water_needs(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Compute daily water needs between start_date and end_date.
    Water need is set to 0 outside the watering season (June to October).

    Parameters:
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
        pd.DataFrame: DataFrame with columns 'date' and 'water_need_m3'.
    """
    # Create a date range and build a DataFrame.
    date_range = pd.date_range(start=start_date, end=end_date)
    df_dates = pd.DataFrame({"date": date_range.date})

    # Create a partial function for water estimation with fixed parameters.
    water_estimator = partial(
        weather.estimate_water_needs,
        lat=39.9208,
        lon=32.8541,
        kc=0.8,
        elevation=900,
    )

    df_water = water_estimator(
        start_date=df_dates.date.iloc[0],
        end_date=df_dates.date.iloc[-1],
        park_area=1,
    )[["date", "water_need_m3"]]
    df_water["date"] = pd.to_datetime(df_water["date"])

    # Only consider water needs during the watering season (June to October).
    df_water["water_need_m3"] = df_water.apply(
        lambda row: row["water_need_m3"] if 6 <= row["date"].month <= 10 else 0,
        axis=1,
    )
    return df_water


def calculate_total_water(row: pd.Series, water_data: pd.DataFrame) -> float:
    """
    Calculate the total water need for an invoice row over its read date range.

    Parameters:
        row (pd.Series): A row from the invoice DataFrame with 'start_read_date' and 'end_read_date'.
        water_data (pd.DataFrame): DataFrame with daily water needs.

    Returns:
        float: Total water need.
    """
    start_date = pd.to_datetime(row["start_read_date"])
    end_date = pd.to_datetime(row["end_read_date"])
    mask = (water_data["date"] >= start_date) & (water_data["date"] <= end_date)
    return water_data.loc[mask, "water_need_m3"].sum()


def process_invoices(invoice_df: pd.DataFrame, matched_df: pd.DataFrame, water_data: pd.DataFrame) -> pd.DataFrame:
    """
    Process invoice data by calculating water needs and merging with grass area information.

    Parameters:
        invoice_df (pd.DataFrame): Invoice DataFrame (expects columns 'name', 'start_read_date', 'end_read_date', 'volume', etc.).
        matched_df (pd.DataFrame): DataFrame containing matched names and grass area (expects columns 'name_invoice' and 'grass_area').
        water_data (pd.DataFrame): DataFrame with daily water needs.

    Returns:
        pd.DataFrame: Processed invoice DataFrame with estimated water volume.
    """
    # Calculate water need for each invoice.
    invoice_df["water_need_m3"] = invoice_df.apply(
        lambda row: calculate_total_water(row, water_data), axis=1
    )

    # Merge invoice data with matched grass area information.
    merged_invoice = invoice_df.merge(
        matched_df[["name_invoice", "grass_area"]],
        left_on="name",
        right_on="name_invoice",
        how="left",
    )

    # Drop rows with no matching grass area.
    merged_invoice.dropna(subset=["grass_area"], inplace=True)

    # Calculate total water need for the grass area.
    merged_invoice["water_need_total"] = merged_invoice["water_need_m3"] * merged_invoice["grass_area"]

    # Select and rename columns.
    processed_invoice = merged_invoice[
        ["subscription", "name", "start_read_date", "end_read_date", "water_need_total", "volume", "grass_area"]
    ].copy()
    processed_invoice.rename(columns={"water_need_total": "estimated_volume"}, inplace=True)
    processed_invoice["estimated_volume"] = processed_invoice["estimated_volume"].astype(int)

    return processed_invoice


def main():
    """
    Main function to orchestrate the processing of green area and invoice data.
    """
    # Load data (adjust file paths as needed).
    ca_green_area_df = pd.read_csv("data/processed/ca_area.csv")
    ca_invoice_df = pd.read_csv("data/processed/ca_invoice.csv")

    # 1. Compute name similarity between green area names and invoice names.
    green_names = ca_green_area_df["PARK ADI"].unique().tolist()
    invoice_names = ca_invoice_df["name"].unique().tolist()
    similarity_df = best_matches(green_names, invoice_names)
    similarity_df.to_csv("data/final/ca_name_matching.csv", index=False)

    # 2. Filter similarity matches by a score threshold.
    filtered_similarity_df = filter_matches(similarity_df, threshold=0.95)

    # 3. Merge green area data with the filtered matches.
    matched_green_area_df = merge_green_area_and_matches(ca_green_area_df, filtered_similarity_df)

    # 4. Compute daily water needs over the specified period.
    water_data = compute_water_needs(start_date="2015-01-01", end_date="2024-01-10")

    # 5. Process invoices to calculate estimated water volumes.
    processed_invoice_df = process_invoices(ca_invoice_df, matched_green_area_df, water_data)
    processed_invoice_df.to_csv("data/final/ca_invoice.csv", index=False)

    print("Processing complete. Output saved to 'data/final/ca_invoice.csv'.")


if __name__ == "__main__":
    main()