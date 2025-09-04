# app/services/calculator.py

# This file is now deprecated and will be removed after the refactor is complete.
# Its logic has been moved to the `engine/` and `adapters/` directories.
# Keeping it temporarily to avoid breaking imports until the final step.


class PortfolioPerformanceCalculator:
    def __init__(self, config):
        raise DeprecationWarning(
            "PortfolioPerformanceCalculator is deprecated. "
            "Use functions from adapters.api_adapter and engine.compute instead."
        )

    def calculate_performance(self, daily_data_list, config):
        raise DeprecationWarning("This method is deprecated.")

    def get_summary_performance(self, calculated_results):
        raise DeprecationWarning("This method is deprecated.")