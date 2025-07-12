__version__ = "0.1.4"
from freebooks.main import convert_aax_to_audio

# This allows users to import convert_aax_to_audio directly from freebooks
# without needing to reference the main module.
# Example: from freebooks import convert_aax_to_audio
__all__ = ["convert_aax_to_audio"]
