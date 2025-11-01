"""Script to upload AWS documentation to the retriever index."""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.retriever_client import RetrieverClient


def chunk_document(content: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Chunk document into smaller pieces while preserving context.
    
    Args:
        content: Full document content
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    
    # Split by paragraphs first
    paragraphs = content.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        # If adding this paragraph would exceed max size, save current chunk
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap (last N chars of previous chunk)
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def extract_metadata(content: str, filename: str) -> Dict[str, str]:
    """Extract metadata from document content.
    
    Args:
        content: Document content
        filename: Source filename
        
    Returns:
        Metadata dictionary
    """
    metadata = {
        "service": "sagemaker",
        "region": "us-east-1",
        "doc_type": "policy",
    }
    
    # Determine document type from filename
    if "security" in filename.lower():
        metadata["doc_type"] = "security"
        metadata["security_level"] = "high"
    elif "pricing" in filename.lower():
        metadata["doc_type"] = "pricing"
    elif "architecture" in filename.lower():
        metadata["doc_type"] = "architecture"
    elif "deployment" in filename.lower():
        metadata["doc_type"] = "deployment"
    
    # Extract service mentions
    if "s3" in content.lower():
        metadata["service"] = "s3"
    elif "iam" in content.lower() and "sagemaker" not in content.lower():
        metadata["service"] = "iam"
    elif "vpc" in content.lower():
        metadata["service"] = "vpc"
    
    return metadata


def upload_document_file(retriever: RetrieverClient, file_path: Path, base_url: str = None):
    """Upload a single document file to the retriever.
    
    Args:
        retriever: RetrieverClient instance
        file_path: Path to document file
        base_url: Base URL for document links
    """
    print(f"  Processing {file_path.name}...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract title from first line or filename
    lines = content.split("\n")
    title = lines[0].strip("# ").strip() if lines and lines[0].startswith("#") else file_path.stem.replace("_", " ").title()
    
    # Extract metadata
    metadata = extract_metadata(content, file_path.name)
    
    # Chunk the document
    chunks = chunk_document(content, max_chunk_size=1000, overlap=200)
    
    print(f"    Chunked into {len(chunks)} pieces")
    
    # Add each chunk as a separate document
    for i, chunk in enumerate(chunks):
        chunk_title = f"{title} - Section {i+1}" if len(chunks) > 1 else title
        url = f"{base_url}#section-{i+1}" if base_url and len(chunks) > 1 else base_url
        
        retriever.add_document(
            title=chunk_title,
            content=chunk,
            url=url,
            metadata=metadata
        )
    
    return len(chunks)


def main():
    """Upload all AWS documentation to retriever."""
    print("Initializing retriever client...")
    retriever = RetrieverClient()
    
    # Get demo_data directory
    demo_data_dir = Path(__file__).parent.parent / "orchestrator" / "demo_data"
    
    if not demo_data_dir.exists():
        print(f"Error: Demo data directory not found at {demo_data_dir}")
        sys.exit(1)
    
    # List of document files to upload
    doc_files = [
        "sample_policy.md",
        "aws_security_policies.md",
        "aws_pricing_catalog.md",
        "aws_architecture_frameworks.md",
        "aws_model_deployment_guides.md"
    ]
    
    total_chunks = 0
    
    print(f"\nUploading AWS documentation from {demo_data_dir}...")
    print("=" * 60)
    
    for doc_file in doc_files:
        doc_path = demo_data_dir / doc_file
        
        if not doc_path.exists():
            print(f"  ⚠️  Skipping {doc_file} (not found)")
            continue
        
        chunks = upload_document_file(
            retriever,
            doc_path,
            base_url=f"file://{doc_file}"
        )
        total_chunks += chunks
    
    print("=" * 60)
    print(f"\n✅ Successfully uploaded {total_chunks} document chunks from {len([f for f in doc_files if (demo_data_dir / f).exists()])} files")
    print("\nAWS documentation is now available for RAG retrieval.")
    print("The retriever will use these documents to ground deployment plans with:")
    print("  - Security best practices")
    print("  - Pricing information and cost optimization")
    print("  - Architecture patterns")
    print("  - Deployment guidelines")


if __name__ == "__main__":
    main()

