import asyncio
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from django.contrib.auth.models import User
from apps.documents.models import Document, ProcessingLog
from .agents import DocumentAnalysisAgents
from .langchain_utils import DocumentIntelligenceChain

class DocumentProcessingState(TypedDict):
    """State for document processing pipeline"""
    document_id: str
    user_id: str
    file_path: str
    current_step: str
    status: str
    progress: float
    extracted_text: str = ""
    raw_text: str = ""
    entities: Dict[str, Any] = {}
    document_type: str = ""
    confidence_score: float = 0.0
    analysis_results: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    error_message: str = ""
    processing_time: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0

class DocumentProcessingGraph:
    """LangGraph orchestration for document processing"""
    
    def __init__(self):
        self.agents = DocumentAnalysisAgents()
        self.langchain_utils = DocumentIntelligenceChain()
        self.graph = self._create_graph()
        self.checkpointer = MemorySaver()
    
    def _create_graph(self) -> StateGraph:
        """Create the document processing graph"""
        
        # Initialize graph with state
        workflow = StateGraph(DocumentProcessingState)
        
        # Add nodes
        workflow.add_node("input_processing", self._process_input)
        workflow.add_node("document_classification", self._classify_document)
        workflow.add_node("ocr_processing", self._process_ocr)
        workflow.add_node("text_extraction", self._extract_text)
        workflow.add_node("entity_extraction", self._extract_entities)
        workflow.add_node("analysis", self._analyze_document)
        workflow.add_node("validation", self._validate_results)
        workflow.add_node("completion", self._complete_processing)
        
        # Add edges (workflow)
        workflow.set_entry_point("input_processing")
        workflow.add_edge("input_processing", "document_classification")
        workflow.add_edge("document_classification", "ocr_processing")
        workflow.add_edge("ocr_processing", "text_extraction")
        workflow.add_edge("text_extraction", "entity_extraction")
        workflow.add_edge("entity_extraction", "analysis")
        workflow.add_edge("analysis", "validation")
        workflow.add_edge("validation", "completion")
        workflow.add_edge("completion", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "input_processing",
            self._check_input_result,
            {
                "success": "document_classification",
                "error": "completion"
            }
        )
        
        workflow.add_conditional_edges(
            "ocr_processing",
            self._check_ocr_result,
            {
                "success": "text_extraction",
                "retry": "ocr_processing",
                "error": "completion"
            }
        )
        
        workflow.add_conditional_edges(
            "analysis",
            self._check_analysis_result,
            {
                "success": "validation",
                "error": "completion"
            }
        )
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def process_document(self, document_id: str) -> Dict[str, Any]:
        """Process document through the graph"""
        
        try:
            # Get document
            document = Document.objects.get(id=document_id)
            
            # Initialize state
            initial_state = DocumentProcessingState(
                document_id=document_id,
                user_id=str(document.user.id),
                file_path=document.file.path,
                current_step="input_processing",
                status="processing",
                progress=0.0,
                start_time=datetime.now()
            )
            
            # Update document status
            document.status = 'processing'
            document.save()
            
            # Log start
            await self._log_processing_step(
                document_id, "input_processing", "started", 
                "Document processing started"
            )
            
            # Execute graph
            config = {"configurable": {"thread_id": f"doc_{document_id}"}}
            result = await self.graph.ainvoke(initial_state, config=config)
            
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - result.get('start_time', end_time)).total_seconds()
            
            return {
                "document_id": document_id,
                "status": "completed",
                "processing_time": processing_time,
                "entities": result.get('entities', {}),
                "analysis_results": result.get('analysis_results', {}),
                "confidence_score": result.get('confidence_score', 0.0),
                "document_type": result.get('document_type', ''),
                "extracted_text": result.get('extracted_text', ''),
                "metadata": result.get('metadata', {})
            }
            
        except Exception as e:
            # Log error
            await self._log_processing_step(
                document_id, "error", "failed", 
                f"Processing failed: {str(e)}"
            )
            
            # Update document status
            document.status = 'failed'
            document.error_message = str(e)
            document.save()
            
            raise
    
    # Node implementations
    async def _process_input(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Process document input and validation"""
        try:
            await self._log_processing_step(
                state['document_id'], "input_processing", "started", 
                "Processing document input"
            )
            
            # Validate file exists and is accessible
            import os
            if not os.path.exists(state['file_path']):
                raise FileNotFoundError(f"File not found: {state['file_path']}")
            
            # Update state
            state['current_step'] = 'input_processing'
            state['progress'] = 5.0
            state['status'] = 'processing'
            
            await self._log_processing_step(
                state['document_id'], "input_processing", "completed", 
                "Input processing completed"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _classify_document(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Classify document type"""
        try:
            await self._log_processing_step(
                state['document_id'], "document_classification", "started", 
                "Classifying document type"
            )
            
            # Use classification agent
            classification_result = await self.agents.classification_agent.classify(
                state['file_path']
            )
            
            # Update state
            state['document_type'] = classification_result['type']
            state['metadata']['classification'] = classification_result
            state['current_step'] = 'document_classification'
            state['progress'] = 15.0
            
            await self._log_processing_step(
                state['document_id'], "document_classification", "completed", 
                f"Document classified as: {classification_result['type']}"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _process_ocr(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Process OCR on document"""
        try:
            await self._log_processing_step(
                state['document_id'], "ocr_processing", "started", 
                "Processing OCR"
            )
            
            # Use OCR agent
            ocr_result = await self.agents.ocr_agent.process(
                state['file_path'],
                document_type=state['document_type']
            )
            
            # Update state
            state['raw_text'] = ocr_result['text']
            state['metadata']['ocr'] = ocr_result['metadata']
            state['current_step'] = 'ocr_processing'
            state['progress'] = 30.0
            
            await self._log_processing_step(
                state['document_id'], "ocr_processing", "completed", 
                f"OCR completed with confidence: {ocr_result['confidence']}"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _extract_text(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Extract and clean text from OCR results"""
        try:
            await self._log_processing_step(
                state['document_id'], "text_extraction", "started", 
                "Extracting and cleaning text"
            )
            
            # Use LangChain for text processing
            cleaned_text = await self.langchain_utils.clean_and_structure_text(
                state['raw_text'],
                document_type=state['document_type']
            )
            
            # Update state
            state['extracted_text'] = cleaned_text['text']
            state['metadata']['text_processing'] = cleaned_text['metadata']
            state['current_step'] = 'text_extraction'
            state['progress'] = 45.0
            
            await self._log_processing_step(
                state['document_id'], "text_extraction", "completed", 
                "Text extraction completed"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _extract_entities(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Extract entities from text"""
        try:
            await self._log_processing_step(
                state['document_id'], "entity_extraction", "started", 
                "Extracting entities"
            )
            
            # Use entity extraction agent
            entities_result = await self.agents.entity_extraction_agent.extract(
                state['extracted_text'],
                document_type=state['document_type']
            )
            
            # Update state
            state['entities'] = entities_result['entities']
            state['metadata']['entity_extraction'] = entities_result['metadata']
            state['current_step'] = 'entity_extraction'
            state['progress'] = 60.0
            
            await self._log_processing_step(
                state['document_id'], "entity_extraction", "completed", 
                f"Extracted {len(entities_result['entities'])} entities"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _analyze_document(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Analyze document with business rules"""
        try:
            await self._log_processing_step(
                state['document_id'], "analysis", "started", 
                "Analyzing document"
            )
            
            # Use analysis agent
            analysis_result = await self.agents.analysis_agent.analyze(
                state['entities'],
                state['document_type'],
                text=state['extracted_text']
            )
            
            # Update state
            state['analysis_results'] = analysis_result['analysis']
            state['metadata']['analysis'] = analysis_result['metadata']
            state['confidence_score'] = analysis_result['confidence']
            state['current_step'] = 'analysis'
            state['progress'] = 80.0
            
            await self._log_processing_step(
                state['document_id'], "analysis", "completed", 
                "Document analysis completed"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _validate_results(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Validate processing results"""
        try:
            await self._log_processing_step(
                state['document_id'], "validation", "started", 
                "Validating results"
            )
            
            # Validation logic
            validation_result = await self._validate_processing_results(state)
            
            # Update state
            state['metadata']['validation'] = validation_result
            state['current_step'] = 'validation'
            state['progress'] = 90.0
            
            await self._log_processing_step(
                state['document_id'], "validation", "completed", 
                f"Validation completed: {validation_result['status']}"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    async def _complete_processing(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Complete document processing"""
        try:
            await self._log_processing_step(
                state['document_id'], "completion", "started", 
                "Completing processing"
            )
            
            # Update document in database
            document = Document.objects.get(id=state['document_id'])
            document.status = 'completed'
            document.extracted_text = state['extracted_text']
            document.entities = state['entities']
            document.analysis_results = state['analysis_results']
            document.confidence_score = state['confidence_score']
            document.document_type = state['document_type']
            document.metadata = state['metadata']
            document.processed_at = datetime.now()
            document.save()
            
            # Update state
            state['current_step'] = 'completion'
            state['progress'] = 100.0
            state['status'] = 'completed'
            state['end_time'] = datetime.now()
            
            await self._log_processing_step(
                state['document_id'], "completion", "completed", 
                "Document processing completed successfully"
            )
            
            return state
            
        except Exception as e:
            state['error_message'] = str(e)
            state['status'] = 'error'
            return state
    
    # Conditional edge functions
    def _check_input_result(self, state: DocumentProcessingState) -> str:
        """Check if input processing was successful"""
        return "success" if not state.get('error_message') else "error"
    
    def _check_ocr_result(self, state: DocumentProcessingState) -> str:
        """Check OCR result and decide next action"""
        if state.get('error_message'):
            return "error"
        
        # Check OCR quality
        ocr_confidence = state.get('metadata', {}).get('ocr', {}).get('confidence', 0)
        if ocr_confidence < 0.7 and state['retry_count'] < 3:
            state['retry_count'] += 1
            return "retry"
        
        return "success"
    
    def _check_analysis_result(self, state: DocumentProcessingState) -> str:
        """Check analysis result"""
        return "success" if not state.get('error_message') else "error"
    
    async def _validate_processing_results(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Validate all processing results"""
        validation_score = 0
        issues = []
        
        # Validate extracted text
        if len(state['extracted_text']) < 10:
            issues.append("Extracted text too short")
        else:
            validation_score += 25
        
        # Validate entities
        if state['entities']:
            validation_score += 35
        else:
            issues.append("No entities extracted")
        
        # Validate analysis
        if state['analysis_results']:
            validation_score += 40
        else:
            issues.append("No analysis results")
        
        return {
            "status": "passed" if validation_score >= 70 else "failed",
            "score": validation_score,
            "issues": issues
        }
    
    async def _log_processing_step(self, document_id: str, step: str, status: str, message: str):
        """Log processing step to database"""
        try:
            ProcessingLog.objects.create(
                document_id=document_id,
                step=step,
                status=status,
                message=message
            )
        except Exception as e:
            print(f"Failed to log processing step: {e}")
    
    def get_processing_progress(self, document_id: str) -> Dict[str, Any]:
        """Get current processing progress"""
        try:
            document = Document.objects.get(id=document_id)
            latest_log = document.processing_logs.last()
            
            return {
                "document_id": document_id,
                "status": document.status,
                "progress": getattr(document, 'processing_progress', 0),
                "current_step": getattr(document, 'current_step', ''),
                "estimated_time": getattr(document, 'estimated_time', 0),
                "latest_log": {
                    "step": latest_log.step,
                    "status": latest_log.status,
                    "message": latest_log.message
                } if latest_log else None
            }
        except Document.DoesNotExist:
            return {"error": "Document not found"}