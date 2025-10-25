"""
DLP Masking Module
Handles PII detection and masking using Google DLP

Optimizations:
- Uses asyncio.to_thread() to avoid blocking on synchronous DLP API calls
- Merges original and masked text into unified chunks
- Adds per-chunk trace_links for traceability
- Simplified response structure
"""

import os
import asyncio
from typing import List, Dict, Any
from google.cloud import dlp_v2

# Suppress gRPC fork warnings (safe for our use case with asyncio.to_thread)
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '1'
os.environ['GRPC_POLL_STRATEGY'] = 'poll'

# Default DLP location (region). For content methods we use the global endpoint with a global parent.
DLP_DEFAULT_LOCATION = os.getenv("DLP_LOCATION", "us")


async def mask_chunks_with_dlp(docai_response: dict, project_id: str, gdpr_mode: bool = True, location: str = DLP_DEFAULT_LOCATION) -> dict:
    """
    Mask sensitive information in DocAI chunks using Google DLP API.
    
    Optimizations:
    - Returns unified chunks with both original_text and masked_text
    - Uses asyncio.to_thread() to prevent blocking
    - Adds per-chunk trace_links from edges
    - Simplified response structure

    Args:
        docai_response: Response from extract_traceable_docai() containing chunks and edges
        project_id: GCP project ID
        gdpr_mode: If True, performs PII masking. If False, returns original text as masked_text
        location: DLP API location (default: "us", NOT "global" - use regions like "us", "europe-west1", etc.)

    Returns:
        Dictionary with unified chunks containing both original and masked text
    """
    chunks = docai_response.get("chunks", [])
    edges = docai_response.get("edges", [])
    
    # If GDPR mode is disabled, return chunks with original text (no masking)
    if not gdpr_mode:
        print("🔓 GDPR mode disabled - skipping PII masking")
        
        # Merge fields directly into chunks (in-place update)
        compliance_standards = set()
        
        for chunk in chunks:
            chunk["masked_text"] = chunk.get("text", "")  # Same as original when GDPR is off
            chunk["pii_found"] = False
            chunk["pii_count"] = 0
            chunk["pii_types"] = []
            
            # Add original_text since gdpr_mode=False
            chunk["original_text"] = chunk.get("text", "")
            
            # Add embedding_ready_text for RAG processing
            chunk["embedding_ready_text"] = chunk["masked_text"].lower().replace("\n", " ").strip()

        # Post-processing: Merge edges and trace_links into relationships with unique IDs
        print(f"🔗 Creating relationships for improved traceability...")
        for chunk in chunks:
            chunk_page = chunk.get("page_number")
            chunk_id = chunk.get("chunk_id", "")

            # Add unique node_id for KG
            chunk["node_id"] = f"NODE_{chunk_id}"

            # Get trace_links from chunk (if exists)
            trace_links = chunk.get("trace_links", [])
            relationships = []

            # Build relationships from trace_links (preferred source)
            if trace_links:
                for edge in trace_links:
                    relationship = {
                        "edge_id": f"EDGE_{chunk_id}_{len(relationships) + 1:03d}",
                        "source_id": edge.get("source", ""),
                        "target_id": edge.get("target", ""),
                        "type": edge.get("relationship", "REQUIRES_COMPLIANCE"),
                        "target_class": (
                            "COMPLIANCE_STANDARD"
                            if "compliance" in edge.get("target_type", "").lower()
                            else edge.get("target_type", "UNKNOWN")
                        ),
                        "confidence": edge.get("confidence", 0.7),
                        "page": edge.get("page")
                    }
                    relationships.append(relationship)

                    # Collect compliance standards for summary
                    if relationship["target_class"] == "COMPLIANCE_STANDARD":
                        compliance_standards.add(relationship["target_id"])

            # Fallback: build from global edges if trace_links is empty
            elif chunk_page and edges:
                chunk_edges = [e for e in edges if e.get("page") == chunk_page]
                for edge in chunk_edges:
                    relationship = {
                        "edge_id": f"EDGE_{chunk_id}_{len(relationships) + 1:03d}",
                        "source_id": edge.get("source", ""),
                        "target_id": edge.get("target", ""),
                        "type": edge.get("relationship", "REQUIRES_COMPLIANCE"),
                        "target_class": edge.get("target_type", "UNKNOWN"),
                        "confidence": edge.get("confidence", 0.7),
                        "page": chunk_page
                    }
                    relationships.append(relationship)

                    # Collect compliance standards for summary
                    if relationship["target_class"] == "COMPLIANCE_STANDARD":
                        compliance_standards.add(relationship["target_id"])

            chunk["relationships"] = relationships

            # Remove trace_links after merging (redundant)
            if "trace_links" in chunk:
                del chunk["trace_links"]

            # Remove original_text if no PII found (reduce payload)
            if not chunk.get("pii_found", False) and "original_text" in chunk:
                del chunk["original_text"]

        # Calculate pipeline metrics for dashboarding
        summary_base = docai_response.get("summary", {})

        # Average confidence across all detected requirements
        all_requirements = [r for c in chunks for r in c.get("detected_requirements", [])]
        avg_confidence = round(
            sum(r.get("confidence", 0) for r in all_requirements) / max(1, len(all_requirements)),
            2
        ) if all_requirements else 0.0

        # Compliance density: ratio of compliance standards to requirements
        compliance_density = round(
            summary_base.get("compliance_standards_found", 0) / max(1, summary_base.get("requirements_found", 1)),
            2
        )

        # PII density: ratio of chunks with PII to total chunks
        pii_density = round(
            0 / max(1, summary_base.get("total_chunks", 1)),
            2
        )

        # Calculate derived summary metrics
        relationships_total = sum(len(c.get("relationships", [])) for c in chunks)
        unique_compliance_links = len(set(
            r["target_id"] for c in chunks for r in c.get("relationships", [])
            if r.get("target_class") == "COMPLIANCE_STANDARD"
        ))

        return {
            "chunks": chunks,  # Return the updated chunks directly
            "summary": {
                **summary_base,
                "pii_masking_performed": False,
                "chunks_with_pii": 0,
                "compliance_summary": list(compliance_standards),
                "avg_confidence": avg_confidence,
                "compliance_density": compliance_density,
                "pii_density": pii_density,
                "relationships_total": relationships_total,
                "unique_compliance_links": unique_compliance_links
            }
        }
    
    # GDPR mode enabled - perform PII masking
    try:
        print("🔒 GDPR mode enabled - performing PII masking with DLP...")
        
        # Process chunks with DLP (uses asyncio.to_thread to avoid blocking)
        masked_results = await process_chunks_with_dlp_async(chunks, project_id, location)
        
        # Merge DLP results directly into chunks (in-place update)
        total_pii_found = 0
        total_pii_types = set()
        chunks_with_pii = 0
        compliance_standards = set()
        
        for i, chunk in enumerate(chunks):
            masked_result = masked_results[i]
            
            # Keep only masked_text by default
            chunk["masked_text"] = masked_result.get("masked_text", chunk.get("text", ""))
            chunk["pii_found"] = masked_result.get("pii_found", False)
            chunk["pii_count"] = masked_result.get("pii_count", 0)
            chunk["pii_types"] = masked_result.get("pii_types", [])
            
            # Add original_text only if pii_found=True or gdpr_mode=False
            if masked_result.get("pii_found", False) or not gdpr_mode:
                chunk["original_text"] = chunk.get("text", "")
            
            # Add embedding_ready_text for RAG processing
            chunk["embedding_ready_text"] = chunk["masked_text"].lower().replace("\n", " ").strip()

            # Aggregate PII statistics
            if masked_result.get("pii_found", False):
                chunks_with_pii += 1
                total_pii_found += masked_result.get("pii_count", 0)
                total_pii_types.update(masked_result.get("pii_types", []))

        # Post-processing: Merge edges and trace_links into relationships with unique IDs
        print(f"🔗 Creating relationships for improved traceability...")
        for chunk in chunks:
            chunk_page = chunk.get("page_number")
            chunk_id = chunk.get("chunk_id", "")

            # Add unique node_id for KG
            chunk["node_id"] = f"NODE_{chunk_id}"

            # Get trace_links from chunk (if exists)
            trace_links = chunk.get("trace_links", [])
            relationships = []

            # Build relationships from trace_links (preferred source)
            if trace_links:
                for edge in trace_links:
                    relationship = {
                        "edge_id": f"EDGE_{chunk_id}_{len(relationships) + 1:03d}",
                        "source_id": edge.get("source", ""),
                        "target_id": edge.get("target", ""),
                        "type": edge.get("relationship", "REQUIRES_COMPLIANCE"),
                        "target_class": (
                            "COMPLIANCE_STANDARD"
                            if "compliance" in edge.get("target_type", "").lower()
                            else edge.get("target_type", "UNKNOWN")
                        ),
                        "confidence": edge.get("confidence", 0.7),
                        "page": edge.get("page")
                    }
                    relationships.append(relationship)

                    # Collect compliance standards for summary
                    if relationship["target_class"] == "COMPLIANCE_STANDARD":
                        compliance_standards.add(relationship["target_id"])

            # Fallback: build from global edges if trace_links is empty
            elif chunk_page and edges:
                chunk_edges = [e for e in edges if e.get("page") == chunk_page]
                for edge in chunk_edges:
                    relationship = {
                        "edge_id": f"EDGE_{chunk_id}_{len(relationships) + 1:03d}",
                        "source_id": edge.get("source", ""),
                        "target_id": edge.get("target", ""),
                        "type": edge.get("relationship", "REQUIRES_COMPLIANCE"),
                        "target_class": edge.get("target_type", "UNKNOWN"),
                        "confidence": edge.get("confidence", 0.7),
                        "page": chunk_page
                    }
                    relationships.append(relationship)

                    # Collect compliance standards for summary
                    if relationship["target_class"] == "COMPLIANCE_STANDARD":
                        compliance_standards.add(relationship["target_id"])

            chunk["relationships"] = relationships

            # Remove trace_links after merging (redundant)
            if "trace_links" in chunk:
                del chunk["trace_links"]

            # Remove original_text if no PII found (reduce payload)
            if not chunk.get("pii_found", False) and "original_text" in chunk:
                del chunk["original_text"]

        print(f"✅ DLP masking complete: {chunks_with_pii}/{len(chunks)} chunks with PII")

        # Calculate pipeline metrics for dashboarding
        summary_base = docai_response.get("summary", {})

        # Average confidence across all detected requirements
        all_requirements = [r for c in chunks for r in c.get("detected_requirements", [])]
        avg_confidence = round(
            sum(r.get("confidence", 0) for r in all_requirements) / max(1, len(all_requirements)),
            2
        ) if all_requirements else 0.0

        # Compliance density: ratio of compliance standards to requirements
        compliance_density = round(
            summary_base.get("compliance_standards_found", 0) / max(1, summary_base.get("requirements_found", 1)),
            2
        )

        # PII density: ratio of chunks with PII to total chunks
        pii_density = round(
            chunks_with_pii / max(1, summary_base.get("total_chunks", 1)),
            2
        )

        # Calculate derived summary metrics
        relationships_total = sum(len(c.get("relationships", [])) for c in chunks)
        unique_compliance_links = len(set(
            r["target_id"] for c in chunks for r in c.get("relationships", [])
            if r.get("target_class") == "COMPLIANCE_STANDARD"
        ))

        return {
            "chunks": chunks,  # Return the updated chunks directly
            "summary": {
                **summary_base,
                "pii_masking_performed": True,
                "chunks_with_pii": chunks_with_pii,
                "compliance_summary": list(compliance_standards),
                "avg_confidence": avg_confidence,
                "compliance_density": compliance_density,
                "pii_density": pii_density,
                "relationships_total": relationships_total,
                "unique_compliance_links": unique_compliance_links
            }
        }
    
    except Exception as e:
        print(f"❌ DLP masking error: {str(e)}")
        # On error, add error fields directly to chunks
        compliance_standards = set()
        
        for chunk in chunks:
            chunk["masked_text"] = "[DLP ERROR - Original text preserved]"
            chunk["pii_found"] = False
            chunk["pii_count"] = 0
            chunk["pii_types"] = []
            
            # Add original_text since there was an error
            chunk["original_text"] = chunk.get("text", "")
            
            # Add embedding_ready_text for RAG processing
            chunk["embedding_ready_text"] = chunk["masked_text"].lower().replace("\n", " ").strip()
        
        # Post-processing: Merge edges and trace_links into relationships even on error
        print(f"🔗 Creating relationships for improved traceability...")
        for chunk in chunks:
            chunk_page = chunk.get("page_number")
            chunk_id = chunk.get("chunk_id", "")

            # Add unique node_id for KG
            chunk["node_id"] = f"NODE_{chunk_id}"

            # Get trace_links from chunk (if exists)
            trace_links = chunk.get("trace_links", [])
            relationships = []

            # Build relationships from trace_links (preferred source)
            if trace_links:
                for edge in trace_links:
                    relationship = {
                        "edge_id": f"EDGE_{chunk_id}_{len(relationships) + 1:03d}",
                        "source_id": edge.get("source", ""),
                        "target_id": edge.get("target", ""),
                        "type": edge.get("relationship", "REQUIRES_COMPLIANCE"),
                        "target_class": (
                            "COMPLIANCE_STANDARD"
                            if "compliance" in edge.get("target_type", "").lower()
                            else edge.get("target_type", "UNKNOWN")
                        ),
                        "confidence": edge.get("confidence", 0.7),
                        "page": edge.get("page")
                    }
                    relationships.append(relationship)

                    # Collect compliance standards for summary
                    if relationship["target_class"] == "COMPLIANCE_STANDARD":
                        compliance_standards.add(relationship["target_id"])

            # Fallback: build from global edges if trace_links is empty
            elif chunk_page and edges:
                chunk_edges = [e for e in edges if e.get("page") == chunk_page]
                for edge in chunk_edges:
                    relationship = {
                        "edge_id": f"EDGE_{chunk_id}_{len(relationships) + 1:03d}",
                        "source_id": edge.get("source", ""),
                        "target_id": edge.get("target", ""),
                        "type": edge.get("relationship", "REQUIRES_COMPLIANCE"),
                        "target_class": edge.get("target_type", "UNKNOWN"),
                        "confidence": edge.get("confidence", 0.7),
                        "page": chunk_page
                    }
                    relationships.append(relationship)

                    # Collect compliance standards for summary
                    if relationship["target_class"] == "COMPLIANCE_STANDARD":
                        compliance_standards.add(relationship["target_id"])

            chunk["relationships"] = relationships

            # Remove trace_links after merging (redundant)
            if "trace_links" in chunk:
                del chunk["trace_links"]

            # Remove original_text if no PII found (reduce payload)
            if not chunk.get("pii_found", False) and "original_text" in chunk:
                del chunk["original_text"]

        # Calculate pipeline metrics for dashboarding (even on error)
        summary_base = docai_response.get("summary", {})

        # Average confidence across all detected requirements
        all_requirements = [r for c in chunks for r in c.get("detected_requirements", [])]
        avg_confidence = round(
            sum(r.get("confidence", 0) for r in all_requirements) / max(1, len(all_requirements)),
            2
        ) if all_requirements else 0.0

        # Compliance density: ratio of compliance standards to requirements
        compliance_density = round(
            summary_base.get("compliance_standards_found", 0) / max(1, summary_base.get("requirements_found", 1)),
            2
        )

        # PII density: ratio of chunks with PII to total chunks (0 on error)
        pii_density = 0.0

        # Calculate derived summary metrics
        relationships_total = sum(len(c.get("relationships", [])) for c in chunks)
        unique_compliance_links = len(set(
            r["target_id"] for c in chunks for r in c.get("relationships", [])
            if r.get("target_class") == "COMPLIANCE_STANDARD"
        ))

        return {
            "chunks": chunks,
            "summary": {
                **summary_base,
                "pii_masking_performed": False,
                "error": str(e),
                "compliance_summary": list(compliance_standards),
                "avg_confidence": avg_confidence,
                "compliance_density": compliance_density,
                "pii_density": pii_density,
                "relationships_total": relationships_total,
                "unique_compliance_links": unique_compliance_links
            }
        }


async def process_chunks_with_dlp_async(chunks: List[dict], project_id: str, location: str = DLP_DEFAULT_LOCATION) -> List[dict]:
    """
    Process all chunks with DLP asynchronously using asyncio.to_thread() to avoid blocking.
    
    This function wraps the synchronous DLP API calls in asyncio.to_thread() to prevent
    blocking the event loop, allowing for better concurrency.
    
    Args:
        chunks: List of chunks to process
        project_id: GCP project ID
        location: DLP API location (e.g., "us", "europe-west1", "asia-southeast1")
    
    Returns:
        List of results with masked_text, pii_found, pii_count, pii_types
    """
    # Detect if user passed project number instead of project ID
    if project_id.isdigit():
        error_message = (
            f"DLP API requires PROJECT ID (string), not PROJECT NUMBER (numeric).\n"
            f"   You provided: {project_id} (this is a project NUMBER)\n\n"
            f"🔧 How to find your project ID:\n"
            f"   1. Go to: https://console.cloud.google.com/\n"
            f"   2. Click the project dropdown at the top\n"
            f"   3. Your project ID is shown in the 'ID' column (string like 'my-project-123')\n"
            f"   4. Update PROJECT_ID environment variable with the project ID, not the number"
        )
        print(f"❌ {error_message}")
        raise ValueError(f"DLP API requires project ID (string), got project number: {project_id}")

    # Validate project_id
    if not project_id or not project_id.strip():
        print(f"❌ Invalid project_id: '{project_id}'")
        return [{
            "masked_text": chunk.get("text", ""),
            "pii_found": False,
            "pii_count": 0,
            "pii_types": []
        } for chunk in chunks]

    # ⚠️ CRITICAL: DLP API requires project ID (string like "my-project"), NOT project number (numeric)
    # If you're getting "400 Malformed parent field", you're likely using project number instead of project ID
    # Example: ✅ "poc-genai-hacks" (project ID) vs ❌ "401328495550" (project number)
    project_id_clean = project_id.strip()

    # Initialize DLP client once (outside threads to avoid gRPC fork warnings)
    dlp_client = dlp_v2.DlpServiceClient()

    # Per REST API docs, parent format for deidentify_content can be:
    # Option 1: projects/{projectId} (uses default global location)
    # Option 2: projects/{projectId}/locations/{locationId} (explicit location)
    # We'll use Option 1 (simplest, most reliable)
    parent = f"projects/{project_id_clean}"

    print(f"🔒 DLP Configuration:")
    print(f"   Project ID: {project_id_clean}")
    print(f"   Parent: {parent}")
    print(f"   Chunks to process: {len(chunks)}")
    
    # Pre-configure DLP configs (reused for all chunks)
    deidentify_config = dlp_v2.DeidentifyConfig(
        info_type_transformations=dlp_v2.InfoTypeTransformations(
            transformations=[
                dlp_v2.InfoTypeTransformations.InfoTypeTransformation(
                    info_types=[
                        dlp_v2.InfoType(name="EMAIL_ADDRESS"),
                        dlp_v2.InfoType(name="PHONE_NUMBER"),
                        dlp_v2.InfoType(name="PERSON_NAME"),
                        dlp_v2.InfoType(name="CREDIT_CARD_NUMBER"),
                        dlp_v2.InfoType(name="US_SOCIAL_SECURITY_NUMBER"),
                        dlp_v2.InfoType(name="IP_ADDRESS"),
                        dlp_v2.InfoType(name="DATE_OF_BIRTH"),
                        dlp_v2.InfoType(name="US_PASSPORT"),
                        dlp_v2.InfoType(name="US_DRIVERS_LICENSE_NUMBER")
                    ],
                    primitive_transformation=dlp_v2.PrimitiveTransformation(
                        replace_with_info_type_config=dlp_v2.ReplaceWithInfoTypeConfig()
                    )
                )
            ]
        )
    )

    inspect_config = dlp_v2.InspectConfig(
        info_types=[
            dlp_v2.InfoType(name="EMAIL_ADDRESS"),
            dlp_v2.InfoType(name="PHONE_NUMBER"),
            dlp_v2.InfoType(name="PERSON_NAME"),
            dlp_v2.InfoType(name="CREDIT_CARD_NUMBER"),
            dlp_v2.InfoType(name="US_SOCIAL_SECURITY_NUMBER"),
            dlp_v2.InfoType(name="IP_ADDRESS"),
            dlp_v2.InfoType(name="DATE_OF_BIRTH"),
            dlp_v2.InfoType(name="US_PASSPORT"),
            dlp_v2.InfoType(name="US_DRIVERS_LICENSE_NUMBER")
        ],
        min_likelihood=dlp_v2.Likelihood.POSSIBLE
    )

    # Process chunks in parallel batches for better performance
    batch_size = 5
    all_results = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # Process batch in parallel using asyncio.gather
        # Pass shared client and configs to avoid recreating them in each thread
        tasks = [
            _process_single_chunk_with_dlp_async(chunk, dlp_client, parent, deidentify_config, inspect_config)
            for chunk in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                print(f"⚠️  DLP error for chunk {batch[j].get('chunk_id', 'unknown')}: {str(result)}")
                all_results.append({
                    "masked_text": "[DLP ERROR - Original text preserved]",
                    "pii_found": False,
                    "pii_count": 0,
                    "pii_types": []
                })
            else:
                all_results.append(result)
    
    return all_results


async def _process_single_chunk_with_dlp_async(
    chunk: dict,
    dlp_client: dlp_v2.DlpServiceClient,
    parent: str,
    deidentify_config: dlp_v2.DeidentifyConfig,
    inspect_config: dlp_v2.InspectConfig
) -> dict:
    """
    Process a single chunk with DLP asynchronously using asyncio.to_thread().
    
    This function wraps the synchronous DLP API call in asyncio.to_thread() to avoid
    blocking the event loop. Client and configs are passed in to avoid recreation.
    
    Args:
        chunk: Chunk dictionary with 'text' field
        dlp_client: Shared DLP client instance
        parent: Parent resource path
        deidentify_config: Pre-configured deidentify config
        inspect_config: Pre-configured inspect config
    
    Returns:
        Dictionary with masked_text, pii_found, pii_count, pii_types
    """
    chunk_text = chunk.get("text", "")
    
    # Skip empty chunks
    if not chunk_text.strip():
        return {
            "masked_text": "",
            "pii_found": False,
            "pii_count": 0,
            "pii_types": []
        }
    
    try:
        # Create ContentItem with proper SDK types
        content_item = dlp_v2.ContentItem(value=chunk_text)

        # Create properly typed request using SDK classes
        request = dlp_v2.DeidentifyContentRequest(
            parent=parent,
            deidentify_config=deidentify_config,
            inspect_config=inspect_config,
            item=content_item
        )

        # Execute DLP request using asyncio.to_thread() to avoid blocking
        response = await asyncio.to_thread(dlp_client.deidentify_content, request=request)
        masked_text = response.item.value

        # Extract PII details from the response
        pii_types = []
        pii_count = 0

        # Process transformation summaries for de-identification details
        if hasattr(response, 'overview') and response.overview and hasattr(response.overview, 'transformation_summaries'):
            for summary in response.overview.transformation_summaries:
                if hasattr(summary, 'info_type') and summary.info_type and hasattr(summary.info_type, 'name'):
                    if summary.info_type.name not in pii_types:
                        pii_types.append(summary.info_type.name)

                # Count transformations - use 'count' field directly if available
                if hasattr(summary, 'count'):
                    pii_count += summary.count
                elif hasattr(summary, 'results'):
                    # Fallback: sum counts from results field
                    pii_count += sum(getattr(result, 'count', 0) for result in summary.results)

        # Determine if PII was found
        pii_found = pii_count > 0 or len(pii_types) > 0

        return {
            "masked_text": masked_text,
            "pii_found": pii_found,
            "pii_count": pii_count,
            "pii_types": pii_types
        }
    except Exception as e:
        chunk_id = chunk.get("chunk_id", "unknown")
        print(f"⚠️  DLP processing error for chunk {chunk_id}: {str(e)}")
        # Return original text when DLP call fails; do not retry with unsupported parents
        return {
            "masked_text": chunk_text,
            "pii_found": False,
            "pii_count": 0,
            "pii_types": []
        }


