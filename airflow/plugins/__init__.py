# Plugins package for InsightGen Airflow workflows
from airflow.plugins_manager import AirflowPlugin

# Define utilities module directly in this file
class InsightGenUtils:
    """Utility functions for InsightGen workflow orchestration"""

    @staticmethod
    def validate_data(data):
        """Example validation function"""
        return data is not None


class InsightGenPlugin(AirflowPlugin):
    """Plugin for InsightGen workflow orchestration"""
    name = 'insightgen_plugin'
    operators = []
    hooks = []
    executors = []
    macros = [InsightGenUtils]
    admin_views = []
    flask_blueprints = []
    menu_links = []
