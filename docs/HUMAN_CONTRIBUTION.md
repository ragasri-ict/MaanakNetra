# MAANAKNETRA - Human Contribution & Governance Framework
**Smart India Hackathon 2026 | Problem Statement SIH26108**

---

## 1. Guiding Principle: Human-Led Engineering

MAANAKNETRA is explicitly designed as a **human-led, human-governed engineering project**. AI acts strictly as an implementation assistant for document understanding, retrieval, and synthesis. The architectural integrity, domain correctness, validation mechanisms, and regulatory rules are engineered directly by the human team.

---

## 2. Explicit Responsibilities & Human Deliverables

The human team directly undertakes the following responsibilities:

### A. Standards Data Curation & Ground-Truth Verification
- **Human Action:** Manually compile, curate, and cross-reference all BIS standards data from official Bureau of Indian Standards portals (e.g., Manakonline, BIS Standards Publishing division).
- **Integrity Rule:** No standard number, year of publication, scope summary, or parameter table will be populated by unvetted generative LLM hallucination. Every entry in [`data/`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/data) is verified by human team members against official gazettes or BIS catalogs.

### B. Regulatory Source Verification & QCO Tracking
- **Human Action:** Systematically track and verify Quality Control Orders (QCOs) published by Indian government line ministries (e.g., Department for Promotion of Industry and Internal Trade - DPIIT, Ministry of Steel, Ministry of Electronics and Information Technology - MeitY).
- **Integrity Rule:** Statutory deadlines, compulsory ISI mark mandates, and exemption clauses are transcribed from original Gazette notifications.

### C. Deterministic Validation Rule Definition
- **Human Action:** Formulate and code the deterministic rule logic for:
  - Identifying superseded standards and their direct replacements.
  - Flagging missing mandatory test standards.
  - Parameter range and tolerance matching algorithms.
  - Severity classification (Critical vs. Warning vs. Informational).

### D. Test Case & Fixture Design
- **Human Action:** Author realistic, diverse tender specifications in [`demo/`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/demo) representing real-world procurement challenges:
  - Tenders citing superseded or withdrawn standards.
  - Tenders omitting mandatory QCO compliance clauses.
  - Tenders specifying conflicting or physically impossible material parameters.
  - Well-formed tenders to verify zero false-positive alerts.

### E. Human Review of AI Outputs
- **Human Action:** Implement review benchmarks and evaluation rubrics to assess LLM parameter extraction accuracy and retrieval precision.
- **Integrity Rule:** In production or demonstration, LLM-generated recommendations must present underlying textual evidence and citations for human officer sign-off.

### F. Product Requirements & Scope Decision-Making
- **Human Action:** Sole responsibility for defining project scope, user journeys, contract schemas, UI wireframes, and prioritization of features (Must vs. Should vs. Skip).

### G. End-to-End Validation of the Live Demonstration
- **Human Action:** Conduct rigorous dry runs of the end-to-end user flow: uploading sample tenders, validating extracted parameters against ground truth, verifying graph expansions, and confirming report reproducibility.

### H. Architectural & Technical Defense During Judging
- **Human Action:** Deeply understand and independently defend all technical choices during hackathon evaluation:
  - Explaining the hybrid retrieval architecture (BGE-M3 + BM25 + Cross-Encoder).
  - Justifying why a deterministic rule engine is mandatory over a raw generative chatbot.
  - Demonstrating data lineage, schema integrity, and audit traceability.

---

## 3. Summary Table: AI vs. Human Role Boundary

| Area | Human Role | AI / Model Role |
| :--- | :--- | :--- |
| **Standards Data** | Curates, verifies against BIS portal & Gazette | None (zero fabrication allowed) |
| **QCO Database** | Verifies legal notifications & effective dates | None (zero fabrication allowed) |
| **Tender Understanding** | Designs extraction prompts & target schemas | Parses complex unstructured tender text into structured JSON |
| **Search & Retrieval** | Configures hybrid weights, indexes & filters | Computes dense vector similarities & BM25 keyword rankings |
| **Compliance Logic** | Defines logic rules, status transitions & bounds | Executes deterministic code according to human-written rules |
| **Explanations** | Formats templates, audits clarity | Drafts plain-language summary based on ground-truth evidence |
| **Final Evaluation** | Procurement officer retains full authority | Advisory decision support engine |
