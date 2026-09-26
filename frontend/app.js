/**
 * MAANAKNETRA — Web Application Controller
 * Handles file upload, executes API requests to /api/analyze and /api/demo,
 * and renders explainable procurement intelligence dashboard.
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const selectedFileInfo = document.getElementById("selectedFileInfo");
  const selectedFileName = document.getElementById("selectedFileName");
  const clearFileBtn = document.getElementById("clearFileBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const demoBtn = document.getElementById("demoBtn");
  const quickDemoBtn = document.getElementById("quickDemoBtn");

  const loadingState = document.getElementById("loadingState");
  const loadingTitle = document.getElementById("loadingTitle");
  const loadingSubtitle = document.getElementById("loadingSubtitle");
  const errorAlert = document.getElementById("errorAlert");
  const errorMessage = document.getElementById("errorMessage");

  const resultsSection = document.getElementById("resultsSection");
  const humanReviewBanner = document.getElementById("humanReviewBanner");
  const humanReviewReasons = document.getElementById("humanReviewReasons");

  const exportJsonBtn = document.getElementById("exportJsonBtn");
  const severityFilter = document.getElementById("severityFilter");

  let currentFile = null;
  let currentAnalysisData = null;

  // --------------------------------------------------------------------------
  // File Upload & Drag-and-Drop Handlers
  // --------------------------------------------------------------------------
  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("dragover");
    }, false);
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  clearFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    currentFile = null;
    fileInput.value = "";
    selectedFileInfo.classList.add("hidden");
    analyzeBtn.disabled = true;
  });

  function handleFileSelected(file) {
    currentFile = file;
    selectedFileName.textContent = file.name;
    selectedFileInfo.classList.remove("hidden");
    analyzeBtn.disabled = false;
  }

  // --------------------------------------------------------------------------
  // Audit Actions Trigger
  // --------------------------------------------------------------------------
  analyzeBtn.addEventListener("click", () => {
    if (!currentFile) return;
    executeAnalysis(currentFile);
  });

  demoBtn.addEventListener("click", () => {
    loadCanonicalDemo();
  });

  quickDemoBtn.addEventListener("click", () => {
    loadCanonicalDemo();
  });

  // --------------------------------------------------------------------------
  // API Calls
  // --------------------------------------------------------------------------
  async function loadCanonicalDemo() {
    showLoading(
      "Loading Canonical Demonstration...",
      "Retrieving end-to-end audit for demo/sample_tender.pdf (IS 14220 Openwell Submersible Pumpset)..."
    );
    hideError();

    try {
      const response = await fetch("/api/demo");
      if (!response.ok) {
        throw new Error(`Demo endpoint returned status ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      renderDashboard(data);
    } catch (err) {
      showError(`Failed to load demonstration: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  async function executeAnalysis(file) {
    showLoading(
      `Auditing '${file.name}'...`,
      "Extracting technical specifications, traversing standards knowledge graph, and verifying statutory QCO compliance..."
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
        const errorJson = await response.json().catch(() => ({}));
        throw new Error(errorJson.detail || `Analysis failed with status ${response.status}`);
      }

      const data = await response.json();
      renderDashboard(data);
    } catch (err) {
      showError(`Audit processing error: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  // --------------------------------------------------------------------------
  // Dashboard Renderer
  // --------------------------------------------------------------------------
  function renderDashboard(data) {
    currentAnalysisData = data;

    // 1. Metadata
    const meta = data.tender_metadata || {};
    document.getElementById("resDocTitle").textContent = meta.document_title || "Procurement Tender Document";
    document.getElementById("resAnalysisId").textContent = meta.analysis_id || "ANALYSIS_UNKNOWN";
    document.getElementById("resPageCount").innerHTML = `<i class="ph-bold ph-file-text"></i> ${meta.page_count || 1} Pages`;
    
    const analyzedTime = meta.analyzed_at ? new Date(meta.analyzed_at).toLocaleTimeString() : "Just Now";
    document.getElementById("resTimestamp").innerHTML = `<i class="ph-bold ph-clock"></i> ${analyzedTime}`;
    
    const dept = meta.procuring_department || "State / Central Procurement Dept";
    document.getElementById("resDept").innerHTML = `<i class="ph-bold ph-buildings"></i> ${dept}`;

    // 2. Risk & Overall Procurement KPIs
    const risk = data.risk_indicator || {};
    const riskLevel = risk.risk_level || "MEDIUM";
    const riskBadge = document.getElementById("resRiskBadge");
    riskBadge.textContent = riskLevel;
    riskBadge.className = `risk-badge-large risk-${riskLevel}`;

    const score = Math.round(risk.compliance_score !== undefined ? risk.compliance_score : 50);
    document.getElementById("resComplianceScore").textContent = `${score}%`;
    document.getElementById("resScoreProgress").style.width = `${score}%`;
    document.getElementById("resRiskSummary").textContent = risk.summary || "Specification evaluation complete.";

    // 3. Lifecycle Flags
    const statusFlags = data.status_flags || {};
    const supersededCount = statusFlags.superseded_count || 0;
    const hasSuperseded = statusFlags.has_superseded_standards || false;
    const supersededDesc = document.getElementById("resSupersededDesc");
    const supersededIcon = document.getElementById("resSupersededIcon");

    if (hasSuperseded) {
      supersededIcon.className = "check-icon";
      supersededIcon.innerHTML = `<i class="ph-bold ph-warning"></i>`;
      supersededDesc.textContent = `${supersededCount} citation(s) reference superseded Indian Standards`;
    } else {
      supersededIcon.className = "check-icon status-ok";
      supersededIcon.innerHTML = `<i class="ph-bold ph-check"></i>`;
      supersededDesc.textContent = "All cited standards are active and current";
    }

    const withdrawnCount = statusFlags.withdrawn_count || 0;
    const hasWithdrawn = statusFlags.has_withdrawn_standards || false;
    const withdrawnDesc = document.getElementById("resWithdrawnDesc");
    const withdrawnIcon = document.getElementById("resWithdrawnIcon");

    if (hasWithdrawn) {
      withdrawnIcon.className = "check-icon";
      withdrawnIcon.innerHTML = `<i class="ph-bold ph-x"></i>`;
      withdrawnDesc.textContent = `${withdrawnCount} withdrawn standards detected`;
    } else {
      withdrawnIcon.className = "check-icon status-ok";
      withdrawnIcon.innerHTML = `<i class="ph-bold ph-check"></i>`;
      withdrawnDesc.textContent = "0 withdrawn standards cited";
    }

    // 4. QCO & Certification Flags
    const certFlags = data.certification_flags || {};
    const qcoPill = document.getElementById("resQcoPill");
    const qcoDetail = document.getElementById("resQcoDetail");
    const qcoApplicable = certFlags.qco_mandate_applicable || false;
    const qcoRisk = certFlags.qco_violation_risk || false;
    const isiPresent = certFlags.mandatory_isi_clause_present || false;

    if (qcoRisk) {
      qcoPill.className = "qco-indicator-pill danger";
      qcoPill.innerHTML = `<i class="ph-bold ph-x-circle"></i><span>QCO VIOLATION RISK DETECTED</span>`;
      qcoDetail.innerHTML = `<strong>Statutory QCO is in force</strong> for this product. The tender specification <strong>omits the mandatory Scheme-I BIS ISI Mark licensing requirement</strong>.`;
    } else if (qcoApplicable && isiPresent) {
      qcoPill.className = "qco-indicator-pill success";
      qcoPill.innerHTML = `<i class="ph-bold ph-check-circle"></i><span>QCO COMPLIANT</span>`;
      qcoDetail.innerHTML = `Statutory QCO in force; mandatory BIS Standard Mark requirement verified in tender text.`;
    } else {
      qcoPill.className = "qco-indicator-pill success";
      qcoPill.innerHTML = `<i class="ph-bold ph-info"></i><span>VOLUNTARY SCHEME</span>`;
      qcoDetail.innerHTML = `No mandatory statutory Quality Control Order restriction found in gazetted database for this product scope.`;
    }

    // 5. Human Review Banner
    const reviewRequired = data.human_review_required || false;
    if (reviewRequired) {
      humanReviewBanner.classList.remove("hidden");
      let reviewText = "Manual review by the procurement officer is required prior to tender publication due to: ";
      const reasons = [];
      if (hasSuperseded) reasons.push("superseded standard citation (IS 14220:1994)");
      if (qcoRisk) reasons.push("omission of statutory QCO BIS ISI Mark licensing clause");
      if ((data.findings || []).some(f => f.finding_type === "VAGUE_REQUIREMENT")) {
        reasons.push("unquantified subjective terminology");
      }
      humanReviewReasons.textContent = reviewText + (reasons.join(", ") || "auditable discrepancies") + ".";
    } else {
      humanReviewBanner.classList.add("hidden");
    }

    // 6. Tab Counts
    const findingsList = data.findings || [];
    const clausesList = data.corrected_clause || data.corrected_clauses || [];
    const bomList = data.standards_bom || [];
    const recsList = data.recommended_standards || [];
    const reqsList = data.extracted_requirements || [];

    document.getElementById("tabFindingsCount").textContent = findingsList.length;
    document.getElementById("tabClausesCount").textContent = clausesList.length;
    document.getElementById("tabBomCount").textContent = bomList.length;
    document.getElementById("tabRecsCount").textContent = recsList.length;
    document.getElementById("tabReqsCount").textContent = reqsList.length;

    // 7. Render Tabs Content
    renderFindings(findingsList);
    renderCorrectedClauses(clausesList);
    renderBOM(bomList);
    renderRecommendations(recsList);
    renderGraph(data.graph_summary || {}, data.related_standards || []);
    renderRequirements(reqsList);

    // Reveal results and scroll smoothly
    resultsSection.classList.remove("hidden");
    resultsSection.scrollIntoView({ behavior: "smooth" });
  }

  // --------------------------------------------------------------------------
  // Tab Switching
  // --------------------------------------------------------------------------
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });

  // --------------------------------------------------------------------------
  // Render: Findings
  // --------------------------------------------------------------------------
  severityFilter.addEventListener("change", () => {
    if (!currentAnalysisData) return;
    const filter = severityFilter.value;
    const allFindings = currentAnalysisData.findings || [];
    if (filter === "ALL") {
      renderFindings(allFindings);
    } else {
      renderFindings(allFindings.filter(f => f.severity === filter));
    }
  });

  function renderFindings(findings) {
    const container = document.getElementById("findingsContainer");
    container.innerHTML = "";

    if (!findings || findings.length === 0) {
      container.innerHTML = `
        <div class="card text-center" style="padding: 2rem; color: var(--text-muted);">
          <i class="ph-bold ph-check-circle" style="font-size: 2rem; color: var(--status-success); margin-bottom: 0.5rem;"></i>
          <p>No audit findings for the selected filter.</p>
        </div>
      `;
      return;
    }

    findings.forEach(f => {
      const card = document.createElement("div");
      card.className = `finding-card sev-${f.severity}`;

      const fix = f.suggested_fix || {};
      const src = f.source || {};
      const stdCode = f.affected_standard ? f.affected_standard.is_number : "General";

      card.innerHTML = `
        <div class="finding-header">
          <div class="finding-badges">
            <span class="sev-badge ${f.severity}">${f.severity}</span>
            <span class="type-badge">${f.finding_type}</span>
            <span class="tag tag-mono">${f.finding_id}</span>
          </div>
          <span class="tag"><i class="ph-bold ph-bookmark"></i> ${escapeHtml(stdCode)}</span>
        </div>

        <h4 class="finding-title">${escapeHtml(f.title || "Audit Finding")}</h4>

        ${f.tender_text ? `
          <div class="finding-evidence-quote">
            <strong>Tender Evidence:</strong> "${escapeHtml(f.tender_text)}"
          </div>
        ` : ""}

        <p class="finding-explanation">${escapeHtml(f.explanation || "")}</p>

        ${fix.recommended_action_summary ? `
          <div class="finding-fix-box">
            <span class="fix-label">Recommended Action:</span>
            <p class="fix-text">${escapeHtml(fix.recommended_action_summary)}</p>
          </div>
        ` : ""}

        <div class="finding-footer-meta">
          <span><strong>Source / Rule:</strong> ${escapeHtml(src.source_type || "RULE_ENGINE")} (${escapeHtml(src.rule_id || "")})</span>
          <span><strong>Human Review:</strong> ${f.requires_human_review ? "Mandatory Officer Sign-off" : "Advisory"}</span>
        </div>
      `;

      container.appendChild(card);
    });
  }

  // --------------------------------------------------------------------------
  // Render: Corrected Clauses
  // --------------------------------------------------------------------------
  function renderCorrectedClauses(clauses) {
    const container = document.getElementById("clausesContainer");
    container.innerHTML = "";

    if (!clauses || clauses.length === 0) {
      container.innerHTML = `
        <div class="card text-center" style="padding: 2rem; color: var(--text-muted);">
          <p>No clause rectifications required.</p>
        </div>
      `;
      return;
    }

    clauses.forEach(c => {
      const card = document.createElement("div");
      card.className = "clause-card";

      const linkedIds = (c.linked_finding_ids || []).join(", ");

      card.innerHTML = `
        <div class="clause-card-header">
          <div>
            <span class="clause-id-tag">${c.clause_id}</span>
            <span class="clause-ref-tag" style="margin-left: 0.5rem;"><i class="ph-bold ph-map-pin"></i> ${escapeHtml(c.source_clause_reference || "Specification")}</span>
          </div>
          <button class="btn btn-outline btn-sm copy-clause-btn" data-text="${escapeHtml(c.corrected_text)}">
            <i class="ph-bold ph-copy"></i> Copy Rectified Text
          </button>
        </div>

        <div class="clause-comparison-cols">
          <div class="comparison-col col-original">
            <span class="col-label">Original Tender Text (Flagged):</span>
            <p class="col-text">${escapeHtml(c.original_tender_text || "")}</p>
          </div>
          <div class="comparison-col col-corrected">
            <span class="col-label">Deterministic Rectified Draft (BIS & QCO Grounded):</span>
            <p class="col-text">${escapeHtml(c.corrected_text || "")}</p>
          </div>
        </div>

        <div class="clause-rationale-row">
          <span><strong>Rationale:</strong> ${escapeHtml(c.rationale || "")}</span>
          ${linkedIds ? `<span class="tag tag-mono">Triggered by: ${linkedIds}</span>` : ""}
        </div>
      `;

      container.appendChild(card);
    });

    // Copy to clipboard handlers
    container.querySelectorAll(".copy-clause-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const textToCopy = btn.getAttribute("data-text");
        navigator.clipboard.writeText(textToCopy).then(() => {
          const origHtml = btn.innerHTML;
          btn.innerHTML = `<i class="ph-bold ph-check"></i> Copied!`;
          setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
        });
      });
    });
  }

  // --------------------------------------------------------------------------
  // Render: Standards BOM
  // --------------------------------------------------------------------------
  function renderBOM(bom) {
    const tbody = document.getElementById("bomTableBody");
    tbody.innerHTML = "";

    if (!bom || bom.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No standards recorded.</td></tr>`;
      return;
    }

    bom.forEach(item => {
      const tr = document.createElement("tr");

      const qcoBadge = item.is_mandatory_qco
        ? `<span class="badge-pill badge-mandate-yes">STATUTORY MANDATE</span>`
        : `<span class="badge-pill badge-mandate-no">VOLUNTARY</span>`;

      let compClass = "badge-mandate-no";
      if (item.compliance_status === "ALREADY_CITED_CORRECTLY") compClass = "fit-COMPLIANT";
      else if (item.compliance_status === "CITED_BUT_OUTDATED") compClass = "fit-DEVIATING";

      tr.innerHTML = `
        <td><strong>${item.item_number || ""}</strong></td>
        <td><span class="tag tag-mono">${escapeHtml(item.is_number || "")}</span></td>
        <td>${escapeHtml(item.title || "")}</td>
        <td><span class="tag">${escapeHtml(item.role || "")}</span></td>
        <td>${qcoBadge}</td>
        <td><span class="badge-pill ${compClass}">${escapeHtml(item.compliance_status || "")}</span></td>
        <td>${escapeHtml(item.action_required || "")}</td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // Render: Recommendations & Parameters
  // --------------------------------------------------------------------------
  function renderRecommendations(recs) {
    const container = document.getElementById("recommendationsContainer");
    container.innerHTML = "";

    if (!recs || recs.length === 0) {
      container.innerHTML = `<div class="card text-center" style="padding: 2rem; color: var(--text-muted);">No standard recommendations available.</div>`;
      return;
    }

    recs.forEach(r => {
      const std = r.standard || {};
      const scorePct = Math.round((r.applicability_score || 0) * 100);

      const card = document.createElement("div");
      card.className = "rec-card";

      const paramRows = (r.parameter_fit || []).map(p => `
        <tr>
          <td><strong>${escapeHtml(p.parameter_name)}</strong></td>
          <td>${escapeHtml(p.tender_value || "")}</td>
          <td>${escapeHtml(p.standard_value || "")}</td>
          <td><span class="badge-pill fit-${p.fit_status}">${p.fit_status}</span></td>
        </tr>
      `).join("");

      card.innerHTML = `
        <div class="rec-header">
          <div>
            <span class="rec-code">${escapeHtml(std.is_number || "")}</span>
            <span class="tag" style="margin-left: 0.5rem;">Status: ${std.current_status || "CURRENT"}</span>
          </div>
          <span class="rec-score-pill">Applicability Match: ${scorePct}%</span>
        </div>

        <h4 class="rec-title">${escapeHtml(std.title || "")}</h4>
        <p class="rec-reason">${escapeHtml(r.explanation || "")}</p>

        <h5 style="font-size: 0.85rem; margin-bottom: 0.5rem; color: var(--gov-navy);">Parameter Fit & Verification Matrix</h5>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Technical Parameter</th>
                <th>Tender Specified Value</th>
                <th>Governing Standard Limit</th>
                <th>Compatibility Result</th>
              </tr>
            </thead>
            <tbody>
              ${paramRows || `<tr><td colspan="4" style="color: var(--text-muted);">No structured parameter comparisons.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;

      container.appendChild(card);
    });
  }

  // --------------------------------------------------------------------------
  // Render: Standards Graph
  // --------------------------------------------------------------------------
  function renderGraph(summary, related) {
    document.getElementById("graphNodesCount").textContent = summary.total_nodes || 0;
    document.getElementById("graphEdgesCount").textContent = summary.total_edges || 0;
    document.getElementById("graphPrimaryCluster").textContent = (summary.primary_clusters || []).join(", ") || "IS 14220";

    const tbody = document.getElementById("relatedStandardsBody");
    tbody.innerHTML = "";

    if (!related || related.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No allied relationships recorded.</td></tr>`;
      return;
    }

    related.forEach(rel => {
      const tr = document.createElement("tr");

      tr.innerHTML = `
        <td><span class="tag tag-mono">${escapeHtml(rel.is_number || "")}</span></td>
        <td><span class="tag">${escapeHtml(rel.relationship_type || "")}</span></td>
        <td>${escapeHtml(rel.governing_primary_standard || "")}</td>
        <td><span class="tag">${escapeHtml(rel.status || "CURRENT")}</span></td>
        <td><strong>${escapeHtml(rel.importance || "RECOMMENDED")}</strong></td>
        <td>${escapeHtml(rel.relevance_notes || "")}</td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // Render: Extracted Requirements
  // --------------------------------------------------------------------------
  function renderRequirements(reqs) {
    const tbody = document.getElementById("requirementsTableBody");
    tbody.innerHTML = "";

    if (!reqs || reqs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No technical requirements extracted.</td></tr>`;
      return;
    }

    reqs.forEach(req => {
      const tr = document.createElement("tr");
      const norm = req.normalized_value || {};
      const normStr = norm.numeric_value !== undefined ? `${norm.numeric_value} ${norm.unit || ""}` : (req.value || "");

      tr.innerHTML = `
        <td><span class="tag tag-mono">${escapeHtml(req.requirement_id || "")}</span></td>
        <td><span class="tag">${escapeHtml(req.category || "")}</span></td>
        <td><strong>${escapeHtml(req.parameter_name || "")}</strong></td>
        <td>${escapeHtml(req.value || "")}</td>
        <td><span class="tag tag-mono">${escapeHtml(normStr)}</span></td>
        <td style="font-size: 0.75rem; color: var(--text-secondary);">${escapeHtml(req.source_text || "")}</td>
      `;

      tbody.appendChild(tr);
    });
  }

  // --------------------------------------------------------------------------
  // Export JSON Contract
  // --------------------------------------------------------------------------
  exportJsonBtn.addEventListener("click", () => {
    if (!currentAnalysisData) return;
    const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentAnalysisData, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonStr);
    downloadAnchor.setAttribute("download", `maanaknetra_audit_${currentAnalysisData.tender_metadata?.analysis_id || "report"}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  });

  // --------------------------------------------------------------------------
  // UI Helpers
  // --------------------------------------------------------------------------
  function showLoading(title, subtitle) {
    loadingTitle.textContent = title;
    loadingSubtitle.textContent = subtitle;
    loadingState.classList.remove("hidden");
    analyzeBtn.disabled = true;
    demoBtn.disabled = true;
    quickDemoBtn.disabled = true;
  }

  function hideLoading() {
    loadingState.classList.add("hidden");
    analyzeBtn.disabled = !currentFile;
    demoBtn.disabled = false;
    quickDemoBtn.disabled = false;
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorAlert.classList.remove("hidden");
  }

  function hideError() {
    errorAlert.classList.add("hidden");
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
