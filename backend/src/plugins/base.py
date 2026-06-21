from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any


class BasePlugin(ABC):
    """
    Abstract base class for custom OCR plugins.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def get_hocr(self, image_path: Path) -> str:
        """
        Process the image and return the hOCR XML string.

        Args:
            image_path: Path to the input image file.

        Returns:
            str: The hOCR XML content.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the plugin."""
        pass
