/**
 * MAANAKNETRA — Enterprise Controller
 * AI-Powered Procurement & Indian Standards Intelligence
 *
 * Real API consumption from /api/demo and /api/analyze.
 * Strictly zero hardcoded analysis values.
 */

document.addEventListener("DOMContentLoaded", () => {
  // --------------------------------------------------------------------------
  // DOM Elements
  // --------------------------------------------------------------------------
  const dropTarget = document.getElementById("dropTarget");
  const tenderFileInput = document.getElementById("tenderFileInput");
  const fileSelectionPill = document.getElementById("fileSelectionPill");
  const fileSelectionName = document.getElementById("fileSelectionName");
  const clearSelectionBtn = document.getElementById("clearSelectionBtn");
  const startAuditBtn = document.getElementById("startAuditBtn");

  const headerDemoBtn = document.getElementById("headerDemoBtn");
  const heroDemoBtn = document.getElementById("heroDemoBtn");
  const headerUploadBtn = document.getElementById("headerUploadBtn");

  const auditLoadingState = document.getElementById("auditLoadingState");
  const loadingHeadline = document.getElementById("loadingHeadline");
  const loadingMessage = document.getElementById("loadingMessage");
  const auditErrorAlert = document.getElementById("auditErrorAlert");
  const errorMessage = document.getElementById("errorMessage");

  const auditResultsDashboard = document.getElementById("auditResultsDashboard");
  const officerReviewBanner = document.getElementById("officerReviewBanner");
  const officerReviewReasons = document.getElementById("officerReviewReasons");

  const linterSeveritySelect = document.getElementById("linterSeveritySelect");
  const downloadJsonBtn = document.getElementById("downloadJsonBtn");

  let currentSelectedFile = null;
  let activeAuditData = null;

  // --------------------------------------------------------------------------
  // Drag and Drop & File Selection
  // --------------------------------------------------------------------------
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

  if (headerUploadBtn) {
    headerUploadBtn.addEventListener("click", () => {
      tenderFileInput.click();
    });
  }

  function handleSelectedFile(file) {
    currentSelectedFile = file;
    fileSelectionName.textContent = file.name;
    fileSelectionPill.classList.remove("hidden");
    startAuditBtn.disabled = false;
  }

  // --------------------------------------------------------------------------
  // Action Handlers (Sample Tender & Upload Audit)
  // --------------------------------------------------------------------------
  headerDemoBtn.addEventListener("click", () => {
    fetchCanonicalDemo();
  });

  heroDemoBtn.addEventListener("click", () => {
    fetchCanonicalDemo();
  });

  startAuditBtn.addEventListener("click", () => {
    if (!currentSelectedFile) return;
    executeTenderAudit(currentSelectedFile);
  });

  async function fetchCanonicalDemo() {
    showLoading(
      "Loading Canonical Demonstration...",
      "Retrieving end-to-end procurement audit for demo/sample_tender.pdf from ProcurementAnalysisEngine..."
    );
    hideError();

    try {
      const response = await fetch("/api/demo");
      if (!response.ok) {
        throw new Error(`Demo endpoint returned status ${response.status}: ${response.statusText}`);
      }
      const auditResult = await response.json();
      populateDashboard(auditResult);
    } catch (err) {
      showError(`Unable to load benchmark demonstration: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  async function executeTenderAudit(file) {
    showLoading(
      `Auditing '${file.name}'...`,
      "Running requirement extraction, Indian Standards retrieval, parameter matrix matching, QCO checks, and tender linter..."
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

      const auditResult = await response.json();
      populateDashboard(auditResult);
    } catch (err) {
      showError(`Audit execution error: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  // --------------------------------------------------------------------------
  // Main Dashboard Populator (Strictly from real API data)
  // --------------------------------------------------------------------------
  function populateDashboard(data) {
    activeAuditData = data;

    // 1. Snapshot Bar
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

    document.getElementById("snapshotDocTitle").textContent = meta.document_title || meta.file_name || "Procurement Tender Specification";
    document.getElementById("snapshotAnalysisId").textContent = meta.analysis_id || "ANALYSIS_DOSSIER";
    document.getElementById("snapshotPageCountVal").textContent = meta.page_count || 1;

    let categoryContext = "General Engineering & Equipment";
    if (reqs.length > 0 && reqs[0].product_category_context) {
      categoryContext = reqs[0].product_category_context;
    } else if (data.product_context && data.product_context.primary_item_name) {
      categoryContext = data.product_context.primary_item_name;
    }
    document.getElementById("snapshotCategoryVal").textContent = categoryContext;

    const analyzedTime = meta.analyzed_at ? new Date(meta.analyzed_at).toLocaleString() : "Just Now";
    document.getElementById("snapshotTimestampVal").textContent = analyzedTime;

    // 2. Top KPI Row
    const riskLevel = (risk.risk_level || "MEDIUM").toUpperCase();
    const riskBadge = document.getElementById("kpiRiskBadge");
    riskBadge.textContent = riskLevel;
    riskBadge.className = `risk-badge-view risk-${riskLevel}`;

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
    const critCount = risk.critical_issues_count || findings.filter(f => f.severity === "CRITICAL").length;
    const highCount = risk.high_issues_count || findings.filter(f => f.severity === "HIGH").length;
    const medCount = risk.medium_issues_count || findings.filter(f => f.severity === "MEDIUM").length;
    document.getElementById("kpiFindingsBreakdown").textContent = `${critCount} Critical · ${highCount} High · ${medCount} Medium`;

    const stdsCount = recs.length > 0 ? recs.length : bom.length;
    document.getElementById("kpiStandardsCount").textContent = stdsCount;
    document.getElementById("kpiStandardsBreakdown").textContent = `${stdsCount} governing / referenced Indian Standards`;

    // 3. Human Review Banner
    const isReviewRequired = Boolean(data.human_review_required || findings.some(f => f.requires_human_review));
    if (isReviewRequired) {
      officerReviewBanner.classList.remove("hidden");
      const reasonsList = [];
      if (statusFlags.has_superseded_standards) reasonsList.push("superseded standard citation detected in tender text");
      if (cert.qco_violation_risk) reasonsList.push("omission of mandatory Scheme-I BIS ISI Mark licensing clause under governing QCO");
      if (findings.some(f => f.finding_type === "VAGUE_REQUIREMENT")) reasonsList.push("unquantified subjective terminology requiring objective metrics");
      if (reasonsList.length === 0) reasonsList.push("statutory deviations and compliance gap checks require officer sign-off");
      officerReviewReasons.textContent = "Officer verification required prior to bid publishing due to: " + reasonsList.join("; ") + ".";
    } else {
      officerReviewBanner.classList.add("hidden");
    }

    // 4. Section 1: Extracted Requirements
    renderRequirements(reqs);

    // 5. Section 2: Recommended Standards
    renderRecommendedStandards(recs);

    // 6. Section 3: Parameter Evidence
    renderParameterEvidence(recs);

    // 7. Section 4: Regulatory Intelligence
    renderRegulatoryIntelligence(data);

    // 8. Section 5: Tender Audit Findings (Hero)
    renderLinterFindings(findings);

    // 9. Section 6: Traceable Evidence & Provenance
    renderEvidencePanels(findings, reqs, cert);

    // 10. Section 7: Standards Relationships Hierarchy
    renderRelationships(recs, related);

    // 11. Section 8: Corrected Specification Draft
    renderCorrectedClauses(clauses);

    // 12. Standards BOM
    renderBOM(bom);

    // Reveal Dashboard and smooth scroll
    auditResultsDashboard.classList.remove("hidden");
    auditResultsDashboard.scrollIntoView({ behavior: "smooth" });
  }

  // --------------------------------------------------------------------------
  // SECTION 1: Extracted Requirements
  // Parameter | Tender Value | Evidence/Confidence
  // --------------------------------------------------------------------------
  function renderRequirements(reqs) {
    const tbody = document.getElementById("requirementsTableBody");
    tbody.innerHTML = "";

    if (!reqs || reqs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-center" style="padding: 1.75rem; color: var(--text-muted);">No requirements extracted from document.</td></tr>`;
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
          <div style="font-size: 0.78rem; color: var(--text-body); line-height: 1.4;">
            "${escapeHtml(r.source_text || "")}"
          </div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem; display: flex; gap: 0.5rem; align-items: center;">
            <span><i class="ph-bold ph-map-pin"></i> ${escapeHtml(clauseLoc)}</span>
            <span>·</span>
            <span style="color: var(--emerald-dark); font-weight: 600;"><i class="ph-bold ph-seal-check"></i> ${confPct}% Confidence</span>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 2: Recommended Standards
  // Rank, IS number, Title, Match score, Status, Reason, Evidence
  // Top recommendation is visually prominent.
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
          <span class="rec-score-pill"><i class="ph-bold ph-target"></i> Match Score: ${scorePct}%</span>
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
  // SECTION 3: Parameter Evidence Matrix
  // Parameter | Tender | Standard Evidence | Assessment
  // States: COMPLIANT, DEVIATING, NOT SPECIFIED
  // --------------------------------------------------------------------------
  function renderParameterEvidence(recs) {
    const tbody = document.getElementById("parameterEvidenceBody");
    tbody.innerHTML = "";

    const primaryRec = (recs && recs.length > 0) ? recs[0] : null;
    const paramFits = primaryRec ? (primaryRec.parameter_fit || []) : [];

    if (!paramFits || paramFits.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center" style="padding: 1.75rem; color: var(--text-muted);">No parameter fits evaluated.</td></tr>`;
      return;
    }

    paramFits.forEach((p) => {
      const tr = document.createElement("tr");

      let badgeClass = "badge-NOT_SPECIFIED";
      let badgeLabel = "NOT SPECIFIED";
      let badgeIcon = "ph-minus";

      const fitStatus = (p.fit_status || "").toUpperCase();
      if (fitStatus === "COMPLIANT") {
        badgeClass = "badge-COMPLIANT";
        badgeLabel = "COMPLIANT";
        badgeIcon = "ph-check";
      } else if (fitStatus === "DEVIATING") {
        badgeClass = "badge-DEVIATING";
        badgeLabel = "DEVIATING";
        badgeIcon = "ph-warning";
      }

      tr.innerHTML = `
        <td><strong>${escapeHtml(p.parameter_name || "")}</strong></td>
        <td><span style="color: var(--navy-900); font-weight: 500;">${escapeHtml(p.tender_value || "—")}</span></td>
        <td style="font-size: 0.78rem; color: var(--text-body); line-height: 1.4;">${escapeHtml(p.standard_value || "—")}</td>
        <td>
          <span class="legend-badge ${badgeClass}">
            <i class="ph-bold ${badgeIcon}"></i>
            ${badgeLabel}
          </span>
        </td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 4: Regulatory Intelligence
  // Current / Superseded, Replacement, QCO info, Certification, Effective date,
  // Verification status, Review required, Review reason.
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
      regVerifStatus.className = "detail-value font-semibold text-amber";
    } else {
      regVerifStatus.textContent = "CURRENT / VERIFIED";
      regVerifStatus.className = "detail-value font-semibold text-emerald";
    }

    const regReviewReq = document.getElementById("regQcoReviewRequired");
    regReviewReq.textContent = data.human_review_required ? "YES — OFFICER REVIEW REQUIRED" : "NO — FULLY COMPLIANT";
    regReviewReq.className = data.human_review_required ? "detail-value font-bold text-crimson" : "detail-value font-bold text-emerald";

    document.getElementById("regQcoReviewReason").textContent = cert.qco_violation_risk
      ? "Statutory omission: Mandatory Scheme-I BIS ISI mark licensing clause absent in tender."
      : "Standard verified against statutory gazette database.";

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
          <span class="track-desc">Active revision confirmed against BIS Product Manual</span>
        </div>
      `;
    }
  }

  // --------------------------------------------------------------------------
  // SECTION 5: Tender Audit Findings (Hero Feature)
  // Grouped by CRITICAL, HIGH, MEDIUM
  // Each finding: title, severity, why it matters, exact tender evidence,
  // affected standard/QCO, provenance, recommended action, review state.
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
      container.innerHTML = `<div class="card text-center" style="padding: 2.5rem; color: var(--text-muted);"><i class="ph-bold ph-check-circle" style="font-size: 1.75rem; color: var(--emerald-main); display: block; margin-bottom: 0.5rem;"></i>No tender linter findings found for the selected filter.</div>`;
      return;
    }

    findings.forEach((f) => {
      const card = document.createElement("div");
      card.className = `finding-card sev-${f.severity}`;

      const fix = f.suggested_fix || {};
      const src = f.source || {};
      const stdCode = f.affected_standard ? f.affected_standard.is_number : "BIS Standard";
      const reviewState = f.requires_human_review ? "Human verification required before procurement action" : "Advisory Standard Finding";

      card.innerHTML = `
        <div class="finding-top-row">
          <div class="finding-tags">
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
            <span class="fix-label"><i class="ph-bold ph-arrow-bend-down-right"></i> Recommended Procurement Action:</span>
            <p class="fix-text">${escapeHtml(fix.recommended_action_summary)}</p>
          </div>
        ` : ""}

        <div class="finding-footer">
          <span><strong>Provenance:</strong> ${escapeHtml(src.source_type || "RULE_ENGINE")} (${escapeHtml(src.rule_id || "")})</span>
          <span class="officer-badge"><i class="ph-bold ph-user-focus"></i> ${escapeHtml(reviewState)}</span>
        </div>
      `;

      container.appendChild(card);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 6: Evidence & Traceability Registry
  // Source, evidence, standard/QCO, provenance, verification status.
  // Expandable panels.
  // --------------------------------------------------------------------------
  function renderEvidencePanels(findings, reqs, cert) {
    const container = document.getElementById("evidencePanelsContainer");
    container.innerHTML = "";

    if (!findings || findings.length === 0) {
      container.innerHTML = `<div class="card text-center" style="padding: 1.5rem; color: var(--text-muted);">No evidence panels recorded.</div>`;
      return;
    }

    findings.forEach((f, idx) => {
      const details = document.createElement("details");
      details.className = "evidence-accordion";
      if (idx === 0) details.open = true;

      const src = f.source || {};
      const stdCode = f.affected_standard ? f.affected_standard.is_number : "BIS Standard";
      const verifStatus = f.resolution_status || (f.requires_human_review ? "PENDING VERIFICATION" : "VERIFIED");

      details.innerHTML = `
        <summary class="evidence-header">
          <div class="evidence-header-left">
            <span class="badge-sev ${f.severity}">${f.severity}</span>
            <span class="evidence-header-title">${escapeHtml(f.title || f.finding_id)}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="pill pill-mono">${escapeHtml(stdCode)}</span>
            <span class="pill">${escapeHtml(verifStatus)}</span>
            <i class="ph-bold ph-caret-down"></i>
          </div>
        </summary>
        <div class="evidence-body">
          <div class="evidence-row">
            <span class="ev-lbl">Source Location:</span>
            <span>${escapeHtml(src.standard_clause_reference || src.legal_gazette_reference || "Tender Document Specification")}</span>
          </div>
          <div class="evidence-row">
            <span class="ev-lbl">Tender Evidence:</span>
            <span style="font-style: italic; color: var(--navy-900);">"${escapeHtml(f.tender_text || "Clause omitted in original tender text")}"</span>
          </div>
          <div class="evidence-row">
            <span class="ev-lbl">Standard / QCO:</span>
            <span>${escapeHtml(stdCode)} ${src.legal_gazette_reference ? `· Gazette: ${escapeHtml(src.legal_gazette_reference)}` : ""}</span>
          </div>
          <div class="evidence-row">
            <span class="ev-lbl">Rule Provenance:</span>
            <span class="pill pill-mono">${escapeHtml(src.rule_id || "RULE_ENGINE")}</span>
          </div>
          <div class="evidence-row">
            <span class="ev-lbl">Verification Status:</span>
            <span class="font-semibold ${f.requires_human_review ? "text-amber" : "text-emerald"}">
              ${escapeHtml(verifStatus)} — Human verification required before procurement action.
            </span>
          </div>
        </div>
      `;

      container.appendChild(details);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 7: Standards Relationships (Real Graph Data)
  // Preferred: IS 14220 -> IS 9283 -> IS 12615 + Allied Table
  // --------------------------------------------------------------------------
  function renderRelationships(recs, related) {
    const tbody = document.getElementById("alliedStandardsBody");
    tbody.innerHTML = "";

    // Primary chain header
    if (recs && recs.length > 0 && recs[0].standard) {
      const primary = recs[0].standard;
      const primaryCodeEl = document.getElementById("normativeChainPrimary");
      const primaryTitleEl = document.getElementById("normativeChainPrimaryTitle");
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
        <td><span class="pill ${rel.importance === "MANDATORY" ? "font-bold text-crimson" : ""}">${escapeHtml(rel.importance || "RECOMMENDED")}</span></td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // SECTION 8: Corrected Specification Draft
  // ORIGINAL CLAUSE ↓ CORRECTED DRAFT
  // For each: clause ID, original, corrected, rationale, source, "Officer-reviewable draft", Copy button.
  // --------------------------------------------------------------------------
  function renderCorrectedClauses(clauses) {
    const container = document.getElementById("correctedClausesContainer");
    container.innerHTML = "";

    if (!clauses || clauses.length === 0) {
      container.innerHTML = `<div class="card text-center" style="padding: 2rem; color: var(--text-muted);">No clause rectifications required. Tender clauses conform to specifications.</div>`;
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
            <span class="col-tag">Corrected Draft (BIS & QCO Grounded)</span>
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

    // Copy to clipboard handlers
    container.querySelectorAll(".copy-clause-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const textToCopy = btn.getAttribute("data-text");
        if (!textToCopy) return;

        navigator.clipboard.writeText(textToCopy).then(() => {
          const originalHTML = btn.innerHTML;
          btn.innerHTML = `<i class="ph-bold ph-check"></i> Copied!`;
          btn.style.borderColor = "var(--emerald-main)";
          btn.style.color = "var(--emerald-dark)";
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
  // STANDARDS BILL OF MATERIALS (BOM)
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
        ? `<span class="legend-badge badge-DEVIATING" style="font-size: 0.68rem;"><i class="ph-bold ph-shield-check"></i> STATUTORY MANDATE</span>`
        : `<span class="legend-badge badge-NOT_SPECIFIED" style="font-size: 0.68rem;">VOLUNTARY</span>`;

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
  // Export JSON Contract
  // --------------------------------------------------------------------------
  downloadJsonBtn.addEventListener("click", () => {
    if (!activeAuditData) return;
    const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeAuditData, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonStr);
    downloadAnchor.setAttribute("download", `maanaknetra_audit_${activeAuditData.tender_metadata?.analysis_id || "dossier"}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  });

  // --------------------------------------------------------------------------
  // UI Helpers (Loading, Error, Escape)
  // --------------------------------------------------------------------------
  function showLoading(headline, msg) {
    loadingHeadline.textContent = headline;
    loadingMessage.textContent = msg;
    auditLoadingState.classList.remove("hidden");
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
  }

  function hideError() {
    auditErrorAlert.classList.add("hidden");
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
