"""
Vector Search Service for Freight Payment AI Assistant
Enhanced version of the original search functionality with caching and error handling
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import voyageai
from cachetools import TTLCache
import hashlib
import json

from config import Settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Enhanced vector search service with caching and error handling"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.db = None
        self.collection = None
        self.voyage_client = None
        self.cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl)
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize MongoDB and VoyageAI connections"""
        try:
            # Initialize MongoDB connection
            self.client = MongoClient(self.settings.mongodb_uri)
            self.db = self.client[self.settings.mongodb_database]
            self.collection = self.db[self.settings.mongodb_collection]
            
            # Initialize VoyageAI client
            if self.settings.voyage_api_key:
                self.voyage_client = voyageai.Client(api_key=self.settings.voyage_api_key)
            else:
                logger.warning("VoyageAI API key not provided. Vector search will be limited.")
            
            logger.info("Vector search service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector search service: {str(e)}")
            raise
    
    def _generate_cache_key(self, query: str, limit: int) -> str:
        """Generate cache key for query"""
        key_data = {
            "query": query,
            "limit": limit,
            "model": self.settings.voyage_model
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using VoyageAI"""
        if not self.voyage_client:
            raise ValueError("VoyageAI client not initialized")
        
        try:
            result = await asyncio.to_thread(
                self.voyage_client.embed,
                texts=[text],
                model=self.settings.voyage_model,
                input_type="query"
            )
            return result.embeddings[0]
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    async def search(self, query: str, limit: int = None) -> List[Dict[str, Any]]:
        """Search for similar documents using vector search"""
        if limit is None:
            limit = self.settings.default_search_limit
        
        # Check cache first
        cache_key = self._generate_cache_key(query, limit)
        if cache_key in self.cache:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return self.cache[cache_key]
        
        try:
            # Generate query embedding
            query_vector = await self._generate_embedding(query)
            
            # Build aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.settings.vector_index_name,
                        "path": "Reason_Embedded",
                        "queryVector": query_vector,
                        "numCandidates": self.settings.vector_search_candidates,
                        "limit": min(limit, self.settings.max_search_limit)
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "score": {"$meta": "vectorSearchScore"},
                        "reason": "$event.eventData.subTypeData.reason",
                        "event_type": "$event.eventType",
                        "timestamp": "$event.timestamp",
                        "metadata": {
                            "carrier": "$event.eventData.carrier",
                            "status": "$event.eventData.status",
                            "transaction_id": "$event.eventData.transactionId"
                        }
                    }
                }
            ]
            
            # Execute search
            start_time = datetime.utcnow()
            results = list(self.collection.aggregate(pipeline))
            end_time = datetime.utcnow()
            
            # Log performance
            execution_time = (end_time - start_time).total_seconds()
            logger.info(f"Vector search completed in {execution_time:.3f}s, found {len(results)} results")
            
            # Cache results
            self.cache[cache_key] = results
            
            return results
            
        except PyMongoError as e:
            logger.error(f"MongoDB error during search: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise
    
    async def find_similar_by_id(self, document_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find documents similar to a specific document by ID"""
        try:
            # Get the original document
            document = self.collection.find_one({"_id": document_id})
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
            
            # Extract reason for similarity search
            reason = document.get("event", {}).get("eventData", {}).get("subTypeData", {}).get("reason", "")
            if not reason:
                raise ValueError(f"No reason found in document {document_id}")
            
            # Search for similar documents
            results = await self.search(reason, limit + 1)  # +1 to exclude the original document
            
            # Filter out the original document
            filtered_results = [r for r in results if str(r.get("_id")) != document_id]
            
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar documents for {document_id}: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection"""
        try:
            total_docs = self.collection.count_documents({})
            embedded_docs = self.collection.count_documents({"Reason_Embedded": {"$exists": True}})
            
            # Get sample of reasons for analysis
            pipeline = [
                {"$match": {"event.eventData.subTypeData.reason": {"$exists": True}}},
                {"$group": {
                    "_id": "$event.eventData.subTypeData.reason",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 20}
            ]
            
            top_reasons = list(self.collection.aggregate(pipeline))
            
            return {
                "total_documents": total_docs,
                "embedded_documents": embedded_docs,
                "embedding_percentage": round((embedded_docs / total_docs) * 100, 2) if total_docs > 0 else 0,
                "top_reasons": [
                    {"reason": item["_id"], "count": item["count"]} 
                    for item in top_reasons
                ],
                "cache_size": len(self.cache),
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            raise
    
    def close(self):
        """Close connections"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")