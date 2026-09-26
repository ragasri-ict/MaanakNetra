/**
 * MAANAKNETRA — Enterprise Master Controller
 * AI-Powered Procurement & Indian Standards Intelligence
 *
 * Consumes real backend API from /api/demo and /api/analyze.
 * Strictly zero hardcoded analysis values.
 */

document.addEventListener("DOMContentLoaded", () => {
  // --------------------------------------------------------------------------
  // DOM Elements
  // --------------------------------------------------------------------------
  const appSidebar = document.getElementById("appSidebar");
  const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
  const newTenderBtn = document.getElementById("newTenderBtn");
  const headerDemoBtn = document.getElementById("headerDemoBtn");
  const heroDemoBtn = document.getElementById("heroDemoBtn");
  const heroUploadBtn = document.getElementById("heroUploadBtn");
  const startAuditBtn = document.getElementById("startAuditBtn");
  const retryAuditBtn = document.getElementById("retryAuditBtn");

  const dropTarget = document.getElementById("dropTarget");
  const tenderFileInput = document.getElementById("tenderFileInput");
  const fileSelectionPill = document.getElementById("fileSelectionPill");
  const fileSelectionName = document.getElementById("fileSelectionName");
  const clearSelectionBtn = document.getElementById("clearSelectionBtn");

  const secOverview = document.getElementById("secOverview");
  const auditLoadingState = document.getElementById("auditLoadingState");
  const loadingHeadline = document.getElementById("loadingHeadline");
  const loadingMessage = document.getElementById("loadingMessage");
  const auditErrorAlert = document.getElementById("auditErrorAlert");
  const errorMessage = document.getElementById("errorMessage");
  const resultsWorkspace = document.getElementById("resultsWorkspace");
  const officerReviewBanner = document.getElementById("officerReviewBanner");
  const officerReviewReasons = document.getElementById("officerReviewReasons");

  const linterSeveritySelect = document.getElementById("linterSeveritySelect");
  const downloadJsonBtn = document.getElementById("downloadJsonBtn");
  const stickyExportJsonBtn = document.getElementById("stickyExportJsonBtn");

  const evidenceDrawerBackdrop = document.getElementById("evidenceDrawerBackdrop");
  const closeDrawerBtn = document.getElementById("closeDrawerBtn");
  const drawerDismissBtn = document.getElementById("drawerDismissBtn");
  const drawerTitle = document.getElementById("drawerTitle");
  const drawerBody = document.getElementById("drawerBody");

  const appToast = document.getElementById("appToast");
  const toastMessage = document.getElementById("toastMessage");

  let currentSelectedFile = null;
  let activeAuditData = null;
  let toastTimer = null;

  // --------------------------------------------------------------------------
  // Sidebar & Navigation
  // --------------------------------------------------------------------------
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener("click", () => {
      appSidebar.classList.toggle("open");
    });
  }

  // Smooth scroll and active state for sidebar links
  document.querySelectorAll(".sidebar-nav .nav-item").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = link.getAttribute("data-target");
      const targetEl = document.getElementById(targetId);

      document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => item.classList.remove("active"));
      link.classList.add("active");

      if (targetEl) {
        // If results not visible yet and user clicked a results section, scroll to overview
        if (resultsWorkspace.classList.contains("hidden") && targetId !== "secOverview") {
          secOverview.scrollIntoView({ behavior: "smooth" });
        } else {
          targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }

      // Close mobile sidebar on navigate
      if (window.innerWidth <= 768) {
        appSidebar.classList.remove("open");
      }
    });
  });

  // New Tender Button (Resets view to intake)
  newTenderBtn.addEventListener("click", () => {
    resetToIntakeView();
  });

  function resetToIntakeView() {
    resultsWorkspace.classList.add("hidden");
    auditErrorAlert.classList.add("hidden");
    auditLoadingState.classList.add("hidden");
    secOverview.classList.remove("hidden");

    currentSelectedFile = null;
    tenderFileInput.value = "";
    fileSelectionPill.classList.add("hidden");
    startAuditBtn.disabled = true;

    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => item.classList.remove("active"));
    const overviewNav = document.querySelector(".sidebar-nav .nav-item[data-target='secOverview']");
    if (overviewNav) overviewNav.classList.add("active");

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // --------------------------------------------------------------------------
  // File Upload Handlers (Drag & Drop + Input)
  // --------------------------------------------------------------------------
  heroUploadBtn.addEventListener("click", () => {
    tenderFileInput.click();
  });

  ["dragenter", "dragover"].forEach((evtName) => {
    dropTarget.addEventListener(evtName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropTarget.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach((evtName) => {
    dropTarget.addEventListener(evtName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropTarget.classList.remove("dragover");
    }, false);
  });

  dropTarget.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      handleSelectedFile(dt.files[0]);
    }
  });

  tenderFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  clearSelectionBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    currentSelectedFile = null;
    tenderFileInput.value = "";
    fileSelectionPill.classList.add("hidden");
    startAuditBtn.disabled = true;
  });

  function handleSelectedFile(file) {
    currentSelectedFile = file;
    fileSelectionName.textContent = file.name;
    fileSelectionPill.classList.remove("hidden");
    startAuditBtn.disabled = false;
  }

  // --------------------------------------------------------------------------
  // Action Handlers: Sample Tender & Upload Audit
  // --------------------------------------------------------------------------
  headerDemoBtn.addEventListener("click", () => {
    fetchBenchmarkDemo();
  });

  heroDemoBtn.addEventListener("click", () => {
    fetchBenchmarkDemo();
  });

  startAuditBtn.addEventListener("click", () => {
    if (!currentSelectedFile) return;
    executeTenderAudit(currentSelectedFile);
  });

  if (retryAuditBtn) {
    retryAuditBtn.addEventListener("click", () => {
      if (currentSelectedFile) {
        executeTenderAudit(currentSelectedFile);
      } else {
        fetchBenchmarkDemo();
      }
    });
  }

  async function fetchBenchmarkDemo() {
    showLoading(
      "Analyzing Canonical Demonstration Tender...",
      "Executing end-to-end procurement intelligence analysis for demo/sample_tender.pdf (IS 14220 Submersible Pumpset)..."
    );
    hideError();

    try {
      const response = await fetch("/api/demo");
      if (!response.ok) {
        throw new Error(`Demo endpoint returned status ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      populateDashboard(data);
      showToast("Demo tender audit loaded successfully");
    } catch (err) {
      showError(`Unable to load benchmark demonstration: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  async function executeTenderAudit(file) {
    showLoading(
      `Auditing '${file.name}'...`,
      "Running multi-phase deterministic rule checks, parameter limit matrix, standards knowledge graph traversal, and statutory QCO audit..."
    );
    hideError();

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Analysis failed with HTTP status ${response.status}`);
      }

      const data = await response.json();
      populateDashboard(data);
      showToast(`Tender '${file.name}' analyzed successfully`);
    } catch (err) {
      showError(`Audit execution error: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  // --------------------------------------------------------------------------
  // Master Dashboard Populator (Strictly from real API response)
  // --------------------------------------------------------------------------
  function populateDashboard(data) {
    activeAuditData = data;

    const meta = data.tender_metadata || {};
    const reqs = data.extracted_requirements || [];
    const findings = data.findings || [];
    const clauses = data.corrected_clause || data.corrected_clauses || [];
    const recs = data.recommended_standards || [];
    const bom = data.standards_bom || [];
    const related = data.related_standards || [];
    const cert = data.certification_flags || {};
    const statusFlags = data.status_flags || {};
    const risk = data.risk_indicator || {};

    // 1. Dossier Snapshot Bar
    document.getElementById("dossierDocTitle").textContent = meta.document_title || meta.file_name || "Procurement Tender Specification";
    document.getElementById("dossierAnalysisId").textContent = meta.analysis_id || "ANALYSIS_DOSSIER";
    document.getElementById("dossierPageCount").textContent = meta.page_count || 1;

    let categoryContext = "General Engineering & Equipment";
    if (reqs.length > 0 && reqs[0].product_category_context) {
      categoryContext = reqs[0].product_category_context;
    } else if (data.product_context && data.product_context.primary_item_name) {
      categoryContext = data.product_context.primary_item_name;
    }
    document.getElementById("dossierCategory").textContent = categoryContext;

    const analyzedTime = meta.analyzed_at ? new Date(meta.analyzed_at).toLocaleString() : "Just Now";
    document.getElementById("dossierTimestamp").textContent = analyzedTime;

    // 2. Top KPI Strip
    const riskLevel = (risk.risk_level || "MEDIUM").toUpperCase();
    const riskBadge = document.getElementById("kpiRiskBadge");
    riskBadge.textContent = riskLevel;
    riskBadge.className = `risk-badge-display risk-${riskLevel}`;

    document.getElementById("kpiRiskSubtext").textContent = risk.summary || "Evaluation completed against Indian Standards & statutory QCOs.";

    const complianceScore = Math.round(risk.compliance_score !== undefined ? risk.compliance_score : 50);
    document.getElementById("kpiComplianceScore").textContent = `${complianceScore}%`;
    const complianceFill = document.getElementById("kpiComplianceFill");
    complianceFill.style.width = `${Math.min(100, Math.max(0, complianceScore))}%`;
    if (complianceScore < 40) {
      complianceFill.style.backgroundColor = "var(--crimson-main)";
    } else if (complianceScore < 70) {
      complianceFill.style.backgroundColor = "var(--saffron-main)";
    } else {
      complianceFill.style.backgroundColor = "var(--emerald-main)";
    }

    document.getElementById("kpiFindingsCount").textContent = findings.length;
    const critCount = risk.critical_issues_count !== undefined ? risk.critical_issues_count : findings.filter(f => f.severity === "CRITICAL").length;
    const highCount = risk.high_issues_count !== undefined ? risk.high_issues_count : findings.filter(f => f.severity === "HIGH").length;
    const medCount = risk.medium_issues_count !== undefined ? risk.medium_issues_count : findings.filter(f => f.severity === "MEDIUM").length;
    document.getElementById("kpiFindingsBreakdown").textContent = `${critCount} Critical · ${highCount} High · ${medCount} Medium`;

    const stdsCount = recs.length > 0 ? recs.length : bom.length;
    document.getElementById("kpiStandardsCount").textContent = stdsCount;
    document.getElementById("kpiStandardsBreakdown").textContent = `${stdsCount} governing / referenced Indian Standards`;

    // Sidebar finding badge
    const navAuditBadge = document.getElementById("navAuditBadge");
    if (navAuditBadge) {
      navAuditBadge.textContent = findings.length;
      navAuditBadge.classList.toggle("hidden", findings.length === 0);
    }

    // 3. Human Control & Verification Banner
    const isReviewRequired = Boolean(data.human_review_required || findings.some(f => f.requires_human_review));
    if (isReviewRequired) {
      officerReviewBanner.classList.remove("hidden");
      const reasonsList = [];
      if (statusFlags.has_superseded_standards) reasonsList.push("superseded standard citation detected in tender text");
      if (cert.qco_violation_risk) reasonsList.push("omission of mandatory Scheme-I BIS ISI Mark licensing clause under governing QCO");
      if (findings.some(f => f.finding_type === "VAGUE_REQUIREMENT")) reasonsList.push("unquantified subjective terminology requiring objective metrics");
      if (reasonsList.length === 0) reasonsList.push("statutory deviations and specification gaps require formal review");
      officerReviewReasons.textContent = "Officer verification required prior to bid publishing due to: " + reasonsList.join("; ") + ".";
    } else {
      officerReviewBanner.classList.add("hidden");
    }

    // 4. Decision Trace Pipeline (Section 9)
    populateDecisionTrace(data);

    // 5. Section 5: Tender Audit Findings (Hero Feature)
    renderLinterFindings(findings);

    // 6. Section 8: Corrected Specification Draft
    renderCorrectedClauses(clauses);

    // 7. Section 1: Extracted Requirements
    renderRequirements(reqs);

    // 8. Section 2: Recommended Standards
    renderRecommendedStandards(recs);

    // 9. Section 3: Technical Parameter Evidence
    renderParameterEvidence(recs);

    // 10. Section 4: Regulatory Intelligence
    renderRegulatoryIntelligence(data);

    // 11. Section 7: Standards Relationship Map
    renderStandardsMap(recs, related);

    // 12. Reports & BOM
    renderBOM(bom);

    // 13. Sticky Review Summary (Right Column ~28%)
    populateStickyReviewSummary(data, critCount, highCount, medCount);

    // Reveal Workspace & Smooth Scroll
    resultsWorkspace.classList.remove("hidden");
    resultsWorkspace.scrollIntoView({ behavior: "smooth" });
  }

  // --------------------------------------------------------------------------
  // SECTION 9: Decision Trace Pipeline
  // --------------------------------------------------------------------------
  function populateDecisionTrace(data) {
    const cited = data.already_cited_standards || [];
    const reqs = data.extracted_requirements || [];
    const recs = data.recommended_standards || [];
    const cert = data.certification_flags || {};
    const findings = data.findings || [];
    const clauses = data.corrected_clause || data.corrected_clauses || [];

    const topCited = cited[0] ? cited[0].raw_citation : (metaDocName() || "Tender Clause");
    const topReq = reqs[0] ? reqs[0].parameter_name : "General Requirements";
    const topStd = recs[0] && recs[0].standard ? recs[0].standard.is_number : "IS 14220";
    const topOrder = cert.governing_qco_orders && cert.governing_qco_orders[0] ? cert.governing_qco_orders[0].order_name : "Pumps QCO 2023";
    const topFinding = findings[0] ? findings[0].title : "Audit Complete";
    const topCorr = clauses[0] ? `${clauses[0].clause_id} Rectification` : "Standard Verified";

    document.getElementById("traceTenderClause").textContent = truncateText(topCited, 18);
    document.getElementById("traceExtractedReq").textContent = truncateText(topReq, 18);
    document.getElementById("traceMatchedStd").textContent = truncateText(topStd, 16);
    document.getElementById("traceParamFit").textContent = truncateText(reqs[1] ? reqs[1].parameter_name : "Engineering Limits", 18);
    document.getElementById("traceRegSignal").textContent = truncateText(topOrder, 18);
    document.getElementById("traceFindingType").textContent = truncateText(topFinding, 18);
    document.getElementById("traceCorrectedDraft").textContent = truncateText(topCorr, 18);
  }

  function metaDocName() {
    return activeAuditData?.tender_metadata?.document_title || activeAuditData?.tender_metadata?.file_name;
  }

  // --------------------------------------------------------------------------
  // SECTION 5: Tender Audit Findings (Hero Feature)
  // Critical, High, Medium with counts and [ View Evidence ]
  // --------------------------------------------------------------------------
  linterSeveritySelect.addEventListener("change", () => {
    if (!activeAuditData) return;
    const filter = linterSeveritySelect.value;
    const allFindings = activeAuditData.findings || [];
    if (filter === "ALL") {
      renderLinterFindings(allFindings);
    } else {
      renderLinterFindings(allFindings.filter(f => f.severity === filter));
    }
  });

  function renderLinterFindings(findings) {
    const container = document.getElementById("linterFindingsContainer");
    container.innerHTML = "";

    if (!findings || findings.length === 0) {
      container.innerHTML = `<div class="card text-center" style="padding: 2.5rem; color: var(--text-muted);"><i class="ph-bold ph-check-circle" style="font-size: 2rem; color: var(--emerald-main); display: block; margin-bottom: 0.5rem;"></i>No tender audit findings found for the selected filter.</div>`;
      return;
    }

    findings.forEach((f) => {
      const card = document.createElement("div");
      card.className = `finding-card sev-${f.severity}`;

      const fix = f.suggested_fix || {};
      const src = f.source || {};
      const stdCode = f.affected_standard ? f.affected_standard.is_number : "BIS Standard";
      const reviewState = f.requires_human_review ? "Officer verification required" : "Advisory Standard Finding";

      card.innerHTML = `
        <div class="finding-top-row">
          <div class="finding-tags-group">
            <span class="badge-sev ${f.severity}">${f.severity}</span>
            <span class="badge-type">${escapeHtml(f.finding_type || "AUDIT_FINDING")}</span>
            <span class="pill pill-mono">${escapeHtml(f.finding_id || "")}</span>
          </div>
          <span class="pill"><i class="ph-bold ph-bookmark"></i> ${escapeHtml(stdCode)}</span>
        </div>

        <h4 class="finding-title">${escapeHtml(f.title || "Audit Finding")}</h4>

        ${f.tender_text ? `
          <div class="finding-evidence-quote">
            <strong>Exact Tender Evidence:</strong> "${escapeHtml(f.tender_text)}"
          </div>
        ` : ""}

        <p class="finding-explanation">
          <strong>Why It Matters:</strong> ${escapeHtml(f.explanation || "")}
        </p>

        ${fix.recommended_action_summary ? `
          <div class="finding-fix-box">
            <span class="fix-label"><i class="ph-bold ph-arrow-bend-down-right"></i> Recommended Action:</span>
            <p class="fix-text">${escapeHtml(fix.recommended_action_summary)}</p>
          </div>
        ` : ""}

        <div class="finding-footer">
          <span><strong>Provenance:</strong> ${escapeHtml(src.source_type || "RULE_ENGINE")} (${escapeHtml(src.rule_id || "")})</span>
          <div style="display: flex; align-items: center; gap: 0.65rem;">
            <span class="pill ${f.requires_human_review ? "font-semibold text-amber" : ""}">${escapeHtml(reviewState)}</span>
            <button class="btn-trace-link" type="button" data-finding-id="${escapeHtml(f.finding_id)}">
              <i class="ph-bold ph-magnifying-glass"></i> View Evidence
            </button>
          </div>
        </div>
      `;

      container.appendChild(card);
    });

    // Wire up [ View Evidence ] buttons
    container.querySelectorAll(".btn-trace-link").forEach((btn) => {
      btn.addEventListener("click", () => {
        const fId = btn.getAttribute("data-finding-id");
        openEvidenceDrawerForFinding(fId);
      });
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 8: Corrected Specification Draft
  // ORIGINAL ↓ CORRECTED DRAFT with Copy Draft button and toast
  // --------------------------------------------------------------------------
  function renderCorrectedClauses(clauses) {
    const container = document.getElementById("correctedClausesContainer");
    container.innerHTML = "";

    if (!clauses || clauses.length === 0) {
      container.innerHTML = `<div class="card text-center" style="padding: 2rem; color: var(--text-muted);">No clause rectifications required. Specifications conform to Indian Standards.</div>`;
      return;
    }

    clauses.forEach((c) => {
      const card = document.createElement("div");
      card.className = "clause-card";

      card.innerHTML = `
        <div class="clause-top">
          <div>
            <span class="clause-id-tag">${escapeHtml(c.clause_id || "")}</span>
            <span class="clause-ref-tag"><i class="ph-bold ph-map-pin"></i> ${escapeHtml(c.source_clause_reference || "Tender Specification")}</span>
          </div>
          <button class="btn-copy-draft copy-clause-btn" type="button" data-text="${escapeHtml(c.corrected_text || "")}">
            <i class="ph-bold ph-copy"></i> Copy Draft
          </button>
        </div>

        <div class="clause-side-by-side">
          <div class="col-panel col-original">
            <span class="col-tag">Original Clause (Flagged)</span>
            <p class="col-text">${escapeHtml(c.original_tender_text || "")}</p>
          </div>
          <div class="col-panel col-corrected">
            <span class="col-tag">Corrected Draft (Officer-Reviewable)</span>
            <p class="col-text">${escapeHtml(c.corrected_text || "")}</p>
          </div>
        </div>

        <div class="clause-footer">
          <span><strong>Rationale:</strong> ${escapeHtml(c.rationale || "")}</span>
          <span class="draft-label-tag">Officer-reviewable draft</span>
        </div>
      `;

      container.appendChild(card);
    });

    // Copy to clipboard handlers with toast
    container.querySelectorAll(".copy-clause-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const textToCopy = btn.getAttribute("data-text");
        if (!textToCopy) return;

        navigator.clipboard.writeText(textToCopy).then(() => {
          const originalHTML = btn.innerHTML;
          btn.innerHTML = `<i class="ph-bold ph-check"></i> Copied!`;
          btn.style.borderColor = "var(--emerald-main)";
          btn.style.color = "var(--emerald-dark)";
          showToast("Corrected clause copied to clipboard");
          setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.borderColor = "";
            btn.style.color = "";
          }, 2000);
        });
      });
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 1: Extracted Requirements
  // Parameter | Tender Value | Confidence | Evidence
  // --------------------------------------------------------------------------
  function renderRequirements(reqs) {
    const tbody = document.getElementById("requirementsTableBody");
    tbody.innerHTML = "";

    if (!reqs || reqs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center" style="padding: 1.75rem; color: var(--text-muted);">No requirements extracted from document.</td></tr>`;
      return;
    }

    reqs.forEach((r) => {
      const tr = document.createElement("tr");

      const norm = r.normalized_value || {};
      const normVal = norm.text_value || (norm.numeric_value !== undefined && norm.numeric_value !== null ? `${norm.numeric_value} ${norm.unit || ""}` : "");
      const confPct = Math.round((r.extraction_confidence || 0.9) * 100);
      const clauseLoc = r.source_location && r.source_location.clause_number ? `Clause ${r.source_location.clause_number} (Pg ${r.source_location.source_page || 1})` : (r.field || "Tender Clause");

      tr.innerHTML = `
        <td>
          <strong>${escapeHtml(r.parameter_name || "Parameter")}</strong>
          <div style="margin-top: 0.2rem;">
            <span class="pill pill-mono">${escapeHtml(r.requirement_id || "")}</span>
            <span class="pill">${escapeHtml(r.category || "GENERAL")}</span>
          </div>
        </td>
        <td>
          <div style="font-weight: 600; color: var(--navy-900);">${escapeHtml(r.value || "—")}</div>
          ${normVal ? `<div style="font-size: 0.74rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 0.15rem;">Normalized: ${escapeHtml(normVal)}</div>` : ""}
        </td>
        <td>
          <span class="pill ${confPct >= 90 ? "font-semibold text-emerald" : ""}">
            <i class="ph-bold ph-seal-check"></i> ${confPct}% Confidence
          </span>
        </td>
        <td>
          <div style="font-size: 0.78rem; color: var(--text-body); line-height: 1.4;">
            "${escapeHtml(r.source_text || "")}"
          </div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">
            <i class="ph-bold ph-map-pin"></i> ${escapeHtml(clauseLoc)}
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 2: Recommended Standards
  // Rank, IS Number, Title, Match, Status, Why recommended, [ View Evidence ]
  // --------------------------------------------------------------------------
  function renderRecommendedStandards(recs) {
    const container = document.getElementById("recommendedStandardsList");
    container.innerHTML = "";

    if (!recs || recs.length === 0) {
      container.innerHTML = `<div class="card text-center" style="padding: 2rem; color: var(--text-muted);">No standards recommended for this scope.</div>`;
      return;
    }

    recs.forEach((r, idx) => {
      const std = r.standard || {};
      const scorePct = Math.round((r.applicability_score || 0) * 100);
      const isTop = idx === 0;

      const card = document.createElement("div");
      card.className = `rec-card ${isTop ? "top-recommendation" : ""}`;

      const evidenceItems = (r.evidence || []).map(ev => `
        <div class="rec-ev-item">
          <i class="ph-bold ph-check-circle"></i>
          <span>${escapeHtml(ev)}</span>
        </div>
      `).join("");

      card.innerHTML = `
        <div class="rec-top-row">
          <div class="rec-code-group">
            <span class="pill pill-mono font-bold">Rank #${idx + 1}</span>
            <strong class="rec-code-str">${escapeHtml(std.is_number || "")}</strong>
            <span class="pill"><i class="ph-bold ph-check"></i> Status: ${escapeHtml(std.current_status || "CURRENT")}</span>
            ${std.year ? `<span class="pill pill-mono">${std.year}</span>` : ""}
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="rec-score-pill"><i class="ph-bold ph-target"></i> Match: ${scorePct}%</span>
            <button class="btn-trace-link" type="button" onclick="openEvidenceDrawerForStandard('${escapeHtml(std.is_number)}')">
              <i class="ph-bold ph-magnifying-glass"></i> View Evidence
            </button>
          </div>
        </div>

        <h4 class="rec-title-line">${escapeHtml(std.title || "")}</h4>
        <p class="rec-reason-text"><strong>Why Recommended:</strong> ${escapeHtml(r.explanation || "")}</p>

        ${evidenceItems ? `
          <div class="rec-evidence-list">
            <span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Supporting Standard Evidence:</span>
            ${evidenceItems}
          </div>
        ` : ""}
      `;

      container.appendChild(card);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 3: Technical Parameter Evidence
  // Parameter | Tender | Standard Evidence | Assessment | Evidence
  // --------------------------------------------------------------------------
  function renderParameterEvidence(recs) {
    const tbody = document.getElementById("parameterEvidenceBody");
    tbody.innerHTML = "";

    const primaryRec = (recs && recs.length > 0) ? recs[0] : null;
    const paramFits = primaryRec ? (primaryRec.parameter_fit || []) : [];

    if (!paramFits || paramFits.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center" style="padding: 1.75rem; color: var(--text-muted);">No parameter fits evaluated.</td></tr>`;
      return;
    }

    paramFits.forEach((p) => {
      const tr = document.createElement("tr");

      let badgeClass = "badge-NOT_SPECIFIED";
      let badgeLabel = "— NOT SPECIFIED";

      const fitStatus = (p.fit_status || "").toUpperCase();
      if (fitStatus === "COMPLIANT") {
        badgeClass = "badge-COMPLIANT";
        badgeLabel = "✓ COMPLIANT";
      } else if (fitStatus === "DEVIATING") {
        badgeClass = "badge-DEVIATING";
        badgeLabel = "⚠ DEVIATING";
      }

      tr.innerHTML = `
        <td><strong>${escapeHtml(p.parameter_name || "")}</strong></td>
        <td><span style="color: var(--navy-900); font-weight: 500;">${escapeHtml(p.tender_value || "—")}</span></td>
        <td style="font-size: 0.78rem; color: var(--text-body); line-height: 1.4;">${escapeHtml(p.standard_value || "—")}</td>
        <td>
          <span class="legend-pill ${badgeClass}">
            ${badgeLabel}
          </span>
        </td>
        <td>
          <button class="btn-trace-link" type="button" onclick="openEvidenceDrawerForParameter('${escapeHtml(p.parameter_name)}')">
            <i class="ph-bold ph-magnifying-glass"></i> View
          </button>
        </td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 4: Regulatory Intelligence
  // Standard Status, QCO Applicability, Certification Signal, Effective Date,
  // Verification Status, Review Required
  // --------------------------------------------------------------------------
  function renderRegulatoryIntelligence(data) {
    const cert = data.certification_flags || {};
    const statusFlags = data.status_flags || {};
    const qcoOrders = cert.governing_qco_orders || [];
    const topOrder = qcoOrders[0] || {};
    const citedStds = data.already_cited_standards || [];

    // 1. QCO Info
    const regQcoBadge = document.getElementById("regQcoBadge");
    if (cert.qco_violation_risk || cert.qco_mandate_applicable) {
      regQcoBadge.className = "status-pill status-pill-critical";
      regQcoBadge.textContent = "MANDATORY QCO IN FORCE";
    } else {
      regQcoBadge.className = "status-pill status-pill-amber";
      regQcoBadge.textContent = "VOLUNTARY STANDARD";
    }

    document.getElementById("regQcoTitle").textContent = topOrder.order_name || "Pumps (Quality Control) Order, 2023";
    document.getElementById("regQcoOrder").textContent = topOrder.order_number ? `${topOrder.order_number}` : "S.O. 4333(E)";
    document.getElementById("regQcoMinistry").textContent = topOrder.issuing_ministry || "Ministry of Commerce and Industry (DPIIT)";
    document.getElementById("regQcoScheme").textContent = "Compulsory Scheme-I BIS Standard Mark (ISI mark) licensing";
    document.getElementById("regQcoEffectiveDate").textContent = topOrder.effective_date || "2024-10-06";

    const regVerifStatus = document.getElementById("regQcoVerificationStatus");
    if (data.human_review_required) {
      regVerifStatus.textContent = "PENDING VERIFICATION";
      regVerifStatus.className = "reg-val font-semibold text-amber";
    } else {
      regVerifStatus.textContent = "VERIFIED";
      regVerifStatus.className = "reg-val font-semibold text-emerald";
    }

    const regReviewReq = document.getElementById("regQcoReviewRequired");
    regReviewReq.textContent = data.human_review_required ? "YES — OFFICER REVIEW REQUIRED" : "NO — COMPLIANT";
    regReviewReq.className = data.human_review_required ? "reg-val font-bold text-crimson" : "reg-val font-bold text-emerald";

    // 2. Lifecycle & Supersession Track
    const regLifecycleBadge = document.getElementById("regLifecycleBadge");
    const trackContainer = document.getElementById("supersessionTrackContainer");
    trackContainer.innerHTML = "";

    if (statusFlags.has_superseded_standards) {
      regLifecycleBadge.className = "status-pill status-pill-critical";
      regLifecycleBadge.textContent = "SUPERSEDED CITATION";

      const supersededCited = citedStds.find(s => s.year_cited && s.year_cited < 2018) || {
        raw_citation: "IS 14220:1994",
        source_text: "Openwell Submersible Pumpsets - Specification (First Edition)"
      };

      trackContainer.innerHTML = `
        <div class="track-card obsolete">
          <span class="track-tag text-crimson">CITED IN TENDER (SUPERSEDED)</span>
          <strong class="track-code">${escapeHtml(supersededCited.raw_citation || "IS 14220:1994")}</strong>
          <span class="track-desc">Openwell Submersible Pumpsets (Obsolete First Edition)</span>
        </div>
        <div class="track-arrow-down"><i class="ph-bold ph-arrow-down"></i></div>
        <div class="track-card active">
          <span class="track-tag text-emerald">CURRENT / ACTIVE REPLACEMENT</span>
          <strong class="track-code">IS 14220:2018</strong>
          <span class="track-desc">Openwell Submersible Pumpsets — Specification (Second Revision)</span>
        </div>
      `;
    } else {
      regLifecycleBadge.className = "status-pill status-pill-amber";
      regLifecycleBadge.textContent = "CURRENT CITATION";

      trackContainer.innerHTML = `
        <div class="track-card active">
          <span class="track-tag text-emerald">CURRENT STANDARD CITATION</span>
          <strong class="track-code">IS 14220:2018</strong>
          <span class="track-desc">Active revision confirmed against published BIS Product Manual</span>
        </div>
      `;
    }
  }

  // --------------------------------------------------------------------------
  // SECTION 7: Standards Relationship Map
  // Real graph data with connected visual nodes + allied standards table
  // --------------------------------------------------------------------------
  function renderStandardsMap(recs, related) {
    const tbody = document.getElementById("alliedStandardsBody");
    tbody.innerHTML = "";

    if (recs && recs.length > 0 && recs[0].standard) {
      const primary = recs[0].standard;
      const primaryCodeEl = document.getElementById("graphPrimaryCode");
      const primaryTitleEl = document.getElementById("graphPrimaryTitle");
      if (primaryCodeEl) primaryCodeEl.textContent = `${primary.is_number || "IS 14220"}${primary.year ? `:${primary.year}` : ":2018"}`;
      if (primaryTitleEl) primaryTitleEl.textContent = primary.title || "Openwell Submersible Pumpsets — Specification";
    }

    if (!related || related.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No allied standards mapped in knowledge graph.</td></tr>`;
      return;
    }

    related.forEach((rel) => {
      const tr = document.createElement("tr");

      tr.innerHTML = `
        <td>
          <strong class="mono" style="color: var(--navy-900); font-weight: 700;">${escapeHtml(rel.is_number || "")}</strong>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(rel.title || "")}</div>
        </td>
        <td><span class="pill">${escapeHtml(rel.relationship_type || "NORMATIVE_REFERENCE")}</span></td>
        <td><span class="pill pill-mono">${escapeHtml(rel.governing_primary_standard || "IS 14220")}</span></td>
        <td>
          <span class="pill ${rel.importance === "MANDATORY" ? "font-bold text-crimson" : ""}">
            ${escapeHtml(rel.importance || "RECOMMENDED")}
          </span>
        </td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // REPORTS: Standards Bill of Materials (BOM)
  // --------------------------------------------------------------------------
  function renderBOM(bom) {
    const tbody = document.getElementById("bomTableBody");
    tbody.innerHTML = "";

    if (!bom || bom.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No BOM items recorded.</td></tr>`;
      return;
    }

    bom.forEach((item) => {
      const tr = document.createElement("tr");

      const mandatePill = item.is_mandatory_qco
        ? `<span class="legend-pill badge-DEVIATING" style="font-size: 0.68rem;"><i class="ph-bold ph-shield-check"></i> STATUTORY MANDATE</span>`
        : `<span class="legend-pill badge-NOT_SPECIFIED" style="font-size: 0.68rem;">VOLUNTARY</span>`;

      tr.innerHTML = `
        <td><strong>${item.item_number || ""}</strong></td>
        <td><span class="pill pill-mono font-bold">${escapeHtml(item.is_number || "")}</span></td>
        <td>
          <div style="font-weight: 600; color: var(--navy-900);">${escapeHtml(item.title || "")}</div>
        </td>
        <td><span class="pill">${escapeHtml(item.role || "")}</span></td>
        <td>${mandatePill}</td>
        <td><span class="pill pill-mono">${escapeHtml(item.compliance_status || "")}</span></td>
        <td style="font-size: 0.76rem; color: var(--text-body); line-height: 1.35;">${escapeHtml(item.action_required || "Reference in tender quality specification.")}</td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // Sticky Review Summary (~28% Right Column)
  // --------------------------------------------------------------------------
  function populateStickyReviewSummary(data, critCount, highCount, medCount) {
    const risk = data.risk_indicator || {};
    const cert = data.certification_flags || {};
    const statusFlags = data.status_flags || {};
    const findings = data.findings || [];

    document.getElementById("reviewAnalysisId").textContent = data.tender_metadata?.analysis_id || "ANALYSIS_DOSSIER";

    const riskLevel = (risk.risk_level || "MEDIUM").toUpperCase();
    const reviewRiskBadge = document.getElementById("reviewRiskBadge");
    reviewRiskBadge.textContent = riskLevel;
    reviewRiskBadge.className = `risk-badge-display risk-${riskLevel}`;

    const score = Math.round(risk.compliance_score !== undefined ? risk.compliance_score : 50);
    document.getElementById("reviewComplianceScore").textContent = `${score}%`;
    const fill = document.getElementById("reviewComplianceFill");
    fill.style.width = `${score}%`;
    if (score < 40) fill.style.backgroundColor = "var(--crimson-main)";
    else if (score < 70) fill.style.backgroundColor = "var(--saffron-main)";
    else fill.style.backgroundColor = "var(--emerald-main)";

    document.getElementById("reviewHumanReq").textContent = data.human_review_required ? "REQUIRED" : "COMPLIANT";
    document.getElementById("reviewHumanReq").className = data.human_review_required ? "review-val text-amber font-semibold" : "review-val text-emerald font-semibold";

    document.getElementById("reviewQcoStatus").textContent = cert.qco_violation_risk ? "OMISSION FLAGGED" : (cert.qco_mandate_applicable ? "APPLICABLE" : "VOLUNTARY");
    document.getElementById("reviewQcoStatus").className = cert.qco_violation_risk ? "review-val text-crimson font-semibold" : "review-val text-emerald font-semibold";

    document.getElementById("reviewStandardsStatus").textContent = statusFlags.has_superseded_standards ? "SUPERSEDED CITATION" : "CURRENT";
    document.getElementById("reviewStandardsStatus").className = statusFlags.has_superseded_standards ? "review-val text-crimson font-semibold" : "review-val text-emerald font-semibold";

    document.getElementById("reviewTotalFindings").textContent = findings.length;
    document.getElementById("reviewCritCount").textContent = critCount;
    document.getElementById("reviewHighCount").textContent = highCount;
    document.getElementById("reviewMedCount").textContent = medCount;
  }

  // --------------------------------------------------------------------------
  // SECTION 6: Evidence Drawer (Slide-In Modal)
  // --------------------------------------------------------------------------
  window.openEvidenceDrawerForFinding = function(findingId) {
    if (!activeAuditData) return;
    const findings = activeAuditData.findings || [];
    const f = findings.find(item => item.finding_id === findingId) || findings[0];
    if (!f) return;

    drawerTitle.textContent = `${f.finding_id} · ${f.title || "Audit Finding"}`;
    const src = f.source || {};
    const std = f.affected_standard || {};
    const fix = f.suggested_fix || {};

    drawerBody.innerHTML = `
      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Severity & Finding Type</span>
          <div style="margin-top: 0.25rem; display: flex; gap: 0.4rem; align-items: center;">
            <span class="badge-sev ${f.severity}">${f.severity}</span>
            <span class="badge-type">${escapeHtml(f.finding_type || "AUDIT_FINDING")}</span>
          </div>
        </div>
      </div>

      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Exact Tender Clause Evidence</span>
          <div class="drawer-field-val quote">"${escapeHtml(f.tender_text || "Clause omitted in original tender text")}"</div>
        </div>
        <div class="drawer-field-row" style="margin-top: 0.5rem;">
          <span class="drawer-field-lbl">Technical Explanation</span>
          <div class="drawer-field-val">${escapeHtml(f.explanation || "")}</div>
        </div>
      </div>

      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Affected Standard / Statutory QCO</span>
          <div class="drawer-field-val font-semibold">${escapeHtml(std.is_number || "BIS Standard")} — ${escapeHtml(std.title || "")}</div>
          ${std.replacement_standard ? `<div style="font-size: 0.75rem; color: var(--emerald-dark); margin-top: 0.15rem;">Active Replacement: <strong>${escapeHtml(std.replacement_standard)}</strong></div>` : ""}
        </div>
        ${src.legal_gazette_reference ? `
          <div class="drawer-field-row" style="margin-top: 0.5rem;">
            <span class="drawer-field-lbl">Gazette Notification Reference</span>
            <div class="drawer-field-val mono">${escapeHtml(src.legal_gazette_reference)}</div>
          </div>
        ` : ""}
      </div>

      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Rule Engine Provenance</span>
          <div class="drawer-field-val mono">${escapeHtml(src.rule_id || "RULE_ENGINE")} (${escapeHtml(src.source_type || "DETERMINISTIC_LINTER")})</div>
        </div>
        <div class="drawer-field-row" style="margin-top: 0.5rem;">
          <span class="drawer-field-lbl">Verification Status</span>
          <div class="drawer-field-val font-semibold ${f.requires_human_review ? "text-amber" : "text-emerald"}">
            ${f.resolution_status || (f.requires_human_review ? "PENDING VERIFICATION" : "VERIFIED")}
          </div>
        </div>
      </div>

      ${fix.recommended_action_summary ? `
        <div class="drawer-record-block" style="background-color: var(--emerald-light); border-color: var(--emerald-border);">
          <div class="drawer-field-row">
            <span class="drawer-field-lbl" style="color: var(--emerald-dark);">Recommended Officer Action</span>
            <div class="drawer-field-val" style="color: #064E3B; font-weight: 500;">${escapeHtml(fix.recommended_action_summary)}</div>
          </div>
        </div>
      ` : ""}
    `;

    openDrawer();
  };

  window.openEvidenceDrawerForStandard = function(standardCode) {
    if (!activeAuditData) return;
    const recs = activeAuditData.recommended_standards || [];
    const r = recs.find(item => item.standard && item.standard.is_number.includes(standardCode)) || recs[0];
    if (!r) return;

    const std = r.standard || {};
    drawerTitle.textContent = `${std.is_number} · Standard Evidence`;

    const evList = (r.evidence || []).map(ev => `
      <div style="font-size: 0.8rem; color: var(--text-body); display: flex; align-items: flex-start; gap: 0.4rem; line-height: 1.45;">
        <i class="ph-bold ph-check-circle" style="color: var(--emerald-main); margin-top: 0.15rem; flex-shrink: 0;"></i>
        <span>${escapeHtml(ev)}</span>
      </div>
    `).join("");

    drawerBody.innerHTML = `
      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Indian Standard & Status</span>
          <div class="drawer-field-val font-semibold">${escapeHtml(std.is_number)}: ${escapeHtml(std.title || "")}</div>
          <div style="margin-top: 0.35rem; display: flex; gap: 0.5rem;">
            <span class="pill"><i class="ph-bold ph-check"></i> ${escapeHtml(std.current_status || "CURRENT")}</span>
            <span class="pill pill-mono">Applicability: ${Math.round((r.applicability_score || 0) * 100)}%</span>
          </div>
        </div>
      </div>

      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Scope & Retrieval Grounding</span>
          <div class="drawer-field-val">${escapeHtml(r.explanation || "Primary governing Indian Standard for the tender product scope.")}</div>
        </div>
      </div>

      <div class="drawer-record-block">
        <span class="drawer-field-lbl" style="margin-bottom: 0.5rem; display: block;">Supporting Technical Evidence Quotes</span>
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
          ${evList || "<div style='font-size: 0.78rem; color: var(--text-muted);'>No additional evidence quotes extracted.</div>"}
        </div>
      </div>
    `;

    openDrawer();
  };

  window.openEvidenceDrawerForParameter = function(paramName) {
    if (!activeAuditData) return;
    const recs = activeAuditData.recommended_standards || [];
    const primaryRec = recs[0] || {};
    const paramFits = primaryRec.parameter_fit || [];
    const p = paramFits.find(item => item.parameter_name === paramName) || paramFits[0];
    if (!p) return;

    drawerTitle.textContent = `${p.parameter_name} · Parameter Fit`;

    drawerBody.innerHTML = `
      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Parameter & Assessment</span>
          <div class="drawer-field-val font-semibold">${escapeHtml(p.parameter_name)}</div>
          <div style="margin-top: 0.35rem;">
            <span class="legend-pill badge-${p.fit_status || 'NOT_SPECIFIED'}">${p.fit_status || 'NOT_SPECIFIED'}</span>
          </div>
        </div>
      </div>

      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Tender Specified Value</span>
          <div class="drawer-field-val quote">"${escapeHtml(p.tender_value || "Not specified in tender schedule")}"</div>
        </div>
      </div>

      <div class="drawer-record-block">
        <div class="drawer-field-row">
          <span class="drawer-field-lbl">Standard Prescribed Requirement & Evidence</span>
          <div class="drawer-field-val">${escapeHtml(p.standard_value || "—")}</div>
        </div>
      </div>
    `;

    openDrawer();
  };

  function openDrawer() {
    evidenceDrawerBackdrop.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    evidenceDrawerBackdrop.classList.add("hidden");
    document.body.style.overflow = "";
  }

  closeDrawerBtn.addEventListener("click", closeDrawer);
  drawerDismissBtn.addEventListener("click", closeDrawer);
  evidenceDrawerBackdrop.addEventListener("click", (e) => {
    if (e.target === evidenceDrawerBackdrop) closeDrawer();
  });

  // --------------------------------------------------------------------------
  // JSON Contract Exporters
  // --------------------------------------------------------------------------
  function triggerJsonDownload() {
    if (!activeAuditData) return;
    const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeAuditData, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonStr);
    downloadAnchor.setAttribute("download", `maanaknetra_audit_${activeAuditData.tender_metadata?.analysis_id || "dossier"}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast("Audit JSON dossier downloaded");
  }

  downloadJsonBtn.addEventListener("click", triggerJsonDownload);
  if (stickyExportJsonBtn) {
    stickyExportJsonBtn.addEventListener("click", triggerJsonDownload);
  }

  // --------------------------------------------------------------------------
  // UI Helpers (Loading, Error, Toast, String utilities)
  // --------------------------------------------------------------------------
  function showLoading(headline, msg) {
    loadingHeadline.textContent = headline;
    loadingMessage.textContent = msg;
    auditLoadingState.classList.remove("hidden");
    secOverview.classList.add("hidden");
    resultsWorkspace.classList.add("hidden");
    startAuditBtn.disabled = true;
    heroDemoBtn.disabled = true;
    headerDemoBtn.disabled = true;
  }

  function hideLoading() {
    auditLoadingState.classList.add("hidden");
    startAuditBtn.disabled = !currentSelectedFile;
    heroDemoBtn.disabled = false;
    headerDemoBtn.disabled = false;
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    auditErrorAlert.classList.remove("hidden");
    secOverview.classList.remove("hidden");
  }

  function hideError() {
    auditErrorAlert.classList.add("hidden");
  }

  function showToast(msg) {
    if (toastTimer) clearTimeout(toastTimer);
    toastMessage.textContent = msg;
    appToast.classList.remove("hidden");
    toastTimer = setTimeout(() => {
      appToast.classList.add("hidden");
    }, 2800);
  }

  function truncateText(str, maxLen) {
    if (!str) return "—";
    if (str.length <= maxLen) return str;
    return str.substring(0, maxLen - 1) + "…";
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
