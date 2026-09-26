# MAANAKNETRA - Product Scope & Requirements
**Smart India Hackathon 2026 | Problem Statement SIH26108**

---

## 1. Primary User Persona

### **The Procurement Officer (Government / PSU / GeM Buyer / Enterprise)**
- **Profile:** Departmental procurement executives, GeM (Government e-Marketplace) buyers, technical evaluation committee members, and tender drafting authorities across Indian ministries and public sector undertakings (PSUs).
- **Core Needs:**
  - Quickly ascertain whether a draft or incoming tender specification aligns with relevant, up-to-date Indian Standards (BIS).
  - Avoid tender litigation, project delays, or audit rejections (CAG/CVC) due to outdated, superseded, or conflicting standards.
  - Comply with mandatory Quality Control Orders (QCOs) issued by line ministries (e.g., DPIIT, Ministry of Steel, MeitY).
  - Avoid time-consuming manual referencing of thousands of standards, amendments, and cross-references.
  - Require auditable, exportable evidence justifying every tender decision and compliance mark.

---

## 2. Problem Being Solved

In public procurement in India:
1. **Outdated Standards in Tenders:** Tenders frequently reference obsolete, superseded, or withdrawn IS codes (e.g., specifying IS 2062:1999 instead of IS 2062:2011, or citing an obsolete cement standard), leading to defective procurement, supply-chain disputes, and CVC queries.
2. **Ignored Mandatory QCOs:** Line ministries periodically issue Quality Control Orders mandating ISI mark certification prior to sale/import. Tender documents routinely omit mandatory QCO clauses, risking illegal non-compliant supply.
3. **Parameter Discrepancies:** Tenders often mandate custom physical/chemical parameters that directly contradict the governing IS standard or fail to cite required standard test methods.
4. **Missing Associated Standards:** A primary product standard relies on normative references (test methods, safety guidelines, installation practices). Tenders cite only the primary standard, omitting crucial testing or safety norms.
5. **Chatbot Hallucination Risk:** Existing AI solutions act as unstructured generative chatbots that invent fictional BIS standard numbers, fabricate amendment years, or misstate legal QCO deadlines.

---

## 3. Core Workflow

```
[ Upload Tender / Specification (PDF/DOCX) ]
                    │
                    ▼
     [ 1. Ingestion & Preprocessing ]
       Extract raw text, sections, and tables (PyMuPDF)
                    │
                    ▼
     [ 2. Requirement Extraction ]
       Extract technical parameters, materials, test conditions, 
       and explicit standard citations using LLM-assisted parsing
                    │
                    ▼
     [ 3. Hybrid Standard Identification ]
       Dense semantic search (BGE-M3) + Lexical search (BM25)
       Cross-Encoder reranking against curated BIS catalog
                    │
                    ▼
     [ 4. Graph-Based Expansion ]
       Traverse relationship graph:
       Normative ── Test Methods ── Safety ── Installation
                    │
                    ▼
     [ 5. Deterministic Compliance Engine ]
       - Check active / superseded / withdrawn status
       - Check amendment currency
       - Check mandatory QCO applicability
       - Verify parameter ranges vs. IS tolerances
                    │
                    ▼
     [ 6. Audit & Discrepancy Generation ]
       Identify missing, conflicting, outdated parameters
                    │
                    ▼
     [ 7. Corrected Specification & Audit Report ]
       Generate downloadable auditable report with full citations, 
       clause references, and side-by-side corrected clauses
```

---

## 4. Feature Prioritization (Prototype Roadmap)

### **MUST BUILD Features (Core Prototype for SIH26108)**
- [x] **Tender Document Ingestion:** Reliable text and table extraction from digital PDF tender specifications (via PyMuPDF).
- [x] **Technical Requirement Extraction:** Structured JSON extraction of physical/chemical parameters, tolerances, operating limits, and mentioned standards.
- [x] **Curated BIS Standards Database:** High-integrity, verified structured repository covering key representative procurement sectors (e.g., Electrical equipment, Steel & Structural, Construction, Electronics/IT).
- [x] **Status & Amendment Verification:** Deterministic checks for:
  - Standard status: `CURRENT`, `SUPERSEDED`, `WITHDRAWN`, `UNDER_REVISION`.
  - Latest amendment tracking.
  - Supersession link (e.g., "IS X superseded by IS Y").
- [x] **Mandatory QCO Verification:** Deterministic check against verified Quality Control Orders (effective date, mandatory ISI mark mandate, issuing ministry).
- [x] **Relationship Expansion Graph:** Automatic expansion of governing standard into normative references, testing standards, and safety standards using structured graph links.
- [x] **Parameter-Level Verification:** Automated comparison between tender-specified values and official standard parameters/tolerances.
- [x] **Audit Findings & Explainability:** Categorized discrepancy flags (Critical, Warning, Info) with exact citations, evidence snippets, and deterministic rule references.
- [x] **Corrected Clause Generation:** Side-by-side corrected clause generation replacing outdated references with active codes.

### **SHOULD BUILD Features (High Priority if prototype milestones met early)**
- [ ] **Exportable Audit Report:** Formal PDF / Word audit summary for procurement files.
- [ ] **Side-by-Side Clause Diff Viewer:** Interactive visual diff showing original tender clause vs. corrected clause.
- [ ] **Multi-standard comparative view:** Comparison across multiple overlapping standards.
- [ ] **Confidence Scoring Breakdown:** Visual metric showing semantic retrieval confidence vs. deterministic rule match certainty.

### **SKIP Features (Explicitly Deferred for First Prototype)**
- ❌ **Generic Conversational Chatbot:** No free-form unconstrained chat interface; all output is structured, actionable, and report-oriented.
- ❌ **Automated Real-Time Web Scraping:** No unvetted, live web crawlers scraping volatile third-party websites during demo execution.
- ❌ **Complex OCR for Poorly Scanned Photocopies:** Initial prototype focuses on digital PDFs/documents; deep OCR fallback deferred to subsequent iterations.
- ❌ **End-to-End E-Procurement ERP Integration:** Direct API integration into GeM / CPPP systems deferred to production phase.
- ❌ **Full Indian Standards Corpus Coverage:** Rather than shallow, unverified coverage of all 20,000+ standards, prototype focuses on depth, verification, and complete relationship trees for target procurement sectors.
