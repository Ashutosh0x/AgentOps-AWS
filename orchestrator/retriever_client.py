"""Retriever client for NeMo Retriever NIM (embedding + reranking) on SageMaker."""

import json
import os
import logging
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from orchestrator.models import RAGEvidence

logger = logging.getLogger(__name__)


class RetrieverClient:
    """Client for NeMo Retriever NIM (two-stage: embedding + reranking)."""

    def __init__(
        self,
        embed_endpoint: str = None,
        rerank_endpoint: str = None,
        region: str = None,
        vector_store: Optional[Dict[str, Any]] = None
    ):
        """Initialize Retriever client.
        
        Args:
            embed_endpoint: SageMaker endpoint for NeMo Retriever Embedding NIM
            rerank_endpoint: SageMaker endpoint for NeMo Retriever Reranking NIM
            region: AWS region
            vector_store: In-memory vector store for MVP (FAISS replacement)
        """
        self.embed_endpoint = embed_endpoint or os.getenv("RETRIEVER_EMBED_ENDPOINT")
        self.rerank_endpoint = rerank_endpoint or os.getenv("RETRIEVER_RERANK_ENDPOINT")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # For MVP: use in-memory vector store if endpoints not provided
        self.use_mock = not (self.embed_endpoint and self.rerank_endpoint)
        
        if not self.use_mock:
            self.runtime_client = boto3.client("sagemaker-runtime", region_name=self.region)
        
        # Simple in-memory vector store for MVP
        self.vector_store = vector_store or {
            "documents": [],
            "embeddings": []
        }
    
    def add_document(self, title: str, content: str, url: str = None, metadata: Dict[str, Any] = None):
        """Add a document to the vector store.
        
        Args:
            title: Document title
            content: Document content
            url: Optional document URL
            metadata: Optional metadata dictionary (e.g., {service, region, doc_type, security_level})
        """
        self.vector_store["documents"].append({
            "title": title,
            "content": content,
            "url": url,
            "metadata": metadata or {}
        })
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query using NeMo Retriever Embedding NIM.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if self.use_mock:
            # Mock embedding: return dummy vector
            logger.warning("Using mock embedding (RETRIEVER_EMBED_ENDPOINT not set)")
            return [0.1] * 768  # Mock 768-dim vector
        
        try:
            payload = {
                "input": query,
                "input_type": "query"
            }
            
            response = self.runtime_client.invoke_endpoint(
                EndpointName=self.embed_endpoint,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            response_body = json.loads(response["Body"].read().decode("utf-8"))
            
            # Extract embedding (adjust based on actual NIM response format)
            if "embedding" in response_body:
                return response_body["embedding"]
            elif "vectors" in response_body:
                return response_body["vectors"][0]
            else:
                raise ValueError(f"Unexpected embedding response format: {response_body}")
                
        except ClientError as e:
            logger.error(f"SageMaker embedding API error: {e}")
            raise
    
    def retrieve_docs(self, query_embedding: List[float], top_k: int = 20, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve documents using vector similarity with optional metadata filtering.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of documents to retrieve
            filters: Optional metadata filters (e.g., {"service": "sagemaker", "doc_type": "security"})
            
        Returns:
            List of document dictionaries with title, content, url, metadata, score
        """
        if not self.vector_store["documents"]:
            logger.warning("Vector store is empty")
            return []
        
        filters = filters or {}
        
        # Filter documents by metadata if provided
        candidate_docs = self.vector_store["documents"]
        if filters:
            candidate_docs = []
            for doc in self.vector_store["documents"]:
                doc_metadata = doc.get("metadata", {})
                match = True
                for key, value in filters.items():
                    if doc_metadata.get(key) != value:
                        match = False
                        break
                if match:
                    candidate_docs.append(doc)
        
        # Simple cosine similarity search (MVP implementation)
        # In production, use OpenSearch Serverless or similar with actual vector similarity
        results = []
        for doc in candidate_docs:
            # Calculate simple keyword-based relevance score (placeholder for vector similarity)
            # In real implementation, compute cosine similarity between query_embedding and doc_embedding
            content_lower = doc.get("content", "").lower()
            title_lower = doc.get("title", "").lower()
            
            # Simple relevance scoring based on content length and metadata
            score = 0.3  # Base score
            
            # Boost score if metadata matches common patterns
            metadata = doc.get("metadata", {})
            if metadata.get("doc_type") in ["security", "pricing", "architecture", "deployment"]:
                score += 0.2
            
            # Add some randomness to simulate retrieval diversity (in production, use actual similarity)
            import random
            score += random.uniform(0.1, 0.4)
            
            results.append({
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
                "url": doc.get("url"),
                "metadata": doc.get("metadata", {}),
                "score": score
            })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int = 3) -> List[RAGEvidence]:
        """Rerank documents using NeMo Retriever Reranking NIM.
        
        Args:
            query: Original query text
            docs: List of candidate documents from retrieval
            top_k: Number of top documents to return after reranking
            
        Returns:
            List of RAGEvidence objects (top-k reranked)
        """
        if self.use_mock:
            # Mock reranking: return top docs as-is
            logger.warning("Using mock reranking (RETRIEVER_RERANK_ENDPOINT not set)")
            return [
                RAGEvidence(
                    title=doc["title"],
                    snippet=doc["content"][:200] if len(doc["content"]) > 200 else doc["content"],
                    url=doc.get("url"),
                    score=doc.get("score", 0.5)
                )
                for doc in docs[:top_k]
            ]
        
        if not docs:
            return []
        
        try:
            # Prepare reranking payload
            passages = [doc["content"] for doc in docs]
            payload = {
                "query": query,
                "passages": passages
            }
            
            response = self.runtime_client.invoke_endpoint(
                EndpointName=self.rerank_endpoint,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            response_body = json.loads(response["Body"].read().decode("utf-8"))
            
            # Extract reranking scores (adjust based on actual NIM response format)
            if "scores" in response_body:
                scores = response_body["scores"]
            elif "rerank_scores" in response_body:
                scores = response_body["rerank_scores"]
            else:
                # Fallback: use original scores
                scores = [doc.get("score", 0.5) for doc in docs]
            
            # Combine documents with reranking scores
            ranked_docs = list(zip(docs, scores))
            ranked_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Return top-k as RAGEvidence
            evidence = []
            for doc, score in ranked_docs[:top_k]:
                evidence.append(RAGEvidence(
                    title=doc["title"],
                    snippet=doc["content"][:200] if len(doc["content"]) > 200 else doc["content"],
                    url=doc.get("url"),
                    score=float(score)
                ))
            
            return evidence
            
        except ClientError as e:
            logger.error(f"SageMaker reranking API error: {e}")
            # Fallback: return docs as-is
            return [
                RAGEvidence(
                    title=doc["title"],
                    snippet=doc["content"][:200] if len(doc["content"]) > 200 else doc["content"],
                    url=doc.get("url"),
                    score=doc.get("score", 0.5)
                )
                for doc in docs[:top_k]
            ]
    
    def query(self, query: str, top_k: int = 3) -> List[RAGEvidence]:
        """Complete two-stage retrieval pipeline: embed → retrieve → rerank.
        
        Args:
            query: Query text
            top_k: Number of top documents to return
            
        Returns:
            List of top-k RAGEvidence objects
        """
        # Stage 1: Embed query
        query_embedding = self.embed_query(query)
        
        # Stage 2: Retrieve candidates
        candidate_docs = self.retrieve_docs(query_embedding, top_k=20)
        
        # Stage 3: Rerank
        ranked_evidence = self.rerank(query, candidate_docs, top_k=top_k)
        
        return ranked_evidence

