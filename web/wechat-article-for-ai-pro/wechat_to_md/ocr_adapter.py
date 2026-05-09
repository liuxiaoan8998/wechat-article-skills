"""OCR Adapter: Unified interface for multiple OCR engines.

Supports:
- RapidOCR (default): Local, fast, free
- AI Vision: Cloud-based, high accuracy
- Auto: Choose based on image complexity
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class OCREngine(ABC):
    """Abstract base class for OCR engines."""
    
    @abstractmethod
    def ocr(self, image_path: Path) -> str:
        """OCR a single image and return text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this OCR engine is available."""
        pass


class RapidOCREngine(OCREngine):
    """RapidOCR engine - local, fast, free."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._engine = None
        self._init_engine()
    
    def _init_engine(self):
        """Initialize RapidOCR engine."""
        try:
            from rapidocr_onnxruntime import RapidOCR
            
            # Get config values
            model = self.config.get('model', 'ch_PP-OCRv4')
            language = self.config.get('language', 'ch')
            
            # Initialize with config
            self._engine = RapidOCR(
                config_path=None,  # Use default config
                model_path=None,   # Auto-download model
            )
        except Exception as e:
            print(f"[RapidOCR] Initialization failed: {e}")
            self._engine = None
    
    def is_available(self) -> bool:
        """Check if RapidOCR is available."""
        return self._engine is not None
    
    def ocr(self, image_path: Path) -> str:
        """OCR using RapidOCR."""
        if not self._engine:
            return "[RapidOCR not available]"
        
        try:
            result, elapse = self._engine(str(image_path))
            
            # Result format: [[box, text, confidence], ...]
            if result and len(result) > 0:
                texts = []
                for item in result:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        # item[0] = box coordinates, item[1] = text, item[2] = confidence
                        text = item[1] if isinstance(item[1], str) else str(item[1])
                        if text.strip():
                            texts.append(text)
                return "\n".join(texts) if texts else "[No text detected]"
            else:
                return "[No text detected]"
                
        except Exception as e:
            return f"[RapidOCR error: {str(e)}]"


class AIVisionEngine(OCREngine):
    """AI Vision engine - cloud-based, high accuracy."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.provider = self.config.get('provider', 'auto')
    
    def is_available(self) -> bool:
        """AI Vision is always available (via Hermes tool)."""
        return True
    
    def ocr(self, image_path: Path) -> str:
        """OCR using AI Vision (via Hermes vision_analyze tool)."""
        # This will be called by the main process
        # Return a placeholder indicating external processing needed
        return f"[AI_VISION_REQUIRED:{image_path}]"


class OCRAdapter:
    """Unified OCR adapter that manages multiple engines."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize OCR adapter.
        
        Args:
            config: Configuration dict with 'engine' key:
                - 'rapidocr': Use RapidOCR (default)
                - 'vision': Use AI Vision
                - 'auto': Auto-select based on image
        """
        self.config = config or {}
        self.engine_name = self.config.get('engine', 'rapidocr')
        self.engines: Dict[str, OCREngine] = {}
        self._init_engines()
    
    def _init_engines(self):
        """Initialize all OCR engines."""
        # RapidOCR config
        rapidocr_config = self.config.get('rapidocr', {})
        self.engines['rapidocr'] = RapidOCREngine(rapidocr_config)
        
        # AI Vision config
        vision_config = self.config.get('vision', {})
        self.engines['vision'] = AIVisionEngine(vision_config)
    
    def _get_engine(self, image_path: Optional[Path] = None) -> OCREngine:
        """Get the appropriate OCR engine."""
        if self.engine_name == 'auto' and image_path:
            # Auto-select logic:
            # - Use RapidOCR for simple text images
            # - Use AI Vision for complex layouts or if RapidOCR fails
            return self.engines['rapidocr']
        elif self.engine_name == 'vision':
            return self.engines['vision']
        else:
            # Default to RapidOCR
            return self.engines['rapidocr']
    
    def ocr(self, image_path: Path) -> str:
        """
        OCR a single image using the configured engine.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text or placeholder for external processing
        """
        engine = self._get_engine(image_path)
        return engine.ocr(image_path)
    
    def ocr_batch(self, image_paths: list[Path]) -> list[tuple[Path, str]]:
        """
        OCR multiple images.
        
        Args:
            image_paths: List of image paths
            
        Returns:
            List of (image_path, text) tuples
        """
        results = []
        for path in image_paths:
            text = self.ocr(path)
            results.append((path, text))
        return results
    
    def get_engine_status(self) -> Dict[str, bool]:
        """Get availability status of all engines."""
        return {
            name: engine.is_available()
            for name, engine in self.engines.items()
        }


# Global adapter instance (lazy initialization)
_adapter: Optional[OCRAdapter] = None


def get_adapter(config: Optional[Dict[str, Any]] = None) -> OCRAdapter:
    """Get or create global OCR adapter."""
    global _adapter
    if _adapter is None or config is not None:
        _adapter = OCRAdapter(config)
    return _adapter


def ocr_image(image_path: Path, config: Optional[Dict[str, Any]] = None) -> str:
    """Convenience function to OCR a single image."""
    adapter = get_adapter(config)
    return adapter.ocr(image_path)


def load_config_from_env() -> Dict[str, Any]:
    """Load OCR config from environment variables."""
    config = {
        'engine': os.getenv('OCR_ENGINE', 'rapidocr'),
        'rapidocr': {
            'model': os.getenv('OCR_RAPIDOCR_MODEL', 'ch_PP-OCRv4'),
            'language': os.getenv('OCR_RAPIDOCR_LANGUAGE', 'ch'),
        },
        'vision': {
            'provider': os.getenv('OCR_VISION_PROVIDER', 'auto'),
        }
    }
    return config
