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
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except:
    pass  # Silently continue if .env file doesn't exist

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
        logger.info(f"Initializing GeneratorRegistry with storage_mode={self.storage_mode}, gcs_bucket={self.gcs_bucket}")
        self._load_generators()
        logger.info(f"Loaded {len(self.generators)} generators: {list(self.generators.keys())}")

    def _load_generators(self) -> None:
        """
        Load all generators based on the storage mode.

        For local storage, loads from the generators directory in the project root.
        For cloud storage, loads from a GCS bucket specified by GCS_BUCKET env var.
        """
        if self.storage_mode == "local":
            logger.info("Using local storage mode for generators")
            self._load_local_generators()
        elif self.storage_mode == "gcs":
            logger.info("Using GCS storage mode for generators")
            self._load_gcs_generators()
        else:
            logger.warning(f"Unknown storage mode: {self.storage_mode}, falling back to local")
            self._load_local_generators()

    def _load_local_generators(self) -> None:
        """Load generators from local YAML files in the generators directory."""
        # Get the project root directory (one level up from this file)
        project_root = Path(__file__).parent.parent
        generators_dir = project_root / "generators"

        logger.info(f"Looking for generators in: {generators_dir.absolute()}")

        if not generators_dir.exists():
            logger.error(f"Generators directory not found: {generators_dir.absolute()}")
            return

        # List all files in the directory
        all_files = list(generators_dir.glob("*"))
        logger.info(f"Found {len(all_files)} files in generators directory: {[f.name for f in all_files]}")

        # Load all YAML files in the generators directory
        for file_path in generators_dir.glob("*.yaml"):
            try:
                logger.info(f"Attempting to load generator from: {file_path.name}")
                with open(file_path, "r") as f:
                    generator = yaml.safe_load(f)

                # Validate the generator structure
                if self._validate_generator(generator):
                    generator_id = generator["id"]
                    self.generators[generator_id] = generator
                    logger.info(f"Successfully loaded generator: {generator_id} from {file_path.name}")
                else:
                    logger.error(f"Invalid generator structure in {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading generator from {file_path.name}: {str(e)}")

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
        required_fields = ["id", "name", "description", "version", "prompts"]
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
        generator = self.generators.get(generator_id)

        if generator:
            # Add default workflow settings if needed
            if "workflow" not in generator:
                # Get parallel_slides from environment variable
                try:
                    parallel_slides = int(os.getenv("PARALLEL_SLIDES", "5"))
                except (ValueError, TypeError):
                    parallel_slides = 5
                    logger.warning(f"Invalid PARALLEL_SLIDES value, using default: {parallel_slides}")

                # Add the default workflow
                generator["workflow"] = {
                    "parallel_observation_processing": True,
                    "sequential_headline_generation": True,
                    "context_window_size": 20,
                    "parallel_slides": parallel_slides
                }
                logger.info(f"Added default workflow settings to generator {generator_id}")
            else:
                # Enforce our required settings
                workflow = generator["workflow"]
                workflow["parallel_observation_processing"] = True
                workflow["sequential_headline_generation"] = True
                workflow["context_window_size"] = 20

                # Get parallel_slides from environment variable
                try:
                    parallel_slides = int(os.getenv("PARALLEL_SLIDES", "5"))
                except (ValueError, TypeError):
                    parallel_slides = workflow.get("parallel_slides", 5)
                    logger.warning(f"Invalid PARALLEL_SLIDES value, using existing or default: {parallel_slides}")

                workflow["parallel_slides"] = parallel_slides

        return generator

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
                "version": g["version"],
                "example_prompt": g.get("example_prompt", "")
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
