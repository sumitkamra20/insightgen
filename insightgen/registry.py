"""
Generator Registry Module

This module provides functionality to load and manage generators from YAML files.
Generators define the prompts and workflow for generating observations and headlines.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeneratorRegistry:
    """
    Registry for managing generators loaded from YAML files.

    This class handles loading generators from either local files or cloud storage,
    depending on the STORAGE_MODE environment variable.
    """

    def __init__(self):
        """Initialize the generator registry."""
        self.generators = {}
        self.storage_mode = os.getenv("STORAGE_MODE", "local")
        self.gcs_bucket = os.getenv("GCS_BUCKET", "")
        self._load_generators()

    def _load_generators(self) -> None:
        """
        Load all generators based on the storage mode.

        For local storage, loads from the generators directory in the project root.
        For cloud storage, loads from a GCS bucket specified by GCS_BUCKET env var.
        """
        if self.storage_mode == "local":
            self._load_local_generators()
        elif self.storage_mode == "gcs":
            self._load_gcs_generators()
        else:
            logger.warning(f"Unknown storage mode: {self.storage_mode}, falling back to local")
            self._load_local_generators()

    def _load_local_generators(self) -> None:
        """Load generators from local YAML files in the generators directory."""
        # Get the project root directory (one level up from this file)
        project_root = Path(__file__).parent.parent
        generators_dir = project_root / "generators"

        if not generators_dir.exists():
            logger.warning(f"Generators directory not found: {generators_dir}")
            return

        # Load all YAML files in the generators directory
        for file_path in generators_dir.glob("*.yaml"):
            try:
                with open(file_path, "r") as f:
                    generator = yaml.safe_load(f)

                # Validate the generator structure
                if self._validate_generator(generator):
                    generator_id = generator["id"]
                    self.generators[generator_id] = generator
                    logger.info(f"Loaded generator: {generator_id} from {file_path.name}")
                else:
                    logger.error(f"Invalid generator structure in {file_path}")
            except Exception as e:
                logger.error(f"Error loading generator from {file_path}: {str(e)}")

    def _load_gcs_generators(self) -> None:
        """Load generators from YAML files in a GCS bucket."""
        if not self.gcs_bucket:
            logger.error("GCS_BUCKET environment variable not set")
            return

        try:
            # Import Google Cloud Storage client library
            from google.cloud import storage

            # Create a storage client
            storage_client = storage.Client()

            # Get the bucket
            bucket = storage_client.bucket(self.gcs_bucket)

            # List all blobs in the bucket with .yaml extension
            blobs = bucket.list_blobs(prefix="generators/")

            for blob in blobs:
                if blob.name.endswith(".yaml"):
                    try:
                        # Download the blob as a string
                        yaml_content = blob.download_as_string().decode("utf-8")

                        # Parse the YAML content
                        generator = yaml.safe_load(yaml_content)

                        # Validate the generator structure
                        if self._validate_generator(generator):
                            generator_id = generator["id"]
                            self.generators[generator_id] = generator
                            logger.info(f"Loaded generator: {generator_id} from GCS: {blob.name}")
                        else:
                            logger.error(f"Invalid generator structure in GCS: {blob.name}")
                    except Exception as e:
                        logger.error(f"Error loading generator from GCS: {blob.name}: {str(e)}")
        except ImportError:
            logger.error("Google Cloud Storage library not installed. Run: pip install google-cloud-storage")
        except Exception as e:
            logger.error(f"Error accessing GCS bucket: {str(e)}")

    def _validate_generator(self, generator: Dict[str, Any]) -> bool:
        """
        Validate the structure of a generator.

        Args:
            generator: The generator dictionary to validate

        Returns:
            bool: True if the generator is valid, False otherwise
        """
        required_fields = ["id", "name", "description", "version", "prompts", "workflow"]
        for field in required_fields:
            if field not in generator:
                logger.error(f"Missing required field in generator: {field}")
                return False

        # Check prompts structure
        prompts = generator.get("prompts", {})
        if not isinstance(prompts, dict):
            logger.error("Prompts must be a dictionary")
            return False

        for prompt_type in ["observations", "headlines"]:
            if prompt_type not in prompts:
                logger.error(f"Missing prompt type: {prompt_type}")
                return False

            prompt = prompts[prompt_type]
            if "system_prompt" not in prompt:
                logger.error(f"Missing system_prompt in {prompt_type}")
                return False

        return True

    def get_generator(self, generator_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a generator by ID.

        Args:
            generator_id: The ID of the generator to retrieve

        Returns:
            The generator dictionary, or None if not found
        """
        return self.generators.get(generator_id)

    def list_generators(self) -> List[Dict[str, str]]:
        """
        List all available generators.

        Returns:
            A list of dictionaries with generator metadata
        """
        return [
            {
                "id": g["id"],
                "name": g["name"],
                "description": g["description"],
                "version": g["version"]
            }
            for g in self.generators.values()
        ]

    def get_default_generator_id(self) -> str:
        """
        Get the ID of the default generator.

        Returns:
            The ID of the default generator, or the first available generator if not found
        """
        if "BGS_Default" in self.generators:
            return "BGS_Default"

        # If BGS_Default is not found, return the first available generator
        if self.generators:
            return next(iter(self.generators.keys()))

        # If no generators are available, raise an exception
        raise ValueError("No generators available")
