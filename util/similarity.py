import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def best_matches(list1, list2):
    """
    For each string in list1, find the string in list2 with the highest cosine similarity.
    The resulting DataFrame is sorted in descending order by the similarity score.

    Parameters:
        list1 (list of str): List of strings.
        list2 (list of str): Another list of strings.

    Returns:
        pd.DataFrame: A dataframe with columns 'name_1', 'name_2', and 'score'.
                      Each row contains a string from list1, its best match from list2,
                      and the cosine similarity score, sorted by score descending.
    """
    # Combine both lists to build a common vocabulary for the vectorizer.
    combined_texts = list1 + list2

    # Initialize and fit the vectorizer.
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(combined_texts)

    # Split the TF-IDF matrix back into two parts corresponding to list1 and list2.
    tfidf_list1 = tfidf_matrix[: len(list1)]
    tfidf_list2 = tfidf_matrix[len(list1) :]

    # Compute the cosine similarity between each string in list1 and each string in list2.
    similarity_matrix = cosine_similarity(tfidf_list1, tfidf_list2)

    # For each string in list1, find the best matching string in list2.
    best_match_indices = similarity_matrix.argmax(axis=1)
    best_match_scores = similarity_matrix.max(axis=1)

    # Create the dataframe.
    df = pd.DataFrame(
        {
            "name_1": list1,
            "name_2": [list2[idx] for idx in best_match_indices],
            "score": best_match_scores,
        }
    )

    # Sort the dataframe by score in descending order.
    df.sort_values("score", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# Example usage:
if __name__ == "__main__":
    list1 = [
        "The quick brown fox jumps over the lazy dog",
        "I love programming in Python",
        "Data science is fun",
    ]

    list2 = [
        "Python programming is enjoyable",
        "The lazy dog was jumped over by a quick brown fox",
        "Machine learning and data science",
    ]

    result_df = best_matches(list1, list2)
    print(result_df)
