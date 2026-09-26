# MAANAKNETRA - Verified Prototype Dataset & Source Provenance
**Domain:** Government Procurement of Openwell & Submersible Pumpsets
**Smart India Hackathon 2026 | Problem Statement SIH26108**

---

## 1. Provenance Policy & Human Curation Methodology

MAANAKNETRA enforces an absolute zero-tolerance policy against hallucinated standards, fictitious dates, or speculative regulatory conclusions. Every data point in this repository originates from official government sources:
- **Bureau of Indian Standards (BIS):** Standards Publishing Division, Sectional Committees MED 20 (Pumps) and ETD 15 (Rotating Electrical Machinery).
- **BIS Product Manuals (PM):** Conformity assessment and scheme of inspection documents issued by the Central Marks Department.
- **BIS Laboratory Information Management System (LIMS):** Scope lists and test method directories.
- **The Gazette of India:** Statutory Quality Control Orders published by the Department for Promotion of Industry and Internal Trade (DPIIT) and the Ministry of Heavy Industries (MHI).

---

## 2. Three-Tiered Data Certainty Framework

To maintain complete intellectual honesty during hackathon judging and technical auditing, all dataset entities are categorized under three distinct certainty tiers:

### Tier 1: VERIFIED FACT
*Items backed by explicit, published Gazette notifications, active BIS standards, or current Product Manuals.*
- **`IS 14220:2018` (First Revision):** Active standard for openwell submersible pumpsets up to 45 kW; supersedes `IS 14220:1994`. Tested according to `IS 11346`.
- **`IS 8034:2018` (Third Revision):** Active standard for borehole submersible pumpsets; supersedes `IS 8034:2002`. Casing hydrostatic test pressure is 1.5x shut-off head or 2.0 bar min.
- **`IS 9283:2024` (Third Revision):** Active standard for line-operated AC motors for submersible pumpsets; supersedes `IS 9283:2013`. High voltage test is 1000V + 2xUn (1500V min).
- **`IS 9079:2018` (Third Revision):** Active standard for monoset pumps for clear, cold water; supersedes `IS 9079:2002`.
- **`IS 6595 (Part 1):2018` (Third Revision):** Active standard for horizontal centrifugal pumps for agricultural and rural water supply.
- **`IS 8472:2019` (Second Revision):** Active standard for centrifugal regenerative pumps.
- **`Pumps (Quality Control) Order, 2023` (S.O. 4333(E)):** Statutory order by DPIIT mandating compulsory ISI mark under Scheme I for IS 14220, IS 8034, IS 9079, and IS 6595 (Part 1).
- **`Energy Efficient Induction Motors QCO, 2017` (S.O. 167(E)):** Statutory order mandating minimum IE2 efficiency and ISI mark on line-operated three-phase surface induction motors under `IS 12615`.

### Tier 2: PENDING VERIFICATION
*Items where official evidence exists, but specific regulatory transition deadlines or cross-applicability rulings require formal human determination.*
- **`IS 996` Active Enforcement Cut-off:** Fourth Revision (`IS 996:2009`) is confirmed on the BIS portal; however, Sectional Committee ETD 15 has circulated newer draft revisions. The exact statutory date when the 2009 version ceases concurrent enforcement requires Gazette confirmation.
- **MSME Phased Enforcement Dates for Pumps QCO 2023:** The parent order `S.O. 4333(E)` is fully verified. Subsequent DPIIT Transition Facilitation Orders provide tiered grace periods for Micro and Small Enterprises; tender linter rules must verify bidder enterprise size before issuing fatal non-compliance flags.
- **`IS 9283:2024` Grace Period Discretion:** The standard was published in 2024. While BIS frequently allows a 12-month dual-running period for existing manufacturing licensees, public procurement tenders have discretion on whether to accept `IS 9283:2013` during the transition.
- **Cross-Applicability of `IS 12615` to Wet Submersible Motors:** Submersible motors are designed to run fully submerged in water/oil and are governed by `IS 9283`. Standard `IS 12615` (and its mandatory QCO `S.O. 167(E)`) covers standard air-cooled surface induction motors. Automatically penalizing a submersible pumpset tender for omitting an `IS 12615 IE2` clause remains `PENDING_VERIFICATION` to prevent false-positive audit findings.

### Tier 3: PROTOTYPE SIMPLIFICATION
*Intentional technical abstractions made for prototype modeling without misrepresenting regulatory facts.*
- **Non-Scalar Efficiency Curves (`IS 14220` Table 1):** In reality, guaranteed efficiency in IS 14220 is a continuous function of operating head (H) and flow rate (Q). To avoid encoding an inaccurate universal fixed cutoff (e.g. 35%), the scalar numeric limit is set to `null` and flagged as duty-point dependent.
- **Focused Domain Scope:** The initial catalog focuses in depth on 8 representative pump and motor standards rather than superficially covering thousands of unverified codes.

---

## 3. Direct Official Source URL Mapping

Generic homepage URLs have been replaced with direct official document references:

| Standard / Order | Old Stored Reference | Direct Official Publication URL |
| :--- | :--- | :--- |
| **IS 14220:2018** | Generic BIS Portal | `https://www.bis.gov.in/wp-content/uploads/2024/07/PM-IS-14220.pdf` |
| **IS 8034:2018** | Generic BIS Portal | `https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/indian_standards/isdetails?is_no=IS+8034` |
| **IS 9283:2024** | Generic LIMS Portal | `https://lims.bis.gov.in/` (Scope directory: IS 9283 ETD 15) |
| **IS 9079:2018** | Generic BIS Portal | `https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/indian_standards/isdetails?is_no=IS+9079` |
| **IS 6595 (Part 1)** | Generic BIS Portal | `https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/indian_standards/isdetails?is_no=IS+6595+%28Part+1%29` |
| **IS 8472:2019** | Generic BIS Portal | `https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/indian_standards/isdetails?is_no=IS+8472` |
| **IS 996** | Generic BIS Portal | `https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/indian_standards/isdetails?is_no=IS+996` |
| **IS 12615:2018** | Generic DPIIT Portal | `https://dpiit.gov.in/sites/default/files/Order_Motors_18Jan2017.pdf` |
| **QCO Pumps 2023** | Generic DPIIT Portal | `https://dpiit.gov.in/sites/default/files/QCO_Pumps_06October2023.pdf` |
| **QCO Motors 2017** | Generic DPIIT Portal | `https://dpiit.gov.in/sites/default/files/Order_Motors_18Jan2017.pdf` |

---

## 4. Dataset Coverage Metrics

| Metric | Count | Details |
| :--- | :---: | :--- |
| **Total Standard Records** | **9** | 8 primary pump/motor codes + 1 historical superseded record (`IS 14220:1994`) |
| **Total Relationship Edges** | **14** | Verified edges (`NORMATIVE_REFERENCE`, `TEST_METHOD`, `SUPERSEDED_BY`, `ALLIED_STANDARD`) |
| **Total Status Records** | **11** | Currency, revisions, and supersession tracking |
| **Total QCO Records** | **2** | Statutory Quality Control Orders (`S.O. 4333(E)` and `S.O. 167(E)`) |
| **Verified Official Standards** | **8** | Confirmed against official BIS Product Manuals and Gazette orders |
| **Pending Verification Standards** | **1** | `IS 996` (Concurrent validity transition date pending Gazette bulletin) |
