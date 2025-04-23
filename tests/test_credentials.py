import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv(override=True)

def test_print_credential_info():
    """Print information about the current Google Cloud credentials."""
    # Check environment variable
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"\nGOOGLE_APPLICATION_CREDENTIALS env var: {cred_path}")

    # Create a client and get information about the credentials
    client = bigquery.Client()

    # Print project info
    print(f"Project: {client.project}")

    # Try to get service account info if available
    try:
        from google.auth import default
        credentials, project = default()
        print(f"Authenticated as: {credentials.service_account_email if hasattr(credentials, 'service_account_email') else 'Not a service account'}")
        print(f"Using project: {project}")
    except Exception as e:
        print(f"Error getting credential details: {e}")

    # List available datasets to check permissions
    try:
        print("\nDatasets you have access to:")
        datasets = list(client.list_datasets())
        if datasets:
            for dataset in datasets:
                print(f"- {dataset.dataset_id}")
        else:
            print("No datasets found in this project or no permission to list datasets")
    except Exception as e:
        print(f"Error listing datasets: {e}")

    return True  # Make the test pass

if __name__ == "__main__":
    test_print_credential_info()
