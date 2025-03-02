import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get port from environment or use default
port = int(os.getenv("API_PORT", 8000))

if __name__ == "__main__":
    print(f"Starting InsightGen API server on port {port}...")
    print(f"API documentation available at: http://localhost:{port}/docs")
    uvicorn.run("insightgen.api.app:app", host="0.0.0.0", port=port, reload=True)
