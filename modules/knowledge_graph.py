"""
Knowledge Graph Module
Handles knowledge graph construction and analysis
"""

from typing import Dict, Any, List


def build_knowledge_graph_from_rag(rag_output: dict, test_cases: list = None) -> dict:
    """
    Build a comprehensive knowledge graph from RAG output with enhanced traceability

    Accepts raw RAG JSON and processes:
    1. Creates REQUIREMENT nodes from detected_requirements
    2. Creates COMPLIANCE_STANDARD nodes from detected_compliance and relationship targets
    3. Uses relationships[] to connect requirements to compliance nodes
    4. Normalizes compliance names using canonical IDs
    5. Adds comprehensive metadata (total_nodes, total_edges, avg_confidence, etc.)

    Args:
        rag_output: RAG processing results with chunks (from /rag-enhance endpoint)
        test_cases: Optional list of test cases to include in the graph

    Returns:
        Knowledge graph with nodes, edges, and metadata
    """
    try:
        # Get chunks from RAG output (unified structure from DLP masking)
        chunks = rag_output.get("chunks", [])
        if not chunks:
            return {
                "status": "error",
                "agent": "Traceability-KG-Builder",
                "error": "No chunks available for knowledge graph construction",
                "nodes": [],
                "edges": [],
                "metadata": {}
            }

        nodes = []
        edges = []
        seen_requirements = set()
        seen_compliance = {}  # canonical_id -> node_info
        seen_test_cases = set()

        # Compliance normalization map (variations -> canonical ID)
        compliance_normalization = {
            "gdpr": "GDPR:2016/679",
            "gdpr:2016/679": "GDPR:2016/679",
            "general data protection regulation": "GDPR:2016/679",
            "ccpa": "CCPA:2018",
            "ccpa:2018": "CCPA:2018",
            "california consumer privacy act": "CCPA:2018",
            "hipaa": "HIPAA:1996",
            "hipaa:1996": "HIPAA:1996",
            "health insurance portability": "HIPAA:1996",
            "fda": "FDA:21CFR11",
            "fda 21 cfr part 11": "FDA:21CFR11",
            "21 cfr part 11": "FDA:21CFR11",
            "soc2": "SOC2:TypeII",
            "soc 2": "SOC2:TypeII",
            "iso27001": "ISO:27001",
            "iso 27001": "ISO:27001"
        }

        def normalize_compliance_id(raw_id: str) -> str:
            """Normalize compliance ID to canonical form"""
            if not raw_id:
                return "UNKNOWN"
            raw_lower = raw_id.lower().strip()
            return compliance_normalization.get(raw_lower, raw_id)

        # Process each chunk to extract nodes and relationships
        for chunk in chunks:
            page_number = chunk.get("page_number", 1)
            chunk_id = chunk.get("chunk_id", "")
            node_id = chunk.get("node_id", f"NODE_{chunk_id}")

            # 1. Create REQUIREMENT nodes from detected_requirements
            detected_requirements = chunk.get("detected_requirements", [])
            for req_entity in detected_requirements:
                req_id = req_entity.get("id")

                if req_id and req_id not in seen_requirements:
                    req_node = {
                        "id": req_id,
                        "type": "REQUIREMENT",
                        "title": req_entity.get("text", "")[:100] + "..." if len(req_entity.get("text", "")) > 100 else req_entity.get("text", ""),
                        "text": req_entity.get("text", ""),
                        "confidence": req_entity.get("confidence", 0.0),
                        "page_number": page_number,
                        "priority": "High" if "critical" in req_entity.get("text", "").lower() else "Medium"
                    }
                    nodes.append(req_node)
                    seen_requirements.add(req_id)

            # 2a. Create COMPLIANCE_STANDARD nodes from detected_compliance
            detected_compliance = chunk.get("detected_compliance", [])
            for comp_entity in detected_compliance:
                comp_raw_id = comp_entity.get("id", comp_entity.get("standard", ""))
                comp_canonical_id = normalize_compliance_id(comp_raw_id)

                if comp_canonical_id and comp_canonical_id not in seen_compliance:
                    comp_kg_id = f"COMP_{len(seen_compliance) + 1:03d}"

                    # Determine standard type from canonical ID
                    standard_type = "UNKNOWN"
                    if comp_canonical_id.startswith("GDPR"):
                        standard_type = "GDPR"
                    elif comp_canonical_id.startswith("CCPA"):
                        standard_type = "CCPA"
                    elif comp_canonical_id.startswith("HIPAA"):
                        standard_type = "HIPAA"
                    elif comp_canonical_id.startswith("FDA"):
                        standard_type = "FDA"
                    elif comp_canonical_id.startswith("SOC2"):
                        standard_type = "SOC2"
                    elif comp_canonical_id.startswith("ISO"):
                        standard_type = "ISO"

                    comp_node = {
                        "id": comp_kg_id,
                        "type": "COMPLIANCE_STANDARD",
                        "title": comp_canonical_id,
                        "text": comp_entity.get("text", f"Compliance standard: {comp_canonical_id}"),
                        "confidence": comp_entity.get("confidence", 0.8),
                        "source": "detected_compliance",
                        "standard_type": standard_type,
                        "page_number": page_number
                    }
                    nodes.append(comp_node)
                    seen_compliance[comp_canonical_id] = comp_kg_id

            # 2b. Create COMPLIANCE_STANDARD nodes from relationship targets
            relationships = chunk.get("relationships", [])
            for rel in relationships:
                target_id = rel.get("target_id")
                target_class = rel.get("target_class", "UNKNOWN")

                if target_class == "COMPLIANCE_STANDARD" and target_id:
                    comp_canonical_id = normalize_compliance_id(target_id)

                    if comp_canonical_id not in seen_compliance:
                        comp_kg_id = f"COMP_{len(seen_compliance) + 1:03d}"

                        # Determine standard type from canonical ID
                        standard_type = "UNKNOWN"
                        if comp_canonical_id.startswith("GDPR"):
                            standard_type = "GDPR"
                        elif comp_canonical_id.startswith("CCPA"):
                            standard_type = "CCPA"
                        elif comp_canonical_id.startswith("HIPAA"):
                            standard_type = "HIPAA"
                        elif comp_canonical_id.startswith("FDA"):
                            standard_type = "FDA"
                        elif comp_canonical_id.startswith("SOC2"):
                            standard_type = "SOC2"
                        elif comp_canonical_id.startswith("ISO"):
                            standard_type = "ISO"

                        comp_node = {
                            "id": comp_kg_id,
                            "type": "COMPLIANCE_STANDARD",
                            "title": comp_canonical_id,
                            "text": f"Compliance standard: {comp_canonical_id}",
                            "confidence": rel.get("confidence", 0.7),
                            "source": "chunk_relationships",
                            "standard_type": standard_type,
                            "page_number": page_number
                        }
                        nodes.append(comp_node)
                        seen_compliance[comp_canonical_id] = comp_kg_id

            # 3. Use relationships[] to connect requirements to compliance nodes
            for rel in relationships:
                source_id = rel.get("source_id")
                target_id = rel.get("target_id")
                target_class = rel.get("target_class", "UNKNOWN")
                rel_type = rel.get("type", "RELATED")
                confidence = rel.get("confidence", 0.7)
                edge_id = rel.get("edge_id", f"edge_{len(edges) + 1:03d}")

                # Skip invalid relationships
                if not source_id or not target_id:
                    continue

                # Normalize target_id if it's a compliance standard
                if target_class == "COMPLIANCE_STANDARD":
                    comp_canonical_id = normalize_compliance_id(target_id)
                    kg_target_id = seen_compliance.get(comp_canonical_id, target_id)
                else:
                    kg_target_id = target_id

                edge = {
                    "id": edge_id,
                    "from": source_id,
                    "to": kg_target_id,
                    "relation": rel_type,
                    "confidence": confidence,
                    "source": "chunk_relationships",
                    "page": rel.get("page", page_number)
                }
                edges.append(edge)

        # Add test cases if provided
        if test_cases:
            for test_case in test_cases:
                test_id = test_case.get("id", f"TC_{len(seen_test_cases) + 1:03d}")
                if test_id not in seen_test_cases:
                    test_node = {
                        "id": test_id,
                        "id": test_id,
                        "type": "TEST_CASE",
                        "title": test_case.get("title", "Unknown Test"),
                        "text": test_case.get("description", ""),
                        "category": test_case.get("category", "Unknown"),
                        "priority": test_case.get("priority", "Medium"),
                        "confidence": 0.9  # High confidence for generated test cases
                    }
                    nodes.append(test_node)
                    seen_test_cases.add(test_id)

                    # Create edges from test cases to requirements
                    derived_from = test_case.get("derived_from")
                    if derived_from and derived_from in seen_requirements:
                        edge = {
                            "id": f"edge_{len(edges) + 1:03d}",
                            "from": test_id,
                            "to": derived_from,
                            "relation": "VERIFIED_BY",
                            "confidence": 0.9,
                            "source": "test_generation"
                        }
                        edges.append(edge)

        # 4. Add comprehensive metadata at the end
        total_nodes = len(nodes)
        total_edges = len(edges)
        requirement_count = len([n for n in nodes if n["type"] == "REQUIREMENT"])
        compliance_count = len([n for n in nodes if n["type"] == "COMPLIANCE_STANDARD"])
        test_count = len([n for n in nodes if n["type"] == "TEST_CASE"])

        # Calculate cross-page relationships (edges spanning multiple pages)
        pages_in_edges = set(e.get("page") for e in edges if e.get("page"))
        cross_page_links = len(pages_in_edges)

        # Calculate average confidence across all edges
        avg_confidence = round(
            sum(e.get("confidence", 0.0) for e in edges) / max(1, total_edges),
            2
        ) if edges else 0.0

        # Calculate graph density (edges per node ratio)
        graph_density = round(total_edges / max(1, total_nodes), 2)

        # Count compliance standards by type
        compliance_by_type = {}
        for node in nodes:
            if node["type"] == "COMPLIANCE_STANDARD":
                std_type = node.get("standard_type", "UNKNOWN")
                compliance_by_type[std_type] = compliance_by_type.get(std_type, 0) + 1

        # Count edges by relation type
        edges_by_relation = {}
        for edge in edges:
            rel_type = edge.get("relation", "UNKNOWN")
            edges_by_relation[rel_type] = edges_by_relation.get(rel_type, 0) + 1

        # Find nodes with most connections (high-degree nodes)
        node_degrees = {}
        for edge in edges:
            source = edge.get("from")
            target = edge.get("to")
            node_degrees[source] = node_degrees.get(source, 0) + 1
            node_degrees[target] = node_degrees.get(target, 0) + 1

        top_connected_nodes = sorted(
            node_degrees.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 most connected nodes

        return {
            "status": "success",
            "agent": "Traceability-KG-Builder",
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "requirement_nodes": requirement_count,
                "compliance_nodes": compliance_count,
                "test_case_nodes": test_count,
                "graph_density": graph_density,
                "avg_confidence": avg_confidence,
                "cross_page_links": cross_page_links,
                "compliance_by_type": compliance_by_type,
                "edges_by_relation": edges_by_relation,
                "top_connected_nodes": [
                    {"node_id": node_id, "connections": count}
                    for node_id, count in top_connected_nodes
                ],
                "normalized_compliance_count": len(seen_compliance),
                "tooltips": []
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "agent": "Traceability-KG-Builder",
            "error": str(e),
            "nodes": [],
            "edges": [],
            "metadata": {}
        }


def analyze_test_coverage(test_categories: list, kg_output: dict) -> dict:
    """
    🚀 Analyze test coverage against KG requirements

    Validates that test cases adequately cover the requirements and compliance standards
    found in the knowledge graph.

    Args:
        test_categories: List of test categories with test cases
        kg_output: Knowledge graph with nodes and edges

    Returns:
        Coverage analysis with gaps and recommendations
    """
    try:
        if not kg_output or kg_output.get("status") != "success":
            return {
                "status": "no_kg_data",
                "message": "No knowledge graph data available for coverage analysis"
            }

        kg_nodes = kg_output.get("nodes", [])
        kg_edges = kg_output.get("edges", [])

        # Extract requirements and compliance standards from KG
        requirements = [n for n in kg_nodes if n.get("type") == "REQUIREMENT"]
        compliance_standards = [n for n in kg_nodes if n.get("type") == "COMPLIANCE_STANDARD"]

        # Count test cases by category
        test_counts = {}
        total_tests = 0

        for category in test_categories:
            category_name = category.get("category_name", "Unknown")
            test_count = category.get("total_tests", 0)
            test_counts[category_name] = test_count
            total_tests += test_count

        # Analyze coverage gaps
        coverage_gaps = []
        coverage_recommendations = []

        # Check if we have enough test cases for requirements
        if len(requirements) > 0:
            tests_per_requirement = total_tests / len(requirements)
            if tests_per_requirement < 2:
                coverage_gaps.append({
                    "type": "insufficient_test_density",
                    "message": f"Only {tests_per_requirement:.1f} tests per requirement (recommended: 2+)",
                    "severity": "medium"
                })
                coverage_recommendations.append("Generate more test cases to improve requirement coverage")

        # Check compliance standard coverage
        if len(compliance_standards) > 0:
            compliance_tests = test_counts.get("Compliance Tests", 0)
            if compliance_tests < len(compliance_standards):
                coverage_gaps.append({
                    "type": "compliance_coverage_gap",
                    "message": f"Only {compliance_tests} compliance tests for {len(compliance_standards)} standards",
                    "severity": "high"
                })
                coverage_recommendations.append("Add more compliance test cases")

        # Check security test coverage
        security_tests = test_counts.get("Security Tests", 0)
        if security_tests < 3:
            coverage_gaps.append({
                "type": "security_coverage_gap",
                "message": f"Only {security_tests} security tests (recommended: 3+)",
                "severity": "high"
            })
            coverage_recommendations.append("Add more security test cases for comprehensive coverage")

        # Calculate coverage metrics
        coverage_score = min(100, (total_tests / max(1, len(requirements))) * 20)  # Max 100%

        return {
            "status": "success",
            "coverage_score": round(coverage_score, 1),
            "total_requirements": len(requirements),
            "total_compliance_standards": len(compliance_standards),
            "total_tests": total_tests,
            "test_distribution": test_counts,
            "coverage_gaps": coverage_gaps,
            "recommendations": coverage_recommendations,
            "kg_utilization": {
                "requirements_mapped": len([tc for cat in test_categories for tc in cat.get("test_cases", []) if tc.get("traceability", {}).get("kg_mapping", {}).get("kg_coverage", 0) > 0]),
                "total_kg_nodes": len(kg_nodes),
                "total_kg_edges": len(kg_edges)
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "coverage_score": 0
        }


def create_flow_visualization(ui_result: dict, kg_result: dict) -> dict:
    """
    🚀 Create requirement → test → compliance flow visualization

    Maps the relationships between requirements, test cases, and compliance standards
    for comprehensive traceability visualization.

    Args:
        ui_result: UI enrichment result with test categories
        kg_result: Knowledge graph with nodes and edges

    Returns:
        Flow visualization data for frontend
    """
    try:
        if not kg_result or kg_result.get("status") != "success":
            return {
                "status": "no_kg_data",
                "message": "No knowledge graph data available for flow visualization"
            }

        kg_nodes = kg_result.get("nodes", [])
        kg_edges = kg_result.get("edges", [])
        test_categories = ui_result.get("test_categories", [])

        # Build flow paths: Requirement → Test → Compliance
        flow_paths = []
        requirement_coverage = {}
        compliance_coverage = {}

        # Extract all test cases
        all_test_cases = []
        for category in test_categories:
            all_test_cases.extend(category.get("test_cases", []))

        # Map requirements to test cases
        for test_case in all_test_cases:
            traceability = test_case.get("traceability", {})
            req_id = traceability.get("requirement_id")
            kg_mapping = traceability.get("kg_mapping", {})

            if req_id:
                if req_id not in requirement_coverage:
                    requirement_coverage[req_id] = {
                        "requirement_id": req_id,
                        "requirement_text": traceability.get("requirement_text", ""),
                        "test_cases": [],
                        "compliance_standards": []
                    }

                requirement_coverage[req_id]["test_cases"].append({
                    "test_id": test_case.get("test_id"),
                    "title": test_case.get("title"),
                    "category": test_case.get("category"),
                    "priority": test_case.get("priority")
                })

                # Map to compliance standards through KG
                kg_edges_for_req = kg_mapping.get("kg_edges", [])

                # Fallback: If kg_mapping doesn't have edges, get them directly from KG
                if not kg_edges_for_req and req_id:
                    kg_edges_for_req = [e for e in kg_edges if e.get("from") == req_id]

                for kg_edge in kg_edges_for_req:
                    # Handle both kg_mapping format and direct KG edge format
                    target_id = kg_edge.get("to") or kg_edge.get("target_id")
                    compliance_std = next((n for n in kg_nodes if n["id"] == target_id), None)

                    if compliance_std and compliance_std.get("type") == "COMPLIANCE_STANDARD":
                        std_id = compliance_std["id"]
                        std_title = compliance_std.get("title", "")

                        if std_id not in compliance_coverage:
                            compliance_coverage[std_id] = {
                                "standard_id": std_id,
                                "standard_name": std_title,
                                "standard_type": compliance_std.get("standard_type", "UNKNOWN"),
                                "test_cases": [],
                                "requirements": []
                            }

                        # Add test case and requirement to compliance coverage
                        test_id = test_case.get("test_id")
                        if test_id not in compliance_coverage[std_id]["test_cases"]:
                            compliance_coverage[std_id]["test_cases"].append(test_id)
                        if req_id not in compliance_coverage[std_id]["requirements"]:
                            compliance_coverage[std_id]["requirements"].append(req_id)

                        # Also add compliance to requirement coverage
                        if std_title not in requirement_coverage[req_id]["compliance_standards"]:
                            requirement_coverage[req_id]["compliance_standards"].append(std_title)

        # Create flow visualization
        flow_visualization = {
            "status": "success",
            "total_requirements": len(requirement_coverage),
            "total_compliance_standards": len(compliance_coverage),
            "total_test_cases": len(all_test_cases),
            "requirement_coverage": list(requirement_coverage.values()),
            "compliance_coverage": list(compliance_coverage.values()),
            "flow_metrics": {
                "avg_tests_per_requirement": round(len(all_test_cases) / max(1, len(requirement_coverage)), 1),
                "avg_requirements_per_standard": round(len(requirement_coverage) / max(1, len(compliance_coverage)), 1),
                "coverage_completeness": min(100, (len(requirement_coverage) / max(1, len([n for n in kg_nodes if n.get("type") == "REQUIREMENT"]))) * 100)
            },
            "visualization_data": {
                "nodes": [
                    {
                        "id": f"req_{req_id}",
                        "type": "requirement",
                        "label": req_id,
                        "title": req_data["requirement_text"][:50] + "...",
                        "test_count": len(req_data["test_cases"])
                    }
                    for req_id, req_data in requirement_coverage.items()
                ] + [
                    {
                        "id": f"std_{std_id}",
                        "type": "compliance_standard",
                        "label": std_id,
                        "title": std_data["standard_name"],
                        "test_count": len(std_data["test_cases"])
                    }
                    for std_id, std_data in compliance_coverage.items()
                ] + [
                    {
                        "id": tc["test_id"],
                        "type": "test_case",
                        "label": tc["test_id"],
                        "title": tc["title"],
                        "category": tc["category"],
                        "priority": tc["priority"]
                    }
                    for tc in all_test_cases
                ],
                "edges": [
                    {
                        "from": f"req_{req_id}",
                        "to": tc["test_id"],
                        "type": "verifies",
                        "label": "verifies"
                    }
                    for req_id, req_data in requirement_coverage.items()
                    for tc in req_data["test_cases"]
                ] + [
                    {
                        "from": tc["test_id"],
                        "to": f"std_{std_id}",
                        "type": "ensures_compliance",
                        "label": "ensures"
                    }
                    for std_id, std_data in compliance_coverage.items()
                    for tc_id in std_data["test_cases"]
                    for tc in all_test_cases
                    if tc["test_id"] == tc_id
                ]
            }
        }

        return flow_visualization

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to create flow visualization"
        }
