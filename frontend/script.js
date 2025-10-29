const nodeSelect = document.getElementById("nodeSelect");
const btnVote = document.getElementById("btnVote");
const btnMine = document.getElementById("btnMine");
const btnResults = document.getElementById("btnResults");
const btnStatus = document.getElementById("btnStatus");

const voterIdInput = document.getElementById("voterId");
const candidateInput = document.getElementById("candidate");
const messageEl = document.getElementById("voteMessage");
const resultsBody = document.getElementById("resultsBody");
const statusOutput = document.getElementById("statusOutput");

const btnPrev = document.getElementById("btnPrev");
const btnNext = document.getElementById("btnNext");
const currentNodeLabel = document.getElementById("currentNodeLabel");

const nodes = [
  "http://localhost:5001",
  "http://localhost:5002",
  "http://localhost:5003",
  "http://localhost:5004",
];

let currentNodeIndex = 0;

function getBaseUrl() {
  return nodeSelect.value;
}

async function updateNodeStatus() {
  const node = nodes[currentNodeIndex];
  currentNodeLabel.textContent = `Node ${currentNodeIndex + 1} (${node})`;
  statusOutput.innerHTML = `<p>Memuat status ${node}...</p>`;

  try {
    const [statusRes, chainRes] = await Promise.all([
      fetch(`${node}/status`),
      fetch(`${node}/chain`),
    ]);
    const statusData = await statusRes.json();
    const chainData = await chainRes.json();

    statusOutput.innerHTML = `
      <div class="node-status fade-in">
        <pre>Status:\n${JSON.stringify(statusData, null, 2)}</pre>
        <pre>Chain:\n${JSON.stringify(chainData.chain, null, 2)}</pre>
      </div>
    `;
  } catch {
    statusOutput.innerHTML = `<p class="error">Tidak bisa menghubungi ${node}</p>`;
  }
}

btnPrev.addEventListener("click", () => {
  currentNodeIndex = (currentNodeIndex - 1 + nodes.length) % nodes.length;
  updateNodeStatus();
});

btnNext.addEventListener("click", () => {
  currentNodeIndex = (currentNodeIndex + 1) % nodes.length;
  updateNodeStatus();
});

btnVote.addEventListener("click", async () => {
  const BASE_URL = getBaseUrl();
  const voter_id = voterIdInput.value.trim();
  const candidate = candidateInput.value.trim();

  if (!voter_id || !candidate) {
    messageEl.textContent = "Isi ID pemilih dan nama kandidat!";
    return;
  }

  messageEl.textContent = "Mengirim vote...";
  try {
    const res = await fetch(`${BASE_URL}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voter_id, candidate }),
    });
    const data = await res.json();
    messageEl.textContent = res.ok ? ` ${data.message}` : ` ${data.message}`;
  } catch (err) {
    messageEl.textContent = "Gagal mengirim vote.";
  }
});

btnMine.addEventListener("click", async () => {
  const BASE_URL = getBaseUrl();
  btnMine.disabled = true;
  btnMine.textContent = "Menambang...";
  try {
    const res = await fetch(`${BASE_URL}/mine`);
    const data = await res.json();
    alert(data.message);
  } catch {
    alert("Gagal menambang.");
  } finally {
    btnMine.disabled = false;
    btnMine.textContent = "Tambang Manual (tanpa tunggu 3 menit)";
  }
});

btnResults.addEventListener("click", async () => {
  const BASE_URL = getBaseUrl();
  resultsBody.innerHTML = "<tr><td colspan='2'>Memuat...</td></tr>";
  try {
    const res = await fetch(`${BASE_URL}/results`);
    const data = await res.json();
    resultsBody.innerHTML = "";
    if (Object.keys(data.results).length === 0) {
      resultsBody.innerHTML = "<tr><td colspan='2'>Belum ada suara.</td></tr>";
      return;
    }
    for (const [candidate, votes] of Object.entries(data.results)) {
      resultsBody.innerHTML += `<tr><td>${candidate}</td><td>${votes}</td></tr>`;
    }
  } catch {
    resultsBody.innerHTML = "<tr><td colspan='2'>Gagal memuat hasil.</td></tr>";
  }
});

btnStatus.addEventListener("click", updateNodeStatus);
