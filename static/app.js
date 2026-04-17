const generateForm = document.getElementById("generate-form");
const uploadForm = document.getElementById("upload-form");
const yamlFileInput = document.getElementById("yaml-file");
const resultSection = document.getElementById("result");
const linksContainer = document.getElementById("links");
const stashPreview = document.getElementById("stash-preview");
const loonPreview = document.getElementById("loon-preview");
const recordsList = document.getElementById("records-list");
const recordsEmpty = document.getElementById("records-empty");
const refreshRecordsButton = document.getElementById("refresh-records");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    window.alert("链接已复制");
  } catch (error) {
    window.prompt("复制失败，请手动复制下面的链接", text);
  }
}

function recordCard(item) {
  const typeLabel = item.source_type === "upload" ? "上传转换" : "节点生成";
  return `
    <article class="record-card">
      <div class="record-top">
        <div>
          <h3>${escapeHtml(item.name)}</h3>
          <p class="record-meta">${typeLabel} · ${item.nodes_count} 个节点 · ${escapeHtml(formatTime(item.created_at))}</p>
        </div>
        <span class="record-token">${escapeHtml(item.token)}</span>
      </div>
      <div class="record-links">
        <a href="${item.files.stash_url}" target="_blank" rel="noreferrer">Stash 配置链接</a>
        <a href="${item.files.loon_url}" target="_blank" rel="noreferrer">Loon 配置链接</a>
      </div>
      <div class="record-actions">
        <a class="action-button" href="${item.files.stash_url}" download>下载 Stash</a>
        <a class="action-button" href="${item.files.loon_url}" download>下载 Loon</a>
        <button type="button" class="action-button ghost-button" data-copy="${item.files.stash_url}">复制 Stash 链接</button>
        <button type="button" class="action-button ghost-button" data-copy="${item.files.loon_url}">复制 Loon 链接</button>
        <a class="action-button accent-button" href="${item.files.stash_import_url}">导入 Stash</a>
        <a class="action-button accent-button" href="${item.files.loon_import_url}">导入 Loon</a>
        <a class="action-button" href="${item.files.loon_universal_url}" target="_blank" rel="noreferrer">Loon 通用唤起</a>
      </div>
    </article>
  `;
}

function bindRecordActions() {
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", () => copyText(button.dataset.copy));
  });
}

async function loadRecords() {
  if (!recordsList || !recordsEmpty) {
    return;
  }
  const response = await fetch("/api/records");
  const data = await response.json();
  const items = data.items || [];
  recordsEmpty.style.display = items.length ? "none" : "block";
  recordsList.innerHTML = items.map(recordCard).join("");
  bindRecordActions();
}

function renderResult(data) {
  if (!resultSection || !linksContainer || !stashPreview || !loonPreview) {
    return;
  }
  resultSection.classList.remove("hidden");
  linksContainer.innerHTML = "";

  const linkEntries = [
    ["Stash 配置链接", data.files.stash_url],
    ["Loon 配置链接", data.files.loon_url],
    ["Stash 导入", data.files.stash_import_url],
    ["Loon 导入", data.files.loon_import_url],
    ["Loon 通用跳转", data.files.loon_universal_url],
  ];

  linkEntries.forEach(([label, href]) => {
    const row = document.createElement("div");
    row.innerHTML = `<strong>${label}</strong><br /><a href="${href}" target="_blank" rel="noreferrer">${href}</a>`;
    linksContainer.appendChild(row);
  });

  stashPreview.textContent = data.stash_preview;
  loonPreview.textContent = data.loon_preview;
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  loadRecords().catch((error) => console.error(error));
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

if (generateForm) {
  generateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(generateForm);
    const payload = {
      profile_name: formData.get("profile_name"),
      node_text: formData.get("node_text"),
    };

    try {
      const data = await postJson("/api/generate", payload);
      renderResult(data);
    } catch (error) {
      window.alert(error.message);
    }
  });
}

if (uploadForm) {
  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = yamlFileInput.files[0];
    if (!file) {
      window.alert("请先选择 YAML 文件");
      return;
    }

    try {
      const content = await file.text();
      const data = await postJson("/api/convert-upload", {
        filename: file.name,
        content,
      });
      renderResult(data);
    } catch (error) {
      window.alert(error.message);
    }
  });
}

if (refreshRecordsButton) {
  refreshRecordsButton.addEventListener("click", () => {
    loadRecords().catch((error) => window.alert(error.message));
  });
}

if (recordsEmpty) {
  loadRecords().catch((error) => {
    console.error(error);
    recordsEmpty.textContent = "配置列表加载失败，请稍后刷新重试。";
  });
}
