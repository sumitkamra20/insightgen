import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This is useful for local development but won't affect production
# where environment variables are set directly
try:
    load_dotenv()
except:
    pass  # Silently continue if .env file doesn't exist

# Get port from environment or use default
# In Render.com, the PORT environment variable is automatically set
port = int(os.getenv("PORT", os.getenv("API_PORT", 8000)))

if __name__ == "__main__":
    print(f"Starting InsightGen API server on port {port}...")
    print(f"API documentation available at: http://localhost:{port}/docs")
    uvicorn.run("insightgen.app:app", host="0.0.0.0", port=port, reload=True)
