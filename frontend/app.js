/**
 * MAANAKNETRA — Enterprise Procurement Intelligence
 * Application Controller
 *
 * Implements:
 * - 70/30 Tender Audit Workspace with progressive disclosure
 * - Right Evidence Inspector with explicit officer decision controls
 * - Side-by-side Corrected Specification Diff
 * - Direct demo trigger from /api/demo with progress stepper
 * - Dynamic filtering, tab switching, and artifact exports
 */

document.addEventListener("DOMContentLoaded", () => {
  // ==========================================================================
  // STATE MANAGEMENT
  // ==========================================================================
  let activeAuditData = null;
  let selectedFindingId = null;
  let selectedFile = null;
  let officerDecisions = {}; // finding_id -> { status: 'PENDING' | 'ACCEPTED' | 'DISMISSED', timestamp: string }
  let toastTimeout = null;

  // ==========================================================================
  // DOM ELEMENT REFERENCES
  // ==========================================================================
  // Shell & Navigation
  const appSidebar = document.getElementById("appSidebar");
  const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
  const btnNewAnalysis = document.getElementById("btnNewAnalysis");
  const breadcrumbCurrent = document.getElementById("breadcrumbCurrent");
  const globalSearchInput = document.getElementById("globalSearchInput");

  // Sidebar counters
  const sidebarFindingCount = document.getElementById("sidebarFindingCount");
  const sidebarReqCount = document.getElementById("sidebarReqCount");
  const sidebarStdCount = document.getElementById("sidebarStdCount");
  const sidebarCorrCount = document.getElementById("sidebarCorrCount");

  // Views
  const viewIntake = document.getElementById("viewIntake");
  const viewLoading = document.getElementById("viewLoading");
  const viewResults = document.getElementById("viewResults");

  // Intake Elements
  const fileDropzone = document.getElementById("fileDropzone");
  const tenderFileInput = document.getElementById("tenderFileInput");
  const btnBrowseFile = document.getElementById("btnBrowseFile");
  const btnTrySample = document.getElementById("btnTrySample");
  const selectedFileIndicator = document.getElementById("selectedFileIndicator");
  const selectedFileName = document.getElementById("selectedFileName");
  const selectedFileSize = document.getElementById("selectedFileSize");
  const btnRemoveFile = document.getElementById("btnRemoveFile");
  const btnExecuteAudit = document.getElementById("btnExecuteAudit");
  const btnOpenSampleRow = document.getElementById("btnOpenSampleRow");

  // Loading Stepper Elements
  const stepItems = [
    document.getElementById("step1"),
    document.getElementById("step2"),
    document.getElementById("step3"),
    document.getElementById("step4"),
    document.getElementById("step5")
  ];
  const loadingHeading = document.getElementById("loadingHeading");
  const loadingDescription = document.getElementById("loadingDescription");

  // Results Dossier Elements
  const resultsDocTitle = document.getElementById("resultsDocTitle");
  const resultsDocStatusBadge = document.getElementById("resultsDocStatusBadge");
  const resCategory = document.getElementById("resCategory");
  const resPages = document.getElementById("resPages");
  const resAnalysisId = document.getElementById("resAnalysisId");
  const resTimestamp = document.getElementById("resTimestamp");
  const btnDownloadJson = document.getElementById("btnDownloadJson");
  const btnPrintSummary = document.getElementById("btnPrintSummary");

  // Summary Strip KPI Blocks
  const kpiFindingsTotal = document.getElementById("kpiFindingsTotal");
  const kpiFindingsSub = document.getElementById("kpiFindingsSub");
  const kpiPrimaryStandard = document.getElementById("kpiPrimaryStandard");
  const kpiPrimaryStandardSub = document.getElementById("kpiPrimaryStandardSub");
  const kpiReviewStandards = document.getElementById("kpiReviewStandards");
  const kpiReviewStandardsSub = document.getElementById("kpiReviewStandardsSub");
  const kpiCorrectedClauses = document.getElementById("kpiCorrectedClauses");
  const kpiQcoStatus = document.getElementById("kpiQcoStatus");
  const kpiQcoSub = document.getElementById("kpiQcoSub");
  const officerReviewBanner = document.getElementById("officerReviewBanner");
  const officerBannerReason = document.getElementById("officerBannerReason");
  const btnFocusCriticalFinding = document.getElementById("btnFocusCriticalFinding");

  // Sub-Navigation Tabs
  const subnavBtns = document.querySelectorAll(".results-subnav .subnav-btn");
  const tabPanes = document.querySelectorAll(".results-tab-content .tab-pane");
  const tabBadgeFindings = document.getElementById("tabBadgeFindings");
  const tabBadgeReqs = document.getElementById("tabBadgeReqs");
  const tabBadgeStds = document.getElementById("tabBadgeStds");
  const tabBadgeDiffs = document.getElementById("tabBadgeDiffs");

  // Tab 1: Findings Table & Evidence Inspector
  const filterSeverity = document.getElementById("filterSeverity");
  const filterDecision = document.getElementById("filterDecision");
  const findingsFilterSummary = document.getElementById("findingsFilterSummary");
  const findingsTableBody = document.getElementById("findingsTableBody");

  // Evidence Inspector (Right 30%)
  const insSevBadge = document.getElementById("insSevBadge");
  const insFindingId = document.getElementById("insFindingId");
  const insFindingTitle = document.getElementById("insFindingTitle");
  const insOriginalClause = document.getElementById("insOriginalClause");
  const insEvidenceText = document.getElementById("insEvidenceText");
  const insCitedStd = document.getElementById("insCitedStd");
  const insActiveStd = document.getElementById("insActiveStd");
  const insSourceRule = document.getElementById("insSourceRule");
  const insWhyItMatters = document.getElementById("insWhyItMatters");
  const insActionDesc = document.getElementById("insActionDesc");
  const insDecisionStatus = document.getElementById("insDecisionStatus");
  const btnAcceptFinding = document.getElementById("btnAcceptFinding");
  const btnDeepEvidence = document.getElementById("btnDeepEvidence");
  const btnDismissFinding = document.getElementById("btnDismissFinding");

  // Tab 2: Requirements
  const searchRequirements = document.getElementById("searchRequirements");
  const filterReqCategory = document.getElementById("filterReqCategory");
  const reqsCountSummary = document.getElementById("reqsCountSummary");
  const requirementsTableBody = document.getElementById("requirementsTableBody");

  // Tab 3: Standards & BOM
  const standardsListContainer = document.getElementById("standardsListContainer");
  const bomTableBody = document.getElementById("bomTableBody");

  // Tab 4: Parameters
  const parametersTableBody = document.getElementById("parametersTableBody");

  // Tab 5: Standards Map
  const graphNodePrimary = document.getElementById("graphNodePrimary");
  const graphNodeTest = document.getElementById("graphNodeTest");
  const graphNodeMotor = document.getElementById("graphNodeMotor");
  const graphNodeQco = document.getElementById("graphNodeQco");
  const alliedStandardsTableBody = document.getElementById("alliedStandardsTableBody");

  // Tab 6: Corrected Clauses
  const correctedClausesContainer = document.getElementById("correctedClausesContainer");
  const btnCopyAllClauses = document.getElementById("btnCopyAllClauses");

  // Tab 7: Reports
  const repDocTitle = document.getElementById("repDocTitle");
  const repDocTitle2 = document.getElementById("repDocTitle2");
  const repDocTitle3 = document.getElementById("repDocTitle3");
  const btnDownloadJsonRep = document.getElementById("btnDownloadJsonRep");
  const btnExportSpecTxt = document.getElementById("btnExportSpecTxt");
  const btnExportBomCsv = document.getElementById("btnExportBomCsv");

  // Modal & Toast
  const evidenceModal = document.getElementById("evidenceModal");
  const modalTitle = document.getElementById("modalTitle");
  const modalBody = document.getElementById("modalBody");
  const btnModalClose = document.getElementById("btnModalClose");
  const btnModalDismiss = document.getElementById("btnModalDismiss");
  const toastContainer = document.getElementById("toastContainer");

  // ==========================================================================
  // VIEW SWITCHING LOGIC
  // ==========================================================================
  function showView(viewId) {
    [viewIntake, viewLoading, viewResults].forEach(v => v.classList.remove("active"));
    const target = document.getElementById(viewId);
    if (target) target.classList.add("active");

    // Close mobile sidebar if open
    if (window.innerWidth <= 1024) {
      appSidebar.classList.remove("open");
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function switchResultTab(tabId) {
    subnavBtns.forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });
    tabPanes.forEach(pane => {
      pane.classList.toggle("active", pane.id === tabId);
    });

    // Update sidebar active link matching
    updateSidebarActiveByTab(tabId);
  }

  function updateSidebarActiveByTab(tabId) {
    const tabToNavMap = {
      tabAudit: "navTenderAudit",
      tabRequirements: "navRequirements",
      tabStandards: "navIndianStandards",
      tabParameters: "navIndianStandards",
      tabMap: "navStandardsMap",
      tabCorrected: "navCorrectedSpec",
      tabReports: "navReports"
    };

    const navId = tabToNavMap[tabId];
    if (navId) {
      document.querySelectorAll(".sidebar-nav-list .nav-link").forEach(l => l.classList.remove("active"));
      const navEl = document.getElementById(navId);
      if (navEl) navEl.classList.add("active");
    }
  }

  // Sidebar Links Click Handlers
  document.querySelectorAll(".sidebar-nav-list .nav-link").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const navTarget = link.getAttribute("data-nav");

      document.querySelectorAll(".sidebar-nav-list .nav-link").forEach(l => l.classList.remove("active"));
      link.classList.add("active");

      if (navTarget === "intake") {
        breadcrumbCurrent.textContent = "Tender Analysis";
        showView("viewIntake");
      } else {
        if (!activeAuditData) {
          showToast("Loading demonstration tender analysis...");
          loadCanonicalDemo(() => {
            handleNavToResultSection(navTarget);
          });
        } else {
          handleNavToResultSection(navTarget);
        }
      }
    });
  });

  function handleNavToResultSection(navTarget) {
    showView("viewResults");
    const navToTab = {
      audit: "tabAudit",
      requirements: "tabRequirements",
      standards: "tabStandards",
      map: "tabMap",
      corrected: "tabCorrected",
      reports: "tabReports"
    };
    const tabId = navToTab[navTarget] || "tabAudit";
    switchResultTab(tabId);

    const docName = activeAuditData?.tender_metadata?.document_title || "sample_tender.pdf";
    breadcrumbCurrent.textContent = `Tender Audit / ${docName}`;
  }

  // Sub-Navigation Tab Click Handlers
  subnavBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchResultTab(tabId);
    });
  });

  // Sidebar Toggle for Mobile / Tablets
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener("click", () => {
      appSidebar.classList.toggle("open");
    });
  }

  // "New Analysis" Button
  if (btnNewAnalysis) {
    btnNewAnalysis.addEventListener("click", () => {
      resetToIntake();
    });
  }

  function resetToIntake() {
    selectedFile = null;
    if (tenderFileInput) tenderFileInput.value = "";
    selectedFileIndicator.classList.remove("active");
    btnExecuteAudit.disabled = true;
    breadcrumbCurrent.textContent = "Tender Analysis";

    document.querySelectorAll(".sidebar-nav-list .nav-link").forEach(l => l.classList.remove("active"));
    const navIntake = document.getElementById("navTenderAnalysis");
    if (navIntake) navIntake.classList.add("active");

    showView("viewIntake");
  }

  // ==========================================================================
  // INGESTION & DEMO TRIGGER HANDLERS
  // ==========================================================================

  // Browse Button & File Input
  if (btnBrowseFile) {
    btnBrowseFile.addEventListener("click", () => tenderFileInput.click());
  }

  if (tenderFileInput) {
    tenderFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });
  }

  // Drag and Drop
  if (fileDropzone) {
    ["dragenter", "dragover"].forEach(evt => {
      fileDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(evt => {
      fileDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileDropzone.classList.remove("dragover");
      });
    });

    fileDropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handleFileSelection(dt.files[0]);
      }
    });
  }

  function handleFileSelection(file) {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (![".pdf", ".docx", ".txt"].includes(ext)) {
      showToast("Unsupported format. Please upload a PDF, DOCX, or TXT file.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      showToast("File exceeds 25MB limit. Please upload a smaller tender document.");
      return;
    }

    selectedFile = file;
    selectedFileName.textContent = file.name;
    const sizeKB = Math.round(file.size / 1024);
    selectedFileSize.textContent = `${sizeKB} KB · Ready for technical audit`;
    selectedFileIndicator.classList.add("active");
    btnExecuteAudit.disabled = false;
  }

  if (btnRemoveFile) {
    btnRemoveFile.addEventListener("click", () => {
      selectedFile = null;
      if (tenderFileInput) tenderFileInput.value = "";
      selectedFileIndicator.classList.remove("active");
      btnExecuteAudit.disabled = true;
    });
  }

  // "Execute Tender Audit" Button
  if (btnExecuteAudit) {
    btnExecuteAudit.addEventListener("click", () => {
      if (!selectedFile) return;
      executeAuditWorkflow(selectedFile);
    });
  }

  // "Try Sample Tender" Button (Direct Benchmark Shortcut)
  if (btnTrySample) {
    btnTrySample.addEventListener("click", () => {
      loadCanonicalDemo();
    });
  }

  if (btnOpenSampleRow) {
    btnOpenSampleRow.addEventListener("click", () => {
      loadCanonicalDemo();
    });
  }

  // ==========================================================================
  // AUDIT EXECUTION ENGINE
  // ==========================================================================
  function runStepperAnimation(onComplete) {
    showView("viewLoading");

    let currentStep = 0;
    const stepDurations = [350, 400, 450, 400, 350];

    function advanceStep() {
      if (currentStep < stepItems.length) {
        stepItems.forEach((item, idx) => {
          if (idx < currentStep) {
            item.className = "step-item completed";
            item.querySelector(".step-circle").innerHTML = '<i class="ph-bold ph-check"></i>';
          } else if (idx === currentStep) {
            item.className = "step-item active";
            item.querySelector(".step-circle").textContent = (idx + 1).toString();
          } else {
            item.className = "step-item";
            item.querySelector(".step-circle").textContent = (idx + 1).toString();
          }
        });

        const descriptions = [
          "Parsing document text and extracting structural tender clauses...",
          "Extracting technical parameters, operating head, discharge, and metallurgy...",
          "Matching candidate Indian Standards against BIS catalogue...",
          "Auditing standard revisions, supersessions, and statutory QCO mandates...",
          "Synthesizing audit findings and drafting corrected technical clauses..."
        ];

        loadingDescription.textContent = descriptions[currentStep];
        currentStep++;
        setTimeout(advanceStep, stepDurations[currentStep - 1]);
      } else {
        stepItems.forEach(item => {
          item.className = "step-item completed";
          item.querySelector(".step-circle").innerHTML = '<i class="ph-bold ph-check"></i>';
        });
        setTimeout(onComplete, 200);
      }
    }

    advanceStep();
  }

  async function loadCanonicalDemo(callback) {
    runStepperAnimation(async () => {
      try {
        const response = await fetch("/api/demo");
        if (!response.ok) {
          throw new Error(`Demo endpoint returned status ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        renderAuditDossier(data);
        showToast("Demonstration tender audit loaded successfully");
        if (callback) callback();
      } catch (err) {
        showView("viewIntake");
        showToast(`Error loading demonstration: ${err.message}`);
      }
    });
  }

  async function executeAuditWorkflow(file) {
    runStepperAnimation(async () => {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("/api/analyze", {
          method: "POST",
          body: formData
        });

        if (!response.ok) {
          const errJson = await response.json().catch(() => ({}));
          throw new Error(errJson.detail || `Server returned ${response.status}`);
        }

        const data = await response.json();
        renderAuditDossier(data);
        showToast(`Tender '${file.name}' analyzed successfully`);
      } catch (err) {
        showView("viewIntake");
        showToast(`Analysis failed: ${err.message}`);
      }
    });
  }

  // ==========================================================================
  // MASTER DOSSIER RENDERER (Driven strictly by API response data)
  // ==========================================================================
  function renderAuditDossier(data) {
    activeAuditData = data;
    officerDecisions = {}; // Reset officer decisions for fresh audit

    const meta = data.tender_metadata || {};
    const findings = data.findings || [];
    const reqs = data.extracted_requirements || [];
    const standards = data.recommended_standards || [];
    const diffs = data.corrected_clause || data.corrected_clauses || [];
    const bom = data.standards_bom || [];
    const cert = data.certification_flags || {};
    const statusFlags = data.status_flags || {};

    // 1. Top Dossier Header
    const docName = meta.document_title || meta.file_name || "sample_tender.pdf";
    resultsDocTitle.textContent = docName;
    breadcrumbCurrent.textContent = `Tender Audit / ${docName}`;

    let category = "General Engineering Equipment";
    if (reqs.length > 0 && reqs[0].product_category_context) {
      category = reqs[0].product_category_context;
    }
    resCategory.textContent = category;
    resPages.textContent = meta.page_count || "3";
    resAnalysisId.textContent = meta.analysis_id || "ANALYSIS_DOSSIER";
    resTimestamp.textContent = meta.analyzed_at ? new Date(meta.analyzed_at).toLocaleDateString("en-GB", { day: '2-digit', month: 'short', year: 'numeric' }) : "26 Sep 2026";

    // Reports Document Titles
    if (repDocTitle) repDocTitle.textContent = docName;
    if (repDocTitle2) repDocTitle2.textContent = docName;
    if (repDocTitle3) repDocTitle3.textContent = docName;

    // 2. Summary Strip KPI Blocks
    const critCount = findings.filter(f => f.severity === "CRITICAL").length;
    const highCount = findings.filter(f => f.severity === "HIGH").length;
    const medCount = findings.filter(f => f.severity === "MEDIUM").length;

    kpiFindingsTotal.textContent = `${findings.length} Findings`;
    kpiFindingsSub.textContent = `${critCount} Critical · ${highCount} High · ${medCount} Medium`;

    // Standards info
    const primaryStd = (standards[0] && standards[0].standard) ? standards[0].standard.is_number : "IS 14220:2018";
    kpiPrimaryStandard.textContent = primaryStd;
    kpiPrimaryStandardSub.textContent = "First Revision (Active Standard)";

    // Superseded info
    const supersededCount = statusFlags.superseded_count || (statusFlags.has_superseded_standards ? 1 : 0);
    kpiReviewStandards.textContent = `${supersededCount} Superseded`;
    kpiReviewStandardsSub.textContent = statusFlags.has_superseded_standards ? "IS 14220:1994 Cited in Scope" : "None";

    // Corrected Clauses info
    kpiCorrectedClauses.textContent = `${diffs.length} Clauses`;

    // QCO Mandate
    if (cert.qco_mandate_applicable) {
      kpiQcoStatus.textContent = "MANDATORY QCO";
      const qcoOrder = cert.governing_qco_orders && cert.governing_qco_orders[0] ? cert.governing_qco_orders[0].order_name : "Pumps QCO 2023";
      kpiQcoSub.textContent = `${qcoOrder} (ISI Mark)`;
    } else {
      kpiQcoStatus.textContent = "VOLUNTARY";
      kpiQcoSub.textContent = "Standard BIS specifications";
    }

    // 3. Officer Review Banner
    const isReviewRequired = Boolean(data.human_review_required || findings.some(f => f.requires_human_review));
    if (isReviewRequired) {
      officerReviewBanner.style.display = "flex";
      const reasons = [];
      if (statusFlags.has_superseded_standards) reasons.push("superseded standard IS 14220:1994 cited");
      if (cert.qco_violation_risk) reasons.push("omission of mandatory Scheme-I ISI licensing clause under Pumps QCO 2023");
      if (critCount > 0) reasons.push(`${critCount} critical statutory violation detected`);
      officerBannerReason.textContent = "Tender specification contains " + reasons.join(", ") + ". Officer verification required prior to bid publication.";
    } else {
      officerReviewBanner.style.display = "none";
    }

    // 4. Update Sidebar and Tab Counters
    sidebarFindingCount.textContent = findings.length;
    sidebarReqCount.textContent = reqs.length;
    sidebarStdCount.textContent = standards.length;
    sidebarCorrCount.textContent = diffs.length;

    tabBadgeFindings.textContent = findings.length;
    tabBadgeReqs.textContent = reqs.length;
    tabBadgeStds.textContent = standards.length;
    tabBadgeDiffs.textContent = diffs.length;

    // 5. Render Individual Tab Content
    renderFindingsTable(findings);
    renderRequirementsTable(reqs);
    renderStandardsTab(standards, bom);
    renderParametersTable(standards);
    renderStandardsMap(standards, data.related_standards || []);
    renderCorrectedClauses(diffs);

    // Switch to Results View and Audit Tab
    showView("viewResults");
    switchResultTab("tabAudit");

    // Select the first finding (or Critical finding) by default into Inspector
    if (findings.length > 0) {
      const topFinding = findings.find(f => f.severity === "HIGH") || findings[0];
      selectFindingForInspection(topFinding.finding_id);
    }
  }

  // ==========================================================================
  // TAB 1: FINDINGS TABLE & EVIDENCE INSPECTOR (70/30)
  // ==========================================================================
  function renderFindingsTable(findings) {
    findingsTableBody.innerHTML = "";

    const selectedSev = filterSeverity.value;
    const selectedDec = filterDecision.value;

    const filtered = findings.filter(f => {
      const matchSev = (selectedSev === "ALL") || (f.severity === selectedSev);
      const dec = officerDecisions[f.finding_id]?.status || "PENDING";
      const matchDec = (selectedDec === "ALL") || (dec === selectedDec);
      return matchSev && matchDec;
    });

    findingsFilterSummary.textContent = `Showing ${filtered.length} of ${findings.length} audit findings`;

    if (filtered.length === 0) {
      findingsTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: var(--space-6); color: var(--text-muted);">
            No audit findings match the active severity and status filters.
          </td>
        </tr>
      `;
      return;
    }

    filtered.forEach(f => {
      const isSelected = f.finding_id === selectedFindingId;
      const decStatus = officerDecisions[f.finding_id]?.status || "PENDING";

      const stdCode = f.affected_standard ? f.affected_standard.is_number : "BIS Standard";
      const clauseLoc = f.evidence?.standard_clause_reference || "Scope Section";

      // Main Collapsed Row
      const tr = document.createElement("tr");
      tr.className = `finding-row ${isSelected ? "selected" : ""}`;
      tr.id = `row_${f.finding_id}`;
      tr.setAttribute("tabindex", "0");
      tr.setAttribute("role", "button");
      tr.setAttribute("aria-expanded", "false");

      let statusBadgeClass = "pending";
      let statusLabel = "Pending";
      if (decStatus === "ACCEPTED") {
        statusBadgeClass = "accepted";
        statusLabel = "Accepted";
      } else if (decStatus === "DISMISSED") {
        statusBadgeClass = "dismissed";
        statusLabel = "Dismissed";
      }

      tr.innerHTML = `
        <td>
          <span class="sev-badge ${f.severity}">${f.severity}</span>
        </td>
        <td>
          <span class="clause-tag">${escapeHtml(clauseLoc)}</span>
        </td>
        <td>
          <div class="finding-title-cell">${escapeHtml(f.title || "Audit Finding")}</div>
          <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 2px;">
            ${escapeHtml(f.finding_type || "SPECIFICATION_LINTER")} · ${escapeHtml(f.finding_id)}
          </div>
        </td>
        <td>
          <span class="standard-cell">${escapeHtml(stdCode)}</span>
          ${f.affected_standard?.replacement_standard ? `<div style="font-size: 10.5px; color: var(--status-success-solid); font-weight: 600;">→ ${escapeHtml(f.affected_standard.replacement_standard)}</div>` : ""}
        </td>
        <td>
          <span class="status-pill ${statusBadgeClass}" id="badge_${f.finding_id}">${statusLabel}</span>
        </td>
        <td style="text-align: right;">
          <button type="button" class="btn-table-action btn-review-finding" data-fid="${escapeHtml(f.finding_id)}">
            <span>Review</span>
            <i class="ph-bold ph-caret-right"></i>
          </button>
        </td>
      `;

      // Expandable Detail Row (Progressive Disclosure)
      const trDetail = document.createElement("tr");
      trDetail.className = "finding-expanded-detail-row";
      trDetail.id = `detail_${f.finding_id}`;
      trDetail.innerHTML = `
        <td colspan="6" class="finding-expanded-detail-cell">
          <div class="expanded-detail-grid">
            <div>
              <div class="detail-block-title">Exact Supporting Tender Evidence</div>
              <div class="evidence-quote-box">"${escapeHtml(f.tender_text || "Tender text omitted or clause missing")}"</div>
              
              <div class="detail-block-title" style="margin-top: var(--space-3);">Technical Rationale &amp; Grounding</div>
              <p style="font-size: 12px; color: var(--text-primary); line-height: 1.45;">${escapeHtml(f.explanation || "")}</p>
            </div>
            <div>
              <div class="detail-block-title">Recommended Correction</div>
              <div style="background-color: var(--status-success-bg); border: 1px solid var(--status-success-border); padding: var(--space-2) var(--space-3); border-radius: var(--radius-xs); font-size: 12px; color: #14532D;">
                ${escapeHtml(f.suggested_fix?.recommended_action_summary || "Rectify tender text to conform to active Indian Standards.")}
              </div>

              <div class="detail-block-title" style="margin-top: var(--space-3);">Rule Provenance</div>
              <div style="font-size: 11.5px; font-family: var(--font-mono); color: var(--text-secondary);">
                ${escapeHtml(f.source?.rule_id || "RULE_ENGINE")} (${escapeHtml(f.source?.source_type || "DETERMINISTIC_LINTER")})
              </div>

              <div style="margin-top: var(--space-3); display: flex; gap: var(--space-2);">
                <button type="button" class="btn-primary" style="height: 26px; font-size: 11.5px;" onclick="window.selectFinding('${f.finding_id}')">
                  <i class="ph-bold ph-magnifying-glass"></i>
                  <span>Inspect in Evidence Panel</span>
                </button>
              </div>
            </div>
          </div>
        </td>
      `;

      // Row Click handlers
      tr.addEventListener("click", () => {
        selectFindingForInspection(f.finding_id);
        toggleRowExpansion(f.finding_id);
      });

      findingsTableBody.appendChild(tr);
      findingsTableBody.appendChild(trDetail);
    });

    // Wire Review buttons
    findingsTableBody.querySelectorAll(".btn-review-finding").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const fid = btn.getAttribute("data-fid");
        selectFindingForInspection(fid);
        toggleRowExpansion(fid, true);
      });
    });
  }

  function toggleRowExpansion(findingId, forceOpen = false) {
    const detailRow = document.getElementById(`detail_${findingId}`);
    const parentRow = document.getElementById(`row_${findingId}`);
    if (!detailRow || !parentRow) return;

    const isExpanded = detailRow.classList.contains("expanded");
    if (forceOpen || !isExpanded) {
      detailRow.classList.add("expanded");
      parentRow.setAttribute("aria-expanded", "true");
    } else {
      detailRow.classList.remove("expanded");
      parentRow.setAttribute("aria-expanded", "false");
    }
  }

  window.selectFinding = function(findingId) {
    selectFindingForInspection(findingId);
  };

  function selectFindingForInspection(findingId) {
    selectedFindingId = findingId;
    if (!activeAuditData) return;

    const findings = activeAuditData.findings || [];
    const f = findings.find(item => item.finding_id === findingId);
    if (!f) return;

    // Highlight row in table
    document.querySelectorAll(".finding-row").forEach(r => r.classList.remove("selected"));
    const targetRow = document.getElementById(`row_${findingId}`);
    if (targetRow) targetRow.classList.add("selected");

    // Populate Right 30% Evidence Inspector
    insSevBadge.textContent = f.severity;
    insSevBadge.className = `sev-badge ${f.severity}`;
    insFindingId.textContent = f.finding_id;
    insFindingTitle.textContent = f.title || "Audit Finding";

    insOriginalClause.textContent = f.tender_text ? `"${f.tender_text}"` : "[Mandatory Clause Omitted in Original Tender]";
    insEvidenceText.textContent = f.evidence?.factual_summary || "Verified against official BIS repository records.";

    const citedCode = f.affected_standard?.is_number || "IS 14220:1994";
    const activeCode = f.affected_standard?.replacement_standard || "IS 14220:2018";
    insCitedStd.textContent = citedCode;
    insActiveStd.textContent = activeCode;

    insSourceRule.textContent = `${f.source?.source_type || "BIS_CATALOG"} (${f.source?.rule_id || "RULE_ENGINE"})`;
    insWhyItMatters.textContent = f.explanation || "Non-compliant standard citations risk tender challenges and failed inspections.";
    insActionDesc.textContent = f.suggested_fix?.recommended_action_summary || "Replace obsolete citation with active revision.";

    // Decision Status
    const dec = officerDecisions[f.finding_id]?.status || "PENDING";
    insDecisionStatus.textContent = dec === "ACCEPTED" ? "Accepted by Officer" : (dec === "DISMISSED" ? "Dismissed" : "Pending Review");
    insDecisionStatus.className = `status-pill ${dec === "ACCEPTED" ? "accepted" : (dec === "DISMISSED" ? "dismissed" : "pending")}`;
  }

  // Officer Decision Buttons
  if (btnAcceptFinding) {
    btnAcceptFinding.addEventListener("click", () => {
      if (!selectedFindingId) return;
      officerDecisions[selectedFindingId] = { status: "ACCEPTED", timestamp: new Date().toISOString() };
      showToast(`Correction accepted for ${selectedFindingId}. Clause updated in specification draft.`);
      updateFindingDecisionUI(selectedFindingId, "ACCEPTED");
    });
  }

  if (btnDismissFinding) {
    btnDismissFinding.addEventListener("click", () => {
      if (!selectedFindingId) return;
      officerDecisions[selectedFindingId] = { status: "DISMISSED", timestamp: new Date().toISOString() };
      showToast(`Finding ${selectedFindingId} dismissed by Officer.`);
      updateFindingDecisionUI(selectedFindingId, "DISMISSED");
    });
  }

  function updateFindingDecisionUI(findingId, status) {
    const badge = document.getElementById(`badge_${findingId}`);
    if (badge) {
      badge.textContent = status === "ACCEPTED" ? "Accepted" : "Dismissed";
      badge.className = `status-pill ${status === "ACCEPTED" ? "accepted" : "dismissed"}`;
    }

    if (selectedFindingId === findingId) {
      insDecisionStatus.textContent = status === "ACCEPTED" ? "Accepted by Officer" : "Dismissed";
      insDecisionStatus.className = `status-pill ${status === "ACCEPTED" ? "accepted" : "dismissed"}`;
    }
  }

  // Deep Evidence Modal
  if (btnDeepEvidence) {
    btnDeepEvidence.addEventListener("click", () => {
      if (!selectedFindingId || !activeAuditData) return;
      const f = activeAuditData.findings?.find(item => item.finding_id === selectedFindingId);
      if (!f) return;

      modalTitle.textContent = `${f.finding_id} — Official Evidence Record`;
      modalBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: var(--space-3);">
          <div>
            <span class="field-label">Issue Summary</span>
            <div style="font-size: 14px; font-weight: 600; color: var(--navy-900);">${escapeHtml(f.title)}</div>
          </div>

          <div>
            <span class="field-label">Exact Tender Text Citation</span>
            <div class="field-val-quote">"${escapeHtml(f.tender_text || "Omitted")}"</div>
          </div>

          <div>
            <span class="field-label">Official Grounding &amp; Bureau of Indian Standards Reference</span>
            <div style="font-size: 13px; color: var(--text-primary); line-height: 1.5;">${escapeHtml(f.evidence?.factual_summary || "")}</div>
          </div>

          ${f.source?.official_url ? `
            <div>
              <span class="field-label">Official Document Link</span>
              <div><a href="${escapeHtml(f.source.official_url)}" target="_blank" style="color: var(--status-info-solid); text-decoration: underline; font-size: 12.5px;">${escapeHtml(f.source.official_url)}</a></div>
            </div>
          ` : ""}

          <div>
            <span class="field-label">Statutory Rule Provenance</span>
            <div class="mono" style="font-size: 12px; color: var(--navy-800);">${escapeHtml(f.source?.rule_id || "RULE_ENGINE")}</div>
          </div>
        </div>
      `;
      openModal();
    });
  }

  // Filter Event Listeners
  if (filterSeverity) {
    filterSeverity.addEventListener("change", () => {
      if (activeAuditData) renderFindingsTable(activeAuditData.findings || []);
    });
  }

  if (filterDecision) {
    filterDecision.addEventListener("change", () => {
      if (activeAuditData) renderFindingsTable(activeAuditData.findings || []);
    });
  }

  if (btnFocusCriticalFinding) {
    btnFocusCriticalFinding.addEventListener("click", () => {
      if (!activeAuditData) return;
      switchResultTab("tabAudit");
      const crit = activeAuditData.findings?.find(f => f.severity === "CRITICAL" || f.finding_type?.includes("QCO"));
      if (crit) {
        selectFindingForInspection(crit.finding_id);
        toggleRowExpansion(crit.finding_id, true);
        const row = document.getElementById(`row_${crit.finding_id}`);
        if (row) row.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  }

  // ==========================================================================
  // TAB 2: EXTRACTED REQUIREMENTS
  // ==========================================================================
  function renderRequirementsTable(reqs) {
    requirementsTableBody.innerHTML = "";

    const filterCat = filterReqCategory?.value || "ALL";
    const searchQuery = (searchRequirements?.value || "").toLowerCase().trim();

    const filtered = reqs.filter(r => {
      const matchCat = (filterCat === "ALL") || (r.category === filterCat);
      const textMatch = !searchQuery || 
        r.parameter_name.toLowerCase().includes(searchQuery) ||
        r.value.toLowerCase().includes(searchQuery) ||
        (r.source_text && r.source_text.toLowerCase().includes(searchQuery));
      return matchCat && textMatch;
    });

    if (reqsCountSummary) {
      reqsCountSummary.textContent = `Showing ${filtered.length} of ${reqs.length} requirements`;
    }

    if (filtered.length === 0) {
      requirementsTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: var(--space-5); color: var(--text-muted);">
            No requirements match the search or category filters.
          </td>
        </tr>
      `;
      return;
    }

    filtered.forEach(r => {
      const tr = document.createElement("tr");
      const norm = r.normalized_value || {};
      const normText = norm.text_value || (norm.numeric_value !== null ? `${norm.numeric_value} ${norm.unit || ""}` : "—");
      const confPct = Math.round((r.extraction_confidence || 0.95) * 100);
      const clauseLoc = r.source_location?.clause_number ? `Clause ${r.source_location.clause_number} (Pg ${r.source_location.source_page || 1})` : "General Scope";

      tr.innerHTML = `
        <td><span class="clause-tag">${escapeHtml(r.requirement_id)}</span></td>
        <td><strong>${escapeHtml(r.parameter_name)}</strong></td>
        <td><span class="clause-tag" style="background: none; border: 1px solid var(--border-main);">${escapeHtml(r.category || "GENERAL")}</span></td>
        <td><span style="color: var(--navy-900); font-weight: 500;">${escapeHtml(r.value || "—")}</span></td>
        <td><span class="mono" style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(normText)}</span></td>
        <td>
          <span style="font-weight: 600; color: ${confPct >= 90 ? "var(--status-success-solid)" : "var(--status-warning-solid)"};">
            ${confPct}%
          </span>
        </td>
        <td><span style="font-size: 12px; color: var(--text-muted);">${escapeHtml(clauseLoc)}</span></td>
      `;

      requirementsTableBody.appendChild(tr);
    });
  }

  if (searchRequirements) {
    searchRequirements.addEventListener("input", () => {
      if (activeAuditData) renderRequirementsTable(activeAuditData.extracted_requirements || []);
    });
  }

  if (filterReqCategory) {
    filterReqCategory.addEventListener("change", () => {
      if (activeAuditData) renderRequirementsTable(activeAuditData.extracted_requirements || []);
    });
  }

  // ==========================================================================
  // TAB 3: INDIAN STANDARDS & BOM
  // ==========================================================================
  function renderStandardsTab(standards, bom) {
    // 1. Recommended Standards List
    standardsListContainer.innerHTML = "";
    if (standards.length === 0) {
      standardsListContainer.innerHTML = `<div style="color: var(--text-muted);">No standards recorded.</div>`;
    } else {
      standards.forEach((stdItem, idx) => {
        const std = stdItem.standard || {};
        const score = Math.round((stdItem.applicability_score || 0.9) * 100);
        const isPrimary = idx === 0;

        const row = document.createElement("div");
        row.className = `standard-dense-row ${isPrimary ? "primary" : ""}`;

        const evListHtml = (stdItem.evidence || []).map(ev => `
          <div class="standard-evidence-item">
            <i class="ph-bold ph-check"></i>
            <span>${escapeHtml(ev)}</span>
          </div>
        `).join("");

        row.innerHTML = `
          <div class="standard-row-top">
            <div style="display: flex; align-items: center; gap: var(--space-3);">
              <span class="standard-is-pill">${escapeHtml(std.is_number)}</span>
              ${isPrimary ? `<span class="table-badge compliant">Primary Product Standard</span>` : `<span class="table-badge completed">Allied Standard</span>`}
              <span class="clause-tag">Applicability: ${score}%</span>
            </div>
            <span class="clause-tag">Status: ${escapeHtml(std.current_status || "CURRENT")}</span>
          </div>

          <div class="standard-title-text">${escapeHtml(std.title || "")}</div>
          <div class="standard-explanation-text">${escapeHtml(stdItem.explanation || "")}</div>

          ${evListHtml ? `
            <div class="standard-evidence-tags">
              <span style="font-weight: 700; text-transform: uppercase; font-size: 11px; color: var(--text-muted); margin-bottom: 2px;">Technical Evidence Citations:</span>
              ${evListHtml}
            </div>
          ` : ""}
        `;

        standardsListContainer.appendChild(row);
      });
    }

    // 2. Standards BOM Table
    bomTableBody.innerHTML = "";
    if (bom.length === 0) {
      bomTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No BOM items recorded.</td></tr>`;
    } else {
      bom.forEach(b => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${b.item_number}</strong></td>
          <td><span class="standard-cell">${escapeHtml(b.is_number)}</span></td>
          <td><strong>${escapeHtml(b.title)}</strong></td>
          <td><span class="clause-tag">${escapeHtml(b.role)}</span></td>
          <td>
            ${b.is_mandatory_qco 
              ? `<span class="table-badge needs-review">MANDATORY QCO</span>` 
              : `<span class="table-badge compliant">Voluntary</span>`}
          </td>
          <td><span class="clause-tag">${escapeHtml(b.compliance_status)}</span></td>
          <td style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(b.action_required)}</td>
        `;
        bomTableBody.appendChild(tr);
      });
    }
  }

  // ==========================================================================
  // TAB 4: PARAMETER MATCHING MATRIX
  // ==========================================================================
  function renderParametersTable(standards) {
    parametersTableBody.innerHTML = "";
    const primary = standards[0] || {};
    const paramFits = primary.parameter_fit || [];

    if (paramFits.length === 0) {
      parametersTableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No parameter fit records evaluated.</td></tr>`;
      return;
    }

    paramFits.forEach(p => {
      const tr = document.createElement("tr");
      const fitStatus = p.fit_status || "NOT_SPECIFIED_IN_TENDER";

      let statusBadge = `<span class="matrix-status-cell NOT_SPECIFIED_IN_TENDER">NOT SPECIFIED</span>`;
      if (fitStatus === "COMPLIANT") {
        statusBadge = `<span class="matrix-status-cell COMPLIANT"><i class="ph-bold ph-check"></i> COMPLIANT</span>`;
      } else if (fitStatus === "DEVIATING") {
        statusBadge = `<span class="matrix-status-cell DEVIATING"><i class="ph-bold ph-warning"></i> DEVIATING</span>`;
      }

      tr.innerHTML = `
        <td><strong>${escapeHtml(p.parameter_name)}</strong></td>
        <td><span style="color: var(--navy-900); font-weight: 500;">${escapeHtml(p.tender_value || "—")}</span></td>
        <td style="font-size: 12.5px; color: var(--text-secondary);">${escapeHtml(p.standard_value || "—")}</td>
        <td>${statusBadge}</td>
      `;

      parametersTableBody.appendChild(tr);
    });
  }

  // ==========================================================================
  // TAB 5: STANDARDS RELATIONSHIP MAP
  // ==========================================================================
  function renderStandardsMap(standards, related) {
    alliedStandardsTableBody.innerHTML = "";

    if (related.length === 0) {
      alliedStandardsTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No allied standards recorded.</td></tr>`;
      return;
    }

    related.forEach(rel => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="standard-cell">${escapeHtml(rel.is_number)}</span></td>
        <td><strong>${escapeHtml(rel.title)}</strong></td>
        <td><span class="clause-tag">${escapeHtml(rel.relationship_type)}</span></td>
        <td><span class="clause-tag">${escapeHtml(rel.governing_primary_standard)}</span></td>
        <td style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(rel.relevance_notes)}</td>
      `;
      alliedStandardsTableBody.appendChild(tr);
    });

    // Node click interactions
    [graphNodePrimary, graphNodeTest, graphNodeMotor, graphNodeQco].forEach(node => {
      if (node) {
        node.addEventListener("click", () => {
          showToast(`Inspecting standard relationship: ${node.querySelector(".standard-is-pill, .graph-node-code")?.textContent || "Standard"}`);
        });
      }
    });
  }

  // ==========================================================================
  // TAB 6: CORRECTED SPECIFICATION DIFF
  // ==========================================================================
  function renderCorrectedClauses(clauses) {
    correctedClausesContainer.innerHTML = "";

    if (clauses.length === 0) {
      correctedClausesContainer.innerHTML = `<div style="text-align: center; padding: var(--space-6); color: var(--text-muted);">No clause modifications required. Original specification conforms to Indian Standards.</div>`;
      return;
    }

    clauses.forEach(c => {
      const card = document.createElement("div");
      card.className = "spec-clause-diff-card";

      card.innerHTML = `
        <div class="diff-card-header">
          <div class="diff-header-left">
            <span class="diff-clause-id">${escapeHtml(c.clause_id)}</span>
            <span class="diff-source-loc">Source: ${escapeHtml(c.source_clause_reference || "Tender Clause")}</span>
          </div>
          <button type="button" class="btn-copy-clause copy-single-btn" data-text="${escapeHtml(c.corrected_text)}">
            <i class="ph-bold ph-copy"></i>
            <span>Copy Clause</span>
          </button>
        </div>

        <div class="diff-columns-grid">
          <div class="diff-col original">
            <span class="diff-col-title">Original Tender Clause</span>
            <div class="diff-text-content">${escapeHtml(c.original_tender_text || "—")}</div>
          </div>
          <div class="diff-col corrected">
            <span class="diff-col-title">Corrected Draft (Officer-Reviewable)</span>
            <div class="diff-text-content">${escapeHtml(c.corrected_text || "—")}</div>
          </div>
        </div>

        <div class="diff-card-footer">
          <span><strong>Rationale:</strong> ${escapeHtml(c.rationale || "")}</span>
          <span class="clause-tag">Governing Rule: ${escapeHtml(c.governing_rules ? c.governing_rules.join(", ") : "BIS_CODE")}</span>
        </div>
      `;

      correctedClausesContainer.appendChild(card);
    });

    // Copy single clause buttons
    correctedClausesContainer.querySelectorAll(".copy-single-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const text = btn.getAttribute("data-text");
        if (text) {
          navigator.clipboard.writeText(text).then(() => {
            const originalHtml = btn.innerHTML;
            btn.innerHTML = `<i class="ph-bold ph-check"></i><span>Copied</span>`;
            showToast("Corrected clause copied to clipboard");
            setTimeout(() => { btn.innerHTML = originalHtml; }, 2000);
          });
        }
      });
    });
  }

  // "Copy All Corrected Clauses" Button
  if (btnCopyAllClauses) {
    btnCopyAllClauses.addEventListener("click", () => {
      if (!activeAuditData) return;
      const clauses = activeAuditData.corrected_clause || activeAuditData.corrected_clauses || [];
      if (clauses.length === 0) return;

      const fullDraftText = clauses.map(c => `[Clause ${c.source_clause_reference} - Rectified]:\n${c.corrected_text}\n(Rationale: ${c.rationale})`).join("\n\n---\n\n");
      navigator.clipboard.writeText(fullDraftText).then(() => {
        showToast("All 8 corrected specification clauses copied to clipboard");
      });
    });
  }

  // ==========================================================================
  // EXPORTERS & DOWNLOADS
  // ==========================================================================
  function downloadJsonDossier() {
    if (!activeAuditData) return;
    const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeAuditData, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", jsonStr);
    dlAnchor.setAttribute("download", `maanaknetra_audit_${activeAuditData.tender_metadata?.analysis_id || "dossier"}.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
    showToast("Audit JSON dossier downloaded successfully");
  }

  if (btnDownloadJson) btnDownloadJson.addEventListener("click", downloadJsonDossier);
  if (btnDownloadJsonRep) btnDownloadJsonRep.addEventListener("click", downloadJsonDossier);

  if (btnExportSpecTxt) {
    btnExportSpecTxt.addEventListener("click", () => {
      if (!activeAuditData) return;
      const clauses = activeAuditData.corrected_clause || activeAuditData.corrected_clauses || [];
      const content = `MAANAKNETRA AUDITED TECHNICAL SPECIFICATION\nTender: ${activeAuditData.tender_metadata?.document_title || "sample_tender.pdf"}\nGenerated: ${new Date().toISOString()}\n\n` +
        clauses.map(c => `=== Clause ${c.source_clause_reference} ===\n${c.corrected_text}\nRationale: ${c.rationale}\n`).join("\n");

      const txtStr = "data:text/plain;charset=utf-8," + encodeURIComponent(content);
      const dlAnchor = document.createElement("a");
      dlAnchor.setAttribute("href", txtStr);
      dlAnchor.setAttribute("download", `audited_specification_${activeAuditData.tender_metadata?.analysis_id || "draft"}.txt`);
      document.body.appendChild(dlAnchor);
      dlAnchor.click();
      dlAnchor.remove();
      showToast("Corrected specification (.txt) exported");
    });
  }

  if (btnExportBomCsv) {
    btnExportBomCsv.addEventListener("click", () => {
      if (!activeAuditData) return;
      const bom = activeAuditData.standards_bom || [];
      let csv = "Item Number,IS Number,Title,Role,Mandatory QCO,Status,Action Required\n";
      bom.forEach(b => {
        csv += `"${b.item_number}","${b.is_number}","${b.title}","${b.role}","${b.is_mandatory_qco}","${b.compliance_status}","${b.action_required}"\n`;
      });
      const csvStr = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
      const dlAnchor = document.createElement("a");
      dlAnchor.setAttribute("href", csvStr);
      dlAnchor.setAttribute("download", `standards_bom_${activeAuditData.tender_metadata?.analysis_id || "export"}.csv`);
      document.body.appendChild(dlAnchor);
      dlAnchor.click();
      dlAnchor.remove();
      showToast("Standards BOM CSV exported");
    });
  }

  if (btnPrintSummary) {
    btnPrintSummary.addEventListener("click", () => {
      window.print();
    });
  }

  // ==========================================================================
  // MODAL & TOAST UTILITIES
  // ==========================================================================
  function openModal() {
    evidenceModal.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    evidenceModal.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (btnModalClose) btnModalClose.addEventListener("click", closeModal);
  if (btnModalDismiss) btnModalDismiss.addEventListener("click", closeModal);
  if (evidenceModal) {
    evidenceModal.addEventListener("click", (e) => {
      if (e.target === evidenceModal) closeModal();
    });
  }

  function showToast(message) {
    if (toastTimeout) clearTimeout(toastTimeout);
    toastContainer.innerHTML = `
      <div class="toast-item">
        <i class="ph-bold ph-check-circle"></i>
        <span>${escapeHtml(message)}</span>
      </div>
    `;
    toastTimeout = setTimeout(() => {
      toastContainer.innerHTML = "";
    }, 3200);
  }

  // Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      if (globalSearchInput) globalSearchInput.focus();
    }
  });

  if (globalSearchInput) {
    globalSearchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const val = globalSearchInput.value.trim();
        if (val) {
          if (!activeAuditData) {
            loadCanonicalDemo(() => {
              switchResultTab("tabRequirements");
              if (searchRequirements) {
                searchRequirements.value = val;
                renderRequirementsTable(activeAuditData.extracted_requirements || []);
              }
            });
          } else {
            switchResultTab("tabRequirements");
            if (searchRequirements) {
              searchRequirements.value = val;
              renderRequirementsTable(activeAuditData.extracted_requirements || []);
            }
          }
        }
      }
    });
  }

  function escapeHtml(str) {
    if (typeof str !== "string") return String(str || "");
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
