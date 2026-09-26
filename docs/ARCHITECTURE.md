# MAANAKNETRA - System Architecture
**Smart India Hackathon 2026 | Problem Statement SIH26108**

---

## 1. Architectural Philosophy & Core Design Principle

> **"LLM interprets the tender; Structured Data + Deterministic Rules govern compliance."**

In regulatory and procurement systems, generative hallucinations are unacceptable. MAANAKNETRA enforces a strict architectural boundary:
- **Probabilistic / AI Layer:** Used exclusively where human-like language flexibility is required—ingesting unstructured tender prose, extracting key technical parameters, retrieving candidate standards via hybrid semantic search, and summarizing findings in concise procurement language.
- **Deterministic / Rule Layer:** Handles all compliance judgments, standard status (active/superseded/withdrawn), amendment applicability, parameter tolerance checking, and Quality Control Order (QCO) mandates based on verified, structured datasets.

```
┌────────────────────────────────────────────────────────┐
│               PROBABILISTIC / AI LAYER                 │
│  - Document Parsing (PyMuPDF)                          │
│  - Parameter Extraction (LLM Structured Output)        │
│  - Candidate Standard Retrieval (BGE-M3 + BM25)        │
│  - Semantic Explanation of Discrepancies               │
└───────────────────────────┬────────────────────────────┘
                            │ Structured Requirements
                            ▼
┌────────────────────────────────────────────────────────┐
│              DETERMINISTIC / RULE ENGINE               │
│  - BIS Database (Structured JSON / Graph)              │
│  - Active / Superseded / Withdrawn Verification        │
│  - Mandatory QCO Applicability Check                   │
│  - Parameter Bounds & Tolerance Comparison             │
│  - Related Standards Expansion (NetworkX)              │
└───────────────────────────┬────────────────────────────┘
                            │ Grounded Audit Results
                            ▼
┌────────────────────────────────────────────────────────┐
│                 PRESENTATION & AUDIT                   │
│  - React + TypeScript + Tailwind Dashboard             │
│  - Auditable Findings with Exact Evidence Citations    │
│  - Corrected Clauses & Exportable Procurement Report   │
└───────────────────────────┘
```

---

## 2. Technology Stack Specification

| Component | Selected Technology | Purpose & Rationale |
| :--- | :--- | :--- |
| **Frontend UI** | **React + TypeScript + Tailwind CSS** | Fast, responsive, component-driven dashboard providing high visual clarity, side-by-side clause comparisons, and audit tracking. |
| **Backend API** | **FastAPI (Python 3.10+)** | Asynchronous, high-throughput, schema-enforced REST API utilizing Pydantic models for validation and contract enforcement. |
| **Document Processing**| **PyMuPDF (`fitz`)** (with OCR fallback capability) | Extremely fast and accurate extraction of text, formatting, and tables from digital PDF tenders. |
| **Dense Embeddings** | **BGE-M3** (or compact local model) | Leading open embedding model capable of dense, multi-lingual, and code/technical terminology representation. |
| **Lexical Search** | **BM25 (`rank_bm25`)** | Exact-match retrieval for alphanumeric standard numbers (e.g., `IS 2062`, `IS 694`, `IS 732`). |
| **Reranking** | **Cross-Encoder (`bge-reranker-base` / `ms-marco`)** | Deep semantic pair scoring between extracted requirement snippets and candidate standard scopes. |
| **LLM Engine** | **Structured Output LLM (via local or API provider)** | Zero-shot / few-shot parameter extraction strictly conforming to JSON Schema contracts (`requirements.schema.json`). |
| **Vector Index** | **FAISS (Facebook AI Similarity Search)** | In-memory, ultra-fast vector index suitable for low-latency prototype retrieval without heavy cloud database dependencies. |
| **Standards Graph** | **NetworkX** | In-memory directed graph modeling relationships: primary standards, normative references, test methods, safety codes, and superseded lineages. |
| **Data Persistence** | **Curated Structured JSON** | Version-controlled, human-auditable JSON files representing standard specifications, QCO registries, and graph node relationships. |

---

## 3. Detailed Component Architecture

### A. Document Ingestion Pipeline
1. **Upload:** User submits tender PDF or text specification.
2. **Text & Table Parsing:** PyMuPDF parses the document into structured page blocks and tabular structures, preserving clause numbers and structural headers.
3. **Chunking & Windowing:** Document is segmented into cohesive technical clauses, preserving local context and references.

### B. Requirement Extraction (LLM + JSON Schema)
- The technical sections of the tender are processed using an LLM guided by few-shot prompts and strictly enforced against [`contracts/requirements.schema.json`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/contracts/requirements.schema.json).
- Extracts:
  - Equipment/material name and category.
  - Specified physical, electrical, or chemical parameters with numerical ranges and units.
  - Explicitly cited Indian or international standards (if any).
  - Operating conditions, test criteria, and safety mandates.

### C. Hybrid Retrieval Engine (Standard Identification)
To ensure both semantic understanding and exact alphanumeric recall:
1. **Lexical Retrieval (BM25):** Matches exact standard numbers (e.g., "IS 2062", "IS 1554 Part 1") and specific keywords.
2. **Dense Retrieval (BGE-M3 + FAISS):** Matches descriptive technical parameters against standard descriptions and scopes (e.g., "cross-linked polyethylene insulated cable" ➔ "IS 7098").
3. **Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking:** Merges BM25 and vector hits, passing top candidates through a Cross-Encoder to produce high-confidence candidate standards.

### D. Standards Relationship Graph (NetworkX)
Standards never exist in isolation. When a primary standard is identified:
- The system queries the `NetworkX` graph to retrieve all connected nodes:
  - `normative_reference`: Mandatory prerequisite standards.
  - `test_method`: Standardized laboratory procedures required to verify specified parameters.
  - `safety_standard`: Mandatory safety, insulation, or hazardous-use codes.
  - `installation_standard`: Associated codes of practice for erection/commissioning.
  - `superseded_by`: Lineage tracking which code replaces an obsolete code.

### E. Deterministic Compliance & Audit Engine
This layer operates on verified ground-truth data:
1. **Status Check:** Evaluates whether cited standards are `CURRENT`, `SUPERSEDED`, or `WITHDRAWN`.
2. **Amendment Audit:** Compares tender provisions against the latest gazetted amendments.
3. **QCO Verification:** Cross-references product category against the Ministry Quality Control Orders registry. If covered by a mandatory QCO, verifies whether tender includes mandatory ISI certification requirement.
4. **Parameter Matcher:** Compares extracted numerical requirements (e.g., Tensile Strength, Operating Voltage, Thickness) with official allowable ranges and tolerance limits in the standard.

### F. Findings & Corrected Specification Engine
- Formulates structured findings conforming to [`contracts/finding.schema.json`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/contracts/finding.schema.json).
- Generates side-by-side corrected clauses:
  - *Example:* Replaces obsolete "IS 2062:1999 Grade A" with active "IS 2062:2011 Grade E250 Quality A".
  - *Example:* Inserts mandatory clause: "Product must bear valid BIS Standard Mark (ISI mark) as per Quality Control Order S.O. XXX(E)".

---

## 4. Data Model and Traceability

The cornerstone of MAANAKNETRA's credibility is **unbroken end-to-end traceability**. In public procurement and CAG/CVC audit reviews, every recommendation or compliance flag must have an irrefutable paper trail back to the tender clause and the official gazetted standard.

### The Traceability Chain

```
┌────────────────────────────────────────────────────────┐
│ 1. TENDER RAW TEXT                                     │
│    Verbatim clause, source page, line number           │
└───────────────────────────┬────────────────────────────┘
                            │ LLM Parser + JSON Schema
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. REQUIREMENT OBJECTS (requirements.schema.json)      │
│    `requirement_id`, normalized parameter, unit,       │
│    operator, bounds, source_location, cited standard   │
└───────────────────────────┬────────────────────────────┘
                            │ Hybrid Search + Graph Match
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. STANDARD OBJECTS (standard.schema.json)             │
│    `is_number`, structured parameters, QCO order,      │
│    normative/test graph links, mandatory provenance    │
└───────────────────────────┬────────────────────────────┘
                            │ Deterministic Evaluation
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. GROUNDING EVIDENCE                                  │
│    Parameter comparison delta, BIS clause citation,    │
│    Gazette S.O. number, amendment date                 │
└───────────────────────────┬────────────────────────────┘
                            │ Tender Linter Rules
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. FINDING OBJECTS (finding.schema.json)               │
│    `finding_id`, severity, finding_type, deterministic │
│    rule ID, suggested replacement clause               │
└───────────────────────────┬────────────────────────────┘
                            │ Aggregation & Synthesis
                            ▼
┌────────────────────────────────────────────────────────┐
│ 6. FINAL ANALYSIS DOCUMENT (analysis.schema.json)      │
│    Standards BOM, side-by-side corrected clauses,      │
│    status flags, risk scorecard, officer review flag   │
└────────────────────────────────────────────────────────┘
```

### Traceability Connections in Detail

1. **Tender Text ➔ Requirement Objects (`requirements.schema.json`):**
   - The raw tender text is ingested, and specific technical sentences are extracted into discrete `RequirementItem` instances.
   - Each item retains `source_text`, `source_page`, and `clause_number`.
   - Visual highlighting hooks (`char_start`, `char_end`, `bounding_box`) are supported in `SourceLocation` to enable direct in-browser PDF highlighting.
   - Technical specifications are parsed into structured `NormalizedValue` objects (`min_value`, `max_value`, `operator`, `unit`), turning ambiguous free-text prose into queryable entities.
   - Explicit standards cited in the document are captured separately in `AlreadyCitedStandard` items to isolate user claims from system recommendations.

2. **Requirement Objects ➔ Standard Objects (`standard.schema.json`):**
   - Extracted requirements and product contexts are mapped to candidate standards using hybrid retrieval (BGE-M3 + BM25).
   - Candidate records are retrieved from the verified BIS catalog (`IndianStandardRecord`).
   - Every standard contains official metadata: status (`CURRENT`, `SUPERSEDED`, `WITHDRAWN`), gazetted amendments, mandatory QCO orders, and structured parameter thresholds (`StandardParameter`).
   - **Conditional Integrity:** Schema-enforced conditional validation requires `superseded_by` when `status == "SUPERSEDED"` and `withdrawn_reason` when `status == "WITHDRAWN"`.
   - Network links (`normative_references`, `test_standards`, `safety_standards`, `installation_standards`, and unclassified `related_standards`) expand the search into an interconnected standards graph.
   - **Provenance Mandate:** Each standard object carries a mandatory `source` and `verification` block proving its authenticity against official sources (e.g. Manakonline).

3. **Standard Objects + Requirements ➔ Grounding Evidence:**
   - Parameter matching algorithms compare the `NormalizedValue` of the requirement against the `StandardParameter` bounds in the standard.
   - If the tender specifies a superseded standard, the graph traverses `superseded_by` to identify the active replacement.
   - If the product category falls under a mandatory QCO, the system checks whether the tender included the mandatory ISI mark clause.
   - Evidence is captured as factual tuples: `(Tender Requirement, Governing IS Clause, Standard Limit, Statutory Gazette S.O.)`.

4. **Evidence ➔ Findings (`finding.schema.json`):**
   - The deterministic rule engine evaluates the evidence against formal rules (e.g. `RULE_SUPERSEDED_STANDARD`, `RULE_QCO_MANDATE_OMITTED`, `RULE_PARAMETER_OUT_OF_BOUNDS`).
   - Discrepancies generate structured `TenderLinterFinding` objects.
   - For `PARAMETER_CONFLICT` finding types, `affected_requirement` is strictly required to preserve parameter-level traceability.
   - Each finding records an officer resolution workflow (`resolution_status`: `PENDING`, `ACCEPTED`, `REJECTED`, `OVERRIDDEN`) with optional `officer_justification`, `resolved_by`, and `resolved_at`.
   - A concrete `suggested_fix` is generated, providing ready-to-use replacement clauses.

5. **Findings ➔ Final Analysis (`analysis.schema.json`):**
   - All findings, recommended standards, related graph expansions, and parameter compliance evaluations are assembled into a single unified `TenderAnalysisResultDocument`.
   - The document produces a **Standards Bill of Materials (Standards BOM)**, aggregating every primary, testing, safety, and installation standard required for end-to-end procurement.
   - Side-by-side corrected clauses (`corrected_clause`) allow procurement officers to review and adopt revisions directly, with every corrected clause explicitly linked to its causal findings via `linked_finding_ids`.
   - High-level `status_flags`, `certification_flags`, and an auditable `risk_indicator` scorecard quantify overall procurement safety.
   - A `human_review_required` boolean flag highlights whether officer intervention is mandatory before releasing the tender.
