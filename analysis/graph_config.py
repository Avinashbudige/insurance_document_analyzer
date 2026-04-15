from typing import Dict, Any
from enum import Enum

class ProcessingStep(Enum):
    INPUT_PROCESSING = "input_processing"
    DOCUMENT_CLASSIFICATION = "document_classification"
    OCR_PROCESSING = "ocr_processing"
    TEXT_EXTRACTION = "text_extraction"
    ENTITY_EXTRACTION = "entity_extraction"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    COMPLETION = "completion"

class GraphConfig:
    """Configuration for LangGraph processing"""
    
    # Processing timeouts (in seconds)
    INPUT_TIMEOUT = 30
    OCR_TIMEOUT = 120
    EXTRACTION_TIMEOUT = 60
    ANALYSIS_TIMEOUT = 90
    VALIDATION_TIMEOUT = 30
    
    # Retry configuration
    MAX_RETRIES = 3
    OCR_RETRY_DELAY = 5
    OCR_MIN_CONFIDENCE = 0.7
    
    # Progress weights
    PROGRESS_WEIGHTS = {
        ProcessingStep.INPUT_PROCESSING: 5,
        ProcessingStep.DOCUMENT_CLASSIFICATION: 10,
        ProcessingStep.OCR_PROCESSING: 15,
        ProcessingStep.TEXT_EXTRACTION: 15,
        ProcessingStep.ENTITY_EXTRACTION: 15,
        ProcessingStep.ANALYSIS: 20,
        ProcessingStep.VALIDATION: 10,
        ProcessingStep.COMPLETION: 10
    }
    
    @classmethod
    def get_step_progress(cls, step: ProcessingStep) -> int:
        """Get progress percentage for a step"""
        return cls.PROGRESS_WEIGHTS.get(step, 0)
    
    @classmethod
    def get_total_progress(cls) -> int:
        """Get total progress percentage"""
        return sum(cls.PROGRESS_WEIGHTS.values())
    
    @classmethod
    def calculate_progress(cls, current_step: ProcessingStep) -> float:
        """Calculate cumulative progress up to current step"""
        total = cls.get_total_progress()
        cumulative = 0
        
        for step in ProcessingStep:
            cumulative += cls.get_step_progress(step)
            if step == current_step:
                break
        
        return (cumulative / total) * 100