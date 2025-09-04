# engine/exceptions.py


class EngineError(Exception):
    """Base exception for all engine-related errors."""

    def __init__(self, message="An error occurred in the performance engine."):
        self.message = message
        super().__init__(self.message)


class InvalidEngineInputError(EngineError):
    """Raised when the input data for the engine is invalid."""

    def __init__(self, message="Invalid input data provided to the engine."):
        self.message = message
        super().__init__(self.message)


class EngineCalculationError(EngineError):
    """Raised when there's an error in the core engine calculation logic."""

    def __init__(self, message="An error occurred during an engine calculation."):
        self.message = message
        super().__init__(self.message)