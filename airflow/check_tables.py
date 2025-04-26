from google.cloud import bigquery

def main():
    client = bigquery.Client()
    print("Checking for DAG-created tables...")

    # List all tables in the dataset
    dataset_id = "insightgen-453212.insightgen_analytics"
    tables = list(client.list_tables(dataset_id))
    print(f"Total tables in {dataset_id}: {len(tables)}")
    for table in tables:
        print(f"  - {table.table_id}")
        # Get table metadata and row count
        try:
            table_ref = client.get_table(f"{dataset_id}.{table.table_id}")
            print(f"    * Row count: {table_ref.num_rows}")
            print(f"    * Created: {table_ref.created}")
        except Exception as e:
            print(f"    * Error getting details: {e}")

if __name__ == "__main__":
    main()
