import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource, TextContent
from django.conf import settings
from django.contrib.auth.models import User
from apps.documents.models import Document, ProcessingLog, ExtractedEntity
from apps.analysis.models import AnalysisResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentAnalyzerMCPServer:
    """MCP Server for Document Analyzer Integration"""
    
    def __init__(self):
        self.server = Server("document-analyzer-mcp")
        self._register_tools()
        self._register_resources()
        
    def _register_tools(self):
        """Register MCP tools for document operations"""
        
        @self.server.tool()
        async def upload_document(file_path: str, user_id: str, title: str) -> Dict[str, Any]:
            """Upload and process a document"""
            try:
                # Get user
                user = User.objects.get(id=user_id)
                
                # Create document record
                document = Document.objects.create(
                    user=user,
                    title=title,
                    file_path=file_path,
                    status='uploaded'
                )
                
                # Trigger processing
                from apps.documents.tasks import process_document_async
                process_document_async.delay(str(document.id))
                
                return {
                    "success": True,
                    "document_id": str(document.id),
                    "status": "processing",
                    "message": "Document uploaded and processing started"
                }
                
            except Exception as e:
                logger.error(f"Error uploading document: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @self.server.tool()
        async def get_document_status(document_id: str) -> Dict[str, Any]:
            """Get processing status of a document"""
            try:
                document = Document.objects.get(id=document_id)
                latest_log = document.processing_logs.last()
                
                return {
                    "document_id": document_id,
                    "status": document.status,
                    "progress": getattr(document, 'processing_progress', 0),
                    "current_step": getattr(document, 'current_step', ''),
                    "estimated_time": getattr(document, 'estimated_time', 0),
                    "error_message": document.error_message,
                    "latest_log": {
                        "step": latest_log.step,
                        "status": latest_log.status,
                        "message": latest_log.message,
                        "timestamp": latest_log.timestamp.isoformat()
                    } if latest_log else None
                }
                
            except Document.DoesNotExist:
                return {
                    "error": "Document not found",
                    "document_id": document_id
                }
        
        @self.server.tool()
        async def get_analysis_results(document_id: str) -> Dict[str, Any]:
            """Get detailed analysis results"""
            try:
                document = Document.objects.get(id=document_id)
                
                return {
                    "document_id": document_id,
                    "status": document.status,
                    "confidence_score": document.confidence_score,
                    "processing_time": document.processing_time,
                    "entities": [
                        {
                            "type": entity.entity_type,
                            "value": entity.value,
                            "confidence": entity.confidence,
                            "page_number": entity.page_number
                        }
                        for entity in document.extracted_entities.all()
                    ],
                    "analysis_results": document.analysis_results,
                    "processing_logs": [
                        {
                            "step": log.step,
                            "status": log.status,
                            "message": log.message,
                            "timestamp": log.timestamp.isoformat()
                        }
                        for log in document.processing_logs.order_by('-timestamp')[:10]
                    ]
                }
                
            except Document.DoesNotExist:
                return {
                    "error": "Document not found",
                    "document_id": document_id
                }
        
        @self.server.tool()
        async def list_user_documents(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
            """List documents for a user"""
            try:
                user = User.objects.get(id=user_id)
                documents = Document.objects.filter(
                    user=user
                ).order_by('-uploaded_at')[:limit]
                
                return [
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "status": doc.status,
                        "document_type": doc.document_type,
                        "uploaded_at": doc.uploaded_at.isoformat(),
                        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                        "confidence_score": doc.confidence_score
                    }
                    for doc in documents
                ]
                
            except Exception as e:
                logger.error(f"Error listing documents: {str(e)}")
                return [{"error": str(e)}]
        
        @self.server.tool()
        async def search_documents(query: str, user_id: str) -> List[Dict[str, Any]]:
            """Search documents by content or metadata"""
            try:
                user = User.objects.get(id=user_id)
                documents = Document.objects.filter(
                    user=user
                ).filter(
                    models.Q(title__icontains=query) |
                    models.Q(extracted_text__icontains=query) |
                    models.Q(entities__value__icontains=query)
                ).distinct()
                
                return [
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "status": doc.status,
                        "document_type": doc.document_type,
                        "uploaded_at": doc.uploaded_at.isoformat(),
                        "confidence_score": doc.confidence_score,
                        "relevance_score": self._calculate_relevance(doc, query)
                    }
                    for doc in documents
                ]
                
            except Exception as e:
                logger.error(f"Error searching documents: {str(e)}")
                return [{"error": str(e)}]
    
    def _register_resources(self):
        """Register MCP resources for document access"""
        
        @self.server.resource()
        async def get_document(document_id: str) -> TextContent:
            """Access document content and metadata"""
            try:
                document = Document.objects.get(id=document_id)
                
                content = {
                    "id": str(document.id),
                    "title": document.title,
                    "type": document.document_type,
                    "status": document.status,
                    "uploaded_at": document.uploaded_at.isoformat(),
                    "processed_at": document.processed_at.isoformat() if document.processed_at else None,
                    "extracted_text": document.extracted_text,
                    "entities": document.entities,
                    "analysis_results": document.analysis_results,
                    "metadata": document.metadata,
                    "confidence_score": document.confidence_score,
                    "processing_time": document.processing_time
                }
                
                return TextContent(
                    type="text",
                    text=json.dumps(content, indent=2)
                )
                
            except Document.DoesNotExist:
                return TextContent(
                    type="text",
                    text=json.dumps({"error": "Document not found"})
                )
        
        @self.server.resource()
        async def get_user_documents(user_id: str) -> TextContent:
            """Access all documents for a user"""
            try:
                user = User.objects.get(id=user_id)
                documents = Document.objects.filter(user=user)
                
                content = {
                    "user_id": user_id,
                    "username": user.username,
                    "documents": [
                        {
                            "id": str(doc.id),
                            "title": doc.title,
                            "status": doc.status,
                            "document_type": doc.document_type,
                            "uploaded_at": doc.uploaded_at.isoformat(),
                            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None
                        }
                        for doc in documents
                    ]
                }
                
                return TextContent(
                    type="text",
                    text=json.dumps(content, indent=2)
                )
                
            except User.DoesNotExist:
                return TextContent(
                    type="text",
                    text=json.dumps({"error": "User not found"})
                )
    
    def _calculate_relevance(self, document, query):
        """Calculate relevance score for search results"""
        query_lower = query.lower()
        title_match = query_lower in document.title.lower()
        text_match = query_lower in document.extracted_text.lower()
        
        score = 0
        if title_match:
            score += 10
        if text_match:
            score += 5
            
        # Add entity matching
        for entity in document.extracted_entities.all():
            if query_lower in entity.value.lower():
                score += 3
        
        return min(score, 100)  # Cap at 100

# Initialize server
mcp_server = DocumentAnalyzerMCPServer()

async def main():
    """Main entry point for MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.server.run(
            read_stream,
            write_stream,
            mcp_server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())