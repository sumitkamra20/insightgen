from google.cloud import bigquery

def main():
    # Get client
    client = bigquery.Client()
    print("Running test query...")

    # Test 1: Simple query
    query = "SELECT 1 as test"
    print("Executing:", query)
    job = client.query(query)
    result = job.result()
    print("Result:", list(result))

    # Test 2: Check if analytics dataset exists
    try:
        dataset_id = "insightgen-453212.insightgen_analytics"
        print(f"Checking if dataset {dataset_id} exists...")
        client.get_dataset(dataset_id)
        print("Dataset exists!")
    except Exception as e:
        print(f"Dataset error: {e}")

    # Test 3: Try to create the dataset if it doesn't exist
    try:
        print("Creating or getting dataset...")
        dataset = bigquery.Dataset(f"{client.project}.insightgen_analytics")
        dataset = client.create_dataset(dataset, exists_ok=True)
        print(f"Dataset {dataset.dataset_id} created/confirmed successfully")
    except Exception as e:
        print(f"Failed to create dataset: {e}")

    # Test 4: Try to create a test table
    try:
        print("Creating test table...")
        query = """
        CREATE OR REPLACE TABLE `insightgen-453212.insightgen_analytics.test_table`
        AS SELECT 1 as dummy
        """
        job = client.query(query)
        result = job.result()
        print("Test table created successfully!")
    except Exception as e:
        print(f"Failed to create test table: {e}")

if __name__ == "__main__":
    main()
