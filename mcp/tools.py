from typing import Dict, Any, List
from django.contrib.auth.models import User
from apps.documents.models import Document, ExtractedEntity
from apps.analysis.models import AnalysisResult

class MCPDocumentTools:
    """MCP Tools for Document Operations"""
    
    @staticmethod
    async def extract_entities(document_id: str) -> Dict[str, Any]:
        """Extract entities from a processed document"""
        try:
            document = Document.objects.get(id=document_id)
            
            if document.status != 'completed':
                return {
                    "error": "Document processing not completed",
                    "status": document.status
                }
            
            entities = document.extracted_entities.all()
            
            return {
                "document_id": document_id,
                "entities": [
                    {
                        "id": str(entity.id),
                        "type": entity.entity_type,
                        "value": entity.value,
                        "confidence": entity.confidence,
                        "page_number": entity.page_number,
                        "coordinates": entity.coordinates
                    }
                    for entity in entities
                ],
                "total_entities": entities.count(),
                "extraction_confidence": document.confidence_score
            }
            
        except Document.DoesNotExist:
            return {"error": "Document not found"}
    
    @staticmethod
    async def classify_document(document_id: str) -> Dict[str, Any]:
        """Get document classification results"""
        try:
            document = Document.objects.get(id=document_id)
            
            return {
                "document_id": document_id,
                "document_type": document.document_type,
                "confidence": document.confidence_score,
                "classification_metadata": document.metadata.get('classification', {}),
                "status": document.status
            }
            
        except Document.DoesNotExist:
            return {"error": "Document not found"}
    
    @staticmethod
    async def get_risk_assessment(document_id: str) -> Dict[str, Any]:
        """Get risk assessment for insurance documents"""
        try:
            document = Document.objects.get(id=document_id)
            
            # Get detailed analysis if available
            try:
                analysis = document.detailed_analysis
                return {
                    "document_id": document_id,
                    "risk_score": analysis.risk_score,
                    "confidence_score": analysis.confidence_score,
                    "completeness_score": analysis.completeness_score,
                    "accuracy_score": analysis.accuracy_score,
                    "fraud_indicators": analysis.fraud_indicators,
                    "recommendations": analysis.recommendations,
                    "required_actions": analysis.required_actions
                }
            except AnalysisResult.DoesNotExist:
                return {
                    "document_id": document_id,
                    "message": "Risk assessment not available",
                    "status": document.status
                }
                
        except Document.DoesNotExist:
            return {"error": "Document not found"}