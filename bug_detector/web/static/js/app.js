// AI-Powered Bug Detection System Frontend Client

const DEMO_SNIPPETS = {
  security: `# Security Vulnerabilities Demo
import os
import subprocess

def execute_user_task(command_str: str, payload: str):
    # SEC001: eval/exec dynamic code execution
    result = eval(payload)
    
    # SEC002: command injection vulnerabilities
    os.system("echo " + command_str)
    subprocess.run("cat " + command_str, shell=True)
    return result
`,

  correctness: `# Correctness Bugs Demo
def process_data(items=[], config={"debug": True}):
    # COR001: mutable default arguments (shared state across calls)
    items.append(1)

    # COR002: comparison with None using equality operator
    if items == None:
        pass

    # COR003: division by literal zero
    factor = 100 / 0

    # COR004: duplicate dictionary keys
    metadata = {"env": "prod", "env": "dev"}

    # COR005: unreachable statement
    return factor
    print("This line is never executed")
`,

  style: `# Style & Quality Issues Demo
# STY002: Variable shadowing built-in 'list'
list = [10, 20, 30]

def fetch_data(id, type):
    try:
        val = list[id]
        # STY003: assert tuple (always evaluates to True!)
        assert (val > 0, "Must be positive")
        return val
    except:
        # STY001: bare except catches KeyboardInterrupt/SystemExit
        return None
`,

  syntax: `# Syntax Error Demo
def calculate_metrics(values, factor
    total = sum(values) * factor
    return total
`,

  clean: `# Clean, Idiomatic Python
from typing import List, Dict

def compute_statistics(numbers: List[float]) -> Dict[str, float]:
    """Calculate basic metrics safely without mutable state or dangerous calls."""
    if not numbers:
        return {"count": 0.0, "mean": 0.0, "max": 0.0}

    count = float(len(numbers))
    mean_val = sum(numbers) / count
    max_val = max(numbers)

    return {
        "count": count,
        "mean": mean_val,
        "max": max_val,
    }
`
};

let currentFindings = [];
let currentFilter = "ALL";

document.addEventListener("DOMContentLoaded", () => {
  initHealthCheck();
  initEditor();
  initAnalyzeAction();
  initHistoryModal();
});

// 1. Health check & capabilities
async function initHealthCheck() {
  const pill = document.getElementById("ai-status-pill");
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();
    if (data.ai_configured) {
      pill.textContent = `AI: Ready (${data.model})`;
      pill.className = "badge-pill pill-green";
    } else {
      pill.textContent = "AI: Skipped (No Key)";
      pill.className = "badge-pill pill-gray";
    }
  } catch (err) {
    pill.textContent = "Status: Offline";
    pill.className = "badge-pill pill-gray";
  }
}

// 2. Editor setup & Tab handling
function initEditor() {
  const editor = document.getElementById("code-input");
  const demoSelector = document.getElementById("demo-selector");
  const btnClear = document.getElementById("btn-clear-code");

  // Tab indentation support
  editor.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      editor.value = editor.value.substring(0, start) + "    " + editor.value.substring(end);
      editor.selectionStart = editor.selectionEnd = start + 4;
    }
  });

  // Demo selector
  demoSelector.addEventListener("change", () => {
    const val = demoSelector.value;
    if (val && DEMO_SNIPPETS[val]) {
      editor.value = DEMO_SNIPPETS[val];
    }
  });

  // Clear button
  btnClear.addEventListener("click", () => {
    editor.value = "";
    demoSelector.value = "";
  });
}

// 3. Analyze Code Action
function initAnalyzeAction() {
  const btnAnalyze = document.getElementById("btn-analyze");
  const editor = document.getElementById("code-input");
  const aiToggle = document.getElementById("ai-toggle-checkbox");

  btnAnalyze.addEventListener("click", async () => {
    const code = editor.value;
    if (!code.trim()) {
      alert("Please provide Python code before analyzing.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_code: code,
          request_ai: aiToggle.checked,
          filename: "<web-input>",
          save: true,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      const report = await response.json();
      renderResults(report);

    } catch (err) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  });

  // Filter tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      applyFilter();
    });
  });
}

function setLoading(isLoading) {
  const emptyState = document.getElementById("empty-state");
  const loadingState = document.getElementById("loading-state");
  const contentState = document.getElementById("content-state");
  const btn = document.getElementById("btn-analyze");

  if (isLoading) {
    emptyState.style.display = "none";
    contentState.style.display = "none";
    loadingState.style.display = "flex";
    btn.disabled = true;
  } else {
    loadingState.style.display = "none";
    btn.disabled = false;
  }
}

// 4. Render Results
function renderResults(report) {
  const emptyState = document.getElementById("empty-state");
  const contentState = document.getElementById("content-state");
  const timingBadge = document.getElementById("timing-badge");
  const syntaxBox = document.getElementById("syntax-error-box");

  emptyState.style.display = "none";
  contentState.style.display = "flex";

  // Timing
  timingBadge.style.display = "inline-flex";
  timingBadge.textContent = `${report.duration_ms.toFixed(1)} ms`;

  // Syntax error handling
  if (!report.is_syntax_valid && report.syntax_error) {
    const err = report.syntax_error;
    syntaxBox.style.display = "block";
    document.getElementById("syntax-err-loc").textContent = `(Line ${err.line_number}:${err.column_offset})`;
    document.getElementById("syntax-err-msg").textContent = err.message;
    document.getElementById("syntax-err-diagram").textContent = err.pointer_diagram || err.line_text || "";
  } else {
    syntaxBox.style.display = "none";
  }

  // Summary Metrics
  const summary = report.summary || {};
  document.getElementById("metric-total").textContent = summary.total_findings || 0;
  document.getElementById("metric-errors").textContent = summary.errors || 0;
  document.getElementById("metric-warnings").textContent = summary.warnings || 0;
  document.getElementById("metric-info").textContent = summary.info || 0;

  // Filter tab counts
  document.getElementById("count-all").textContent = summary.total_findings || 0;
  document.getElementById("count-err").textContent = summary.errors || 0;
  document.getElementById("count-warn").textContent = summary.warnings || 0;
  document.getElementById("count-info").textContent = summary.info || 0;

  // AI Quality Score
  const aiBox = document.getElementById("metric-ai-box");
  const aiScore = document.getElementById("metric-ai-score");
  if (report.ai_review && report.ai_review.code_quality_score !== null && report.ai_review.code_quality_score !== undefined) {
    aiBox.style.display = "block";
    aiScore.textContent = `${report.ai_review.code_quality_score}/100`;
  } else {
    aiBox.style.display = "none";
  }

  // Findings list
  currentFindings = report.findings || [];
  applyFilter();

  // AI Review Details
  const aiSection = document.getElementById("ai-review-section");
  if (report.ai_review && report.ai_review.status === "success") {
    aiSection.style.display = "flex";
    document.getElementById("ai-model-tag").textContent = report.ai_review.model_used || "OpenAI";
    document.getElementById("ai-summary-text").textContent = report.ai_review.overall_summary || "";

    const aiFindingsBox = document.getElementById("ai-findings-container");
    aiFindingsBox.innerHTML = "";
    (report.ai_review.findings || []).forEach((item) => {
      const card = document.createElement("div");
      card.className = "finding-card";
      card.style.borderLeftColor = "#8b5cf6";
      card.innerHTML = `
        <div class="finding-header">
          <span class="finding-title">${escapeHtml(item.issue)}</span>
          <span class="finding-badge badge-INFO">${escapeHtml(item.severity)}</span>
        </div>
        <div class="finding-desc">${escapeHtml(item.explanation)}</div>
        ${item.suggested_fix ? `<div class="finding-fix">Fix: ${escapeHtml(item.suggested_fix)}</div>` : ""}
      `;
      aiFindingsBox.appendChild(card);
    });

    const refactorBox = document.getElementById("ai-refactor-box");
    if (report.ai_review.refactored_code) {
      refactorBox.style.display = "block";
      document.getElementById("ai-refactor-code").textContent = report.ai_review.refactored_code;
    } else {
      refactorBox.style.display = "none";
    }
  } else if (report.ai_review && report.ai_review.status === "error") {
    aiSection.style.display = "flex";
    document.getElementById("ai-model-tag").textContent = "Error";
    document.getElementById("ai-summary-text").textContent = `AI Review Error: ${report.ai_review.error_message}`;
    document.getElementById("ai-findings-container").innerHTML = "";
    document.getElementById("ai-refactor-box").style.display = "none";
  } else {
    aiSection.style.display = "none";
  }
}

// 5. Filter Findings
function applyFilter() {
  const container = document.getElementById("findings-container");
  container.innerHTML = "";

  const filtered = currentFindings.filter((f) => {
    if (currentFilter === "ALL") return true;
    return f.severity === currentFilter;
  });

  if (filtered.length === 0) {
    const emptyMsg = document.createElement("div");
    emptyMsg.style.color = "var(--text-muted)";
    emptyMsg.style.fontSize = "0.85rem";
    emptyMsg.style.padding = "1rem";
    emptyMsg.style.textAlign = "center";
    emptyMsg.textContent = currentFindings.length === 0 ? "✓ No issues detected." : "No findings match this filter.";
    container.appendChild(emptyMsg);
    return;
  }

  filtered.forEach((f) => {
    const card = document.createElement("div");
    card.className = `finding-card severity-${f.severity}`;
    card.innerHTML = `
      <div class="finding-header">
        <span class="finding-title">[${escapeHtml(f.rule_id)}] ${escapeHtml(f.rule_name)}</span>
        <span class="finding-badge badge-${f.severity}">${f.severity}</span>
      </div>
      <div class="finding-loc">Line ${f.line_number}:${f.column_offset}</div>
      ${f.code_snippet ? `<div style="font-family: var(--font-mono); font-size: 0.8rem; color: #94a3b8; background: rgba(0,0,0,0.25); padding: 0.25rem 0.5rem; border-radius: 4px;">${escapeHtml(f.code_snippet)}</div>` : ""}
      <div class="finding-desc">${escapeHtml(f.message)}</div>
      ${f.suggestion ? `<div class="finding-fix">Suggestion: ${escapeHtml(f.suggestion)}</div>` : ""}
    `;
    container.appendChild(card);
  });
}

// 6. History Modal & Drawer
function initHistoryModal() {
  const modal = document.getElementById("history-modal");
  const btnOpen = document.getElementById("btn-open-history");
  const btnClose = document.getElementById("btn-close-history");
  const btnRefresh = document.getElementById("btn-refresh-history");
  const btnClear = document.getElementById("btn-clear-history");

  btnOpen.addEventListener("click", () => {
    modal.classList.add("open");
    loadHistoryList();
  });

  btnClose.addEventListener("click", () => {
    modal.classList.remove("open");
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("open");
  });

  btnRefresh.addEventListener("click", loadHistoryList);

  btnClear.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear all review history?")) return;
    try {
      const res = await fetch("/api/history/clear", { method: "POST" });
      if (res.ok) {
        loadHistoryList();
      }
    } catch (err) {
      alert("Failed to clear history");
    }
  });
}

async function loadHistoryList() {
  const listContainer = document.getElementById("history-list");
  listContainer.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Loading reviews...</div>';

  try {
    const res = await fetch("/api/history?limit=30");
    if (!res.ok) throw new Error("Failed to load history");
    const reviews = await res.json();

    if (!reviews || reviews.length === 0) {
      listContainer.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No past reviews recorded yet.</div>';
      return;
    }

    listContainer.innerHTML = "";
    reviews.forEach((r) => {
      const item = document.createElement("div");
      item.className = "history-item";

      const validBadge = r.is_syntax_valid 
        ? '<span style="color: #10b981; font-size: 0.75rem;">✓ Valid</span>' 
        : '<span style="color: #ef4444; font-size: 0.75rem;">✗ Syntax Error</span>';

      const snippet = (r.source_code || "").trim().split("\n")[0] || "(empty)";

      item.innerHTML = `
        <div class="history-info">
          <div class="history-title">
            <span>Review ${r.id.substring(0, 8)}</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">${r.timestamp.substring(0, 19).replace("T", " ")}</span>
          </div>
          <div class="history-snippet">${escapeHtml(snippet)}</div>
          <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.2rem;">
            ${validBadge} • ${r.summary ? r.summary.total_findings : 0} findings • ${r.duration_ms.toFixed(1)}ms
          </div>
        </div>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <button class="btn-secondary btn-load" style="font-size: 0.75rem;">Load</button>
          <button class="btn-danger btn-del" style="font-size: 0.75rem;">Delete</button>
        </div>
      `;

      item.querySelector(".btn-load").addEventListener("click", () => {
        document.getElementById("code-input").value = r.source_code;
        renderResults(r);
        document.getElementById("history-modal").classList.remove("open");
      });

      item.querySelector(".btn-del").addEventListener("click", async (e) => {
        e.stopPropagation();
        if (confirm("Delete this review record?")) {
          await fetch(`/api/history/${r.id}`, { method: "DELETE" });
          loadHistoryList();
        }
      });

      listContainer.appendChild(item);
    });

  } catch (err) {
    listContainer.innerHTML = `<div style="text-align: center; color: var(--color-error); padding: 1.5rem;">Error loading history: ${err.message}</div>`;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
