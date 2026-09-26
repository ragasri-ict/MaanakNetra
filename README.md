# MAANAKNETRA (मानक नेत्र)
### AI-Powered Procurement & Indian Standards Intelligence Engine
**Smart India Hackathon 2026 | Problem Statement SIH26108**

---

## 🎯 Executive Summary
**MAANAKNETRA** is an intelligent, auditable compliance and verification engine built specifically for Indian public and enterprise procurement officers. When a procurement officer uploads an equipment or material tender specification, MAANAKNETRA extracts technical parameters, identifies applicable Bureau of Indian Standards (BIS) standards, performs parameter-level compliance verification, highlights mandatory Quality Control Orders (QCOs), detects superseded/withdrawn standards, and produces an auditable, corrected specification.

> **Core Philosophy:**
> - **LLM for Document Understanding:** Unstructured tender extraction, semantic matching, and plain-language explanation.
> - **Deterministic Rules for Compliance:** Grounded strictly in verified, structured standards databases and regulatory registries. Zero hallucinated standards, zero fabricated QCO dates.

---

## 🏗️ Repository Structure

```
MAANAKNETRA/
├── frontend/             # React + TypeScript + Tailwind UI
├── backend/              # FastAPI Python service & REST endpoints
├── ai/                   # Extraction, Hybrid Search (BGE-M3 + BM25), Cross-Encoder
├── data/                 # Curated BIS standards dataset, QCO registry, graph data
├── contracts/            # JSON Schemas defining API data models & boundaries
├── demo/                 # Sample tender specs and test fixtures for live demonstration
└── docs/                 # Architectural specifications, scope, and governance
```

---

## 📋 Documentation Quick Links
- **[Product Scope](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/docs/PRODUCT_SCOPE.md):** User personas, workflow, Must/Should/Skip features.
- **[System Architecture](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/docs/ARCHITECTURE.md):** Tech stack, hybrid retrieval, graph expansion, and determinism boundary.
- **[Human-in-the-Loop & Governance](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/docs/HUMAN_CONTRIBUTION.md):** Curation protocol, manual validation, and judging transparency.

---

## 📜 Data Contracts (JSON Schemas)
- [`requirements.schema.json`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/contracts/requirements.schema.json): Extracted tender parameter schema.
- [`standard.schema.json`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/contracts/standard.schema.json): Indian Standard structured representation.
- [`finding.schema.json`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/contracts/finding.schema.json): Audit finding & discrepancy schema.
- [`analysis.schema.json`](file:///c:/Users/Lenovo/OneDrive/Attachments/MaanakNetraOG/contracts/analysis.schema.json): Comprehensive tender audit result contract.

---

## 🛡️ Anti-Hallucination Guardrails
1. **Never fabricate standards:** Standards referenced must exist in the curated standard database.
2. **Never invent regulatory statuses:** Active, superseded, withdrawn, and QCO status are verified against verified gazette/BIS records.
3. **Traceability:** Every finding must provide an exact citation, parameter clause, or regulatory rule ID.
