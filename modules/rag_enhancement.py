"""
RAG Enhancement Module
Handles RAG corpus queries and context enhancement
"""

import os
import asyncio
import threading
from typing import Dict, Any
from vertexai.preview import rag


# 🚀 PERFORMANCE CACHE: Global cache for RAG tools
_rag_tool_cache = {}
_rag_tool_lock = threading.Lock()


def get_cached_rag_tool(project_id: str, rag_corpus_name: str, rag_location: str):
    """
    Get cached RAG tool or create new one with thread safety
    """
    cache_key = f"{project_id}_{rag_corpus_name}_{rag_location}"

    with _rag_tool_lock:
        if cache_key in _rag_tool_cache:
            print(f"🔄 Using cached RAG tool for {cache_key}")
            return _rag_tool_cache[cache_key]

        try:
            print(f"🆕 Creating new RAG tool for {cache_key}")
            # Try multiple methods in order of preference
            rag_tool = None

            # Method 1: Try rag.Tool (newer API)
            if hasattr(rag, 'Tool'):
                try:
                    rag_tool = rag.Tool(
                        retrieval=rag.Retrieval(
                            source=rag.VertexRagStore(
                                rag_corpora=[rag_corpus_name]
                            )
                        )
                    )
                    print(f"✅ Created RAG tool using rag.Tool API")
                except Exception as e:
                    print(f"⚠️  rag.Tool failed: {str(e)}")

            # Method 2: Try rag.Retrieval.from_corpus (older API)
            if not rag_tool and hasattr(rag, 'Retrieval'):
                try:
                    if hasattr(rag.Retrieval, 'from_corpus'):
                        rag_tool = rag.Retrieval.from_corpus(
                            rag_corpus_name=rag_corpus_name,
                            project_id=project_id,
                            location=rag_location
                        )
                        print(f"✅ Created RAG tool using rag.Retrieval.from_corpus API")
                except Exception as e:
                    print(f"⚠️  rag.Retrieval.from_corpus failed: {str(e)}")

            if rag_tool:
                _rag_tool_cache[cache_key] = rag_tool
                return rag_tool
            else:
                print(f"❌ All RAG tool creation methods failed")
                return None

        except Exception as e:
            print(f"❌ Failed to create RAG tool: {str(e)}")
            return None


async def process_chunk_with_rag(chunk: dict, rag_tool, doc_counter: int) -> dict:
    """
    Process a single chunk with RAG tool using async concurrency
    """
    try:
        chunk_text = chunk.get("masked_text", chunk.get("text", ""))
        if not chunk_text.strip():
            return {
                "chunk_id": chunk.get("chunk_id"),
                "text": chunk_text,
                "requirement_entities": chunk.get("requirement_entities", []),
                "compliance_entities": chunk.get("compliance_entities", []),
                "matched_policies": [],
                "bounding_box": chunk.get("bounding_box", {}),
                "source_type": "prd_document",
                "pii_found": chunk.get("pii_found", False),
                "pii_types": chunk.get("pii_types", []),
                "rag_response": "No text to process"
            }

        # Dynamic thresholding based on chunk length
        threshold = 0.6 if len(chunk_text) < 500 else 0.75
        
        # Query RAG tool asynchronously to avoid blocking
        rag_response = await asyncio.to_thread(
            rag_tool.query,
            text=chunk_text,
            similarity_threshold=threshold,
            max_results=3
        )

        # Extract matched policies from RAG response
        matched_policies = []
        if hasattr(rag_response, 'contexts') and rag_response.contexts:
            for context in rag_response.contexts:
                if hasattr(context, 'text') and context.text:
                    matched_policies.append({
                        "policy_name": getattr(context, 'title', 'Unknown Policy'),
                        "policy_text": context.text[:200] + "..." if len(context.text) > 200 else context.text,
                        "similarity_score": getattr(context, 'similarity_score', 0.0),
                        "source": "rag_corpus"
                    })

        return {
            "chunk_id": chunk.get("chunk_id"),
            "text": chunk_text,
            "requirement_entities": chunk.get("requirement_entities", []),
            "compliance_entities": chunk.get("compliance_entities", []),
            "matched_policies": matched_policies,
            "bounding_box": chunk.get("bounding_box", {}),
            "source_type": "prd_document",
            "pii_found": chunk.get("pii_found", False),
            "pii_types": chunk.get("pii_types", []),
            "rag_response": rag_response
        }

    except Exception as e:
        print(f"⚠️  RAG processing error for chunk {chunk.get('chunk_id', 'unknown')}: {str(e)}")
        return {
            "chunk_id": chunk.get("chunk_id"),
            "text": chunk.get("masked_text", chunk.get("text", "")),
            "requirement_entities": chunk.get("requirement_entities", []),
            "compliance_entities": chunk.get("compliance_entities", []),
            "matched_policies": [],
            "bounding_box": chunk.get("bounding_box", {}),
            "source_type": "prd_document",
            "pii_found": chunk.get("pii_found", False),
            "pii_types": chunk.get("pii_types", []),
            "rag_response": f"Error: {str(e)}"
        }


async def query_rag_from_chunks(dlp_output: dict, project_id: str, rag_corpus_name: str = None, rag_location: str = "europe-west3") -> dict:
    """
    Query RAG corpus from DLP-masked chunks for enhanced compliance insights
    """
    try:
        if not rag_corpus_name:
            rag_corpus_name = os.getenv("RAG_CORPUS_NAME", "projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856")
        
        print(f"🔍 Querying RAG corpus: {rag_corpus_name}")
        
        # Get cached RAG tool
        rag_tool = get_cached_rag_tool(project_id, rag_corpus_name, rag_location)
        if not rag_tool:
            print("⚠️  RAG tool creation failed, using fallback keyword matching")
            return await fallback_rag_processing(dlp_output)
        
        # Get chunks from DLP output (unified structure)
        chunks = dlp_output.get("chunks", [])
        if not chunks:
            return {
                "status": "error",
                "agent": "Healthcare-RAG",
                "error": "No chunks available for RAG processing",
                "chunks": [],  # Include empty chunks for KG builder
                "context_docs": []
            }

        # Process chunks with RAG concurrently for better performance
        tasks = [process_chunk_with_rag(chunk, rag_tool, i) for i, chunk in enumerate(chunks)]
        context_docs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions from concurrent processing
        processed_docs = []
        for i, result in enumerate(context_docs):
            if isinstance(result, Exception):
                print(f"⚠️  RAG chunk processing error for chunk {i}: {str(result)}")
                # Create a fallback result for failed chunks
                chunk = chunks[i]
                processed_docs.append({
                    "chunk_id": chunk.get("chunk_id"),
                    "text": chunk.get("masked_text", chunk.get("text", "")),
                    "requirement_entities": chunk.get("requirement_entities", []),
                    "compliance_entities": chunk.get("compliance_entities", []),
                    "matched_policies": [],
                    "bounding_box": chunk.get("bounding_box", {}),
                    "source_type": "prd_document",
                    "pii_found": chunk.get("pii_found", False),
                    "pii_types": chunk.get("pii_types", []),
                    "rag_response": f"Error: {str(result)}"
                })
            else:
                processed_docs.append(result)
        
        context_docs = processed_docs

        # Calculate statistics
        total_policies = sum(len(doc.get("matched_policies", [])) for doc in context_docs)
        chunks_with_policies = len([doc for doc in context_docs if doc.get("matched_policies")])

        return {
            "status": "success",
            "agent": "Healthcare-RAG",
            "chunks": chunks,  # Include chunks for KG builder
            "context_docs": context_docs,
            "metadata": {
                "total_chunks_processed": len(context_docs),
                "total_policies_matched": total_policies,
                "chunks_with_policies": chunks_with_policies,
                "rag_corpus_used": rag_corpus_name,
                "rag_location": rag_location
            }
        }
        
    except Exception as e:
        print(f"❌ RAG processing error: {str(e)}")
        chunks = dlp_output.get("chunks", [])
        return {
            "status": "error",
            "agent": "Healthcare-RAG",
            "error": str(e),
            "chunks": chunks,  # Include chunks even on error for KG builder
            "context_docs": []
        }


async def fallback_rag_processing(dlp_output: dict) -> dict:
    """
    Fallback RAG processing using fuzzy matching when RAG corpus is unavailable

    Uses difflib.SequenceMatcher for intelligent fuzzy matching (ratio > 0.7)
    Deduplicates matched policies per chunk
    Returns same schema as main RAG for uniform UI parsing
    """
    from difflib import SequenceMatcher

    print("🔄 Using fallback fuzzy-match RAG processing")

    # Compact policy database with searchable text
    POLICY_DATABASE = [
        {
            "policy_name": "HIPAA Privacy Rule",
            "policy_text": "Protect patient health information with access controls, audit trails, and encryption",
            "keywords": ["patient", "health", "protected information", "access control", "audit", "encryption"]
        },
        {
            "policy_name": "GDPR Data Protection",
            "policy_text": "EU data subject rights including consent, data minimization, erasure, and portability",
            "keywords": ["data protection", "consent", "privacy", "erasure", "portability", "gdpr"]
        },
        {
            "policy_name": "FDA 21 CFR Part 11",
            "policy_text": "Electronic records and signatures with audit trails and data integrity controls",
            "keywords": ["electronic signature", "audit trail", "data integrity", "fda", "validation"]
        },
        {
            "policy_name": "SOC2 Type II",
            "policy_text": "Security, availability, processing integrity, confidentiality, and privacy controls",
            "keywords": ["security", "availability", "confidentiality", "soc2", "controls"]
        },
        {
            "policy_name": "ISO 27001",
            "policy_text": "Information security management with risk assessment and continuous improvement",
            "keywords": ["information security", "risk management", "iso", "security controls"]
        }
    ]

    # Get chunks from DLP output (unified structure)
    chunks = dlp_output.get("chunks", [])
    context_docs = []

    for chunk in chunks:
        chunk_text = chunk.get("masked_text", chunk.get("text", "")).lower()
        matched_policies = {}  # Use dict for deduplication by policy_name

        # Fuzzy matching with difflib
        for policy in POLICY_DATABASE:
            max_similarity = 0.0

            # Check similarity against keywords
            for keyword in policy["keywords"]:
                similarity = SequenceMatcher(None, keyword.lower(), chunk_text).ratio()
                max_similarity = max(max_similarity, similarity)

            # Also check direct substring matches for exact keyword hits
            for keyword in policy["keywords"]:
                if keyword.lower() in chunk_text:
                    max_similarity = max(max_similarity, 0.9)  # High score for exact matches

            # Add policy if similarity exceeds threshold
            if max_similarity > 0.7:
                # Deduplicate: only keep highest score per policy
                if policy["policy_name"] not in matched_policies or matched_policies[policy["policy_name"]]["similarity_score"] < max_similarity:
                    matched_policies[policy["policy_name"]] = {
                        "policy_name": policy["policy_name"],
                        "policy_text": policy["policy_text"],
                        "similarity_score": round(max_similarity, 2),
                        "source": "fallback_fuzzy_matching"
                    }

        # Convert dict back to list, sorted by similarity score descending
        matched_policies_list = sorted(
            matched_policies.values(),
            key=lambda x: x["similarity_score"],
            reverse=True
        )

        context_docs.append({
            "chunk_id": chunk.get("chunk_id"),
            "text": chunk.get("masked_text", chunk.get("text", "")),
            "requirement_entities": chunk.get("requirement_entities", []),
            "compliance_entities": chunk.get("compliance_entities", []),
            "matched_policies": matched_policies_list,
            "bounding_box": chunk.get("bounding_box", {}),
            "source_type": "prd_document",
            "pii_found": chunk.get("pii_found", False),
            "pii_types": chunk.get("pii_types", []),
            "rag_response": "Fallback fuzzy matching used"
        })

    return {
        "status": "success",
        "agent": "Healthcare-RAG (Fallback)",
        "chunks": chunks,  # Include chunks for KG builder
        "context_docs": context_docs,
        "metadata": {
            "total_chunks_processed": len(context_docs),
            "total_policies_matched": sum(len(doc.get("matched_policies", [])) for doc in context_docs),
            "chunks_with_policies": len([doc for doc in context_docs if doc.get("matched_policies")]),
            "rag_corpus_used": "fallback_fuzzy_matching",
            "rag_location": "local"
        }
    }
