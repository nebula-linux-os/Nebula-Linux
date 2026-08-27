const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Tab switching
$$('.tabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    $$('.tabs button').forEach(b => b.classList.remove('active'));
    $$('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`#tab-${btn.dataset.tab}`).classList.add('active');
    if (btn.dataset.tab === 'memory') loadMemory();
    if (btn.dataset.tab === 'history') loadHistory();
    if (btn.dataset.tab === 'models') loadModels();
  });
});

// Load model list into selector
async function loadModelOptions() {
  try {
    const res = await fetch('/api/models');
    const models = await res.json();
    const select = $('#model-select');
    for (const m of models) {
      if (!m.installed) continue;
      const opt = document.createElement('option');
      opt.value = m.model;
      opt.textContent = `${m.model} (${m.speed})`;
      select.appendChild(opt);
    }
  } catch (e) { console.error(e); }
}

// Chat
let currentTaskId = null;
const messagesEl = $('#messages');

function addMsg(role, text = '') {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;
  const roleLabel = document.createElement('div');
  roleLabel.className = 'msg-role';
  roleLabel.textContent = role;
  const body = document.createElement('div');
  body.className = 'msg-body';
  body.textContent = text;
  wrap.appendChild(roleLabel);
  wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  scrollToBottom();
  return body;
}

function addRouterTag(model, category) {
  const tag = document.createElement('div');
  tag.className = 'router-tag';
  tag.textContent = `router → ${category} · ${model}`;
  messagesEl.appendChild(tag);
  scrollToBottom();
}

function addDoneTag(outcome, steps, duration) {
  const tag = document.createElement('div');
  tag.className = 'done-tag';
  tag.textContent = `done · ${outcome} · ${steps} steps · ${duration}s`;
  messagesEl.appendChild(tag);
  scrollToBottom();
}

function addToolBlock(step, name, args) {
  const block = document.createElement('div');
  block.className = 'tool-block pending';
  block.innerHTML = `
    <div class="tool-header">
      <span class="step">[step ${step}]</span>
      <span class="name">${name}</span>
    </div>
    <div class="tool-args">${escapeJson(args)}</div>
  `;
  messagesEl.appendChild(block);
  scrollToBottom();
  return block;
}

function addToolResult(block, name, result) {
  const isErr = result && result.error;
  block.classList.remove('pending');
  block.classList.add(isErr ? 'err' : 'ok');
  const resDiv = document.createElement('div');
  resDiv.className = 'tool-result';
  resDiv.textContent = JSON.stringify(result, null, 2);
  block.appendChild(resDiv);
  scrollToBottom();
}

function addConfirmBox(block, name, args) {
  const box = document.createElement('div');
  box.className = 'confirm-box';
  box.innerHTML = `
    <span class="text">Allow <b>${name}</b>?</span>
    <button class="deny">Deny</button>
    <button class="allow">Allow</button>
  `;
  block.appendChild(box);
  return new Promise(resolve => {
    box.querySelector('.allow').addEventListener('click', () => { box.remove(); resolve(true); });
    box.querySelector('.deny').addEventListener('click', () => { box.remove(); resolve(false); });
  });
}

function escapeJson(obj) {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
}

function scrollToBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }

async function sendApproval(taskId, allowed) {
  await fetch(`/api/approve/${taskId}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({allowed}),
  });
}

$('#composer').addEventListener('submit', async (e) => {
  e.preventDefault();
  const task = $('#input').value.trim();
  if (!task) return;
  $('#input').value = '';
  $('#send').disabled = true;

  // Cancel any lingering TTS from the previous turn
  if (typeof stopSpeaking === 'function') stopSpeaking();

  addMsg('user', task);
  let assistantBody = null;
  const toolBlocks = {};

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        task,
        model: $('#model-select').value || null,
        auto_approve: $('#auto-approve').checked,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let currentBlock = null;

    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buf += decoder.decode(value, {stream: true});
      const parts = buf.split('\n\n');
      buf = parts.pop();
      for (const part of parts) {
        const dataLine = part.split('\n').find(l => l.startsWith('data: '));
        if (!dataLine) continue;
        const evt = JSON.parse(dataLine.slice(6));
        await handleEvent(evt);
      }
    }
  } catch (err) {
    addMsg('error', String(err));
  } finally {
    $('#send').disabled = false;
    $('#input').focus();
  }

  async function handleEvent(evt) {
    switch (evt.type) {
      case 'task_id':
        currentTaskId = evt.task_id;
        break;
      case 'router':
        addRouterTag(evt.model, evt.category);
        break;
      case 'token':
        if (!assistantBody) assistantBody = addMsg('assistant', '');
        assistantBody.textContent += evt.text;
        window.dispatchEvent(new CustomEvent('nova:assistant_token', {detail: {text: evt.text}}));
        scrollToBottom();
        break;
      case 'assistant_done':
        assistantBody = null;
        window.dispatchEvent(new CustomEvent('nova:assistant_done'));
        break;
      case 'tool_call':
        currentBlock = addToolBlock(evt.step, evt.name, evt.args);
        toolBlocks[`${evt.step}-${evt.name}`] = currentBlock;
        break;
      case 'tool_awaiting_confirm': {
        const allowed = await addConfirmBox(currentBlock, evt.name, evt.args);
        await sendApproval(currentTaskId, allowed);
        break;
      }
      case 'tool_result':
        if (currentBlock) addToolResult(currentBlock, evt.name, evt.result);
        break;
      case 'error':
        addMsg('error', evt.message);
        break;
      case 'done':
        addDoneTag(evt.outcome, evt.steps, evt.duration_s);
        break;
    }
  }
});

$('#input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('#composer').requestSubmit();
  }
});

// Memory tab
async function loadMemory() {
  const list = $('#memory-list');
  list.innerHTML = '<div class="empty">Loading…</div>';
  const res = await fetch('/api/memory');
  const memories = await res.json();
  if (!memories.length) {
    list.innerHTML = '<div class="empty">No memories saved yet.</div>';
    return;
  }
  list.innerHTML = '';
  for (const m of memories) {
    const row = document.createElement('div');
    row.className = 'list-row';
    row.innerHTML = `
      <div>
        <span class="tag">${m.category}</span>
        <span>${m.content}</span>
        <div class="meta">#${m.id} · used ${m.use_count}×</div>
      </div>
      <button data-id="${m.id}">Forget</button>
    `;
    row.querySelector('button').addEventListener('click', async () => {
      await fetch(`/api/memory/${m.id}`, {method: 'DELETE'});
      loadMemory();
    });
    list.appendChild(row);
  }
}

// History tab
async function loadHistory() {
  const list = $('#history-list');
  list.innerHTML = '<div class="empty">Loading…</div>';
  const res = await fetch('/api/history');
  const tasks = await res.json();
  if (!tasks.length) {
    list.innerHTML = '<div class="empty">No task history yet.</div>';
    return;
  }
  list.innerHTML = '';
  for (const t of tasks) {
    const row = document.createElement('div');
    row.className = 'list-row';
    const status = t.outcome === 'completed' ? 'ok' : 'err';
    const when = new Date(t.created_at * 1000).toLocaleString();
    row.innerHTML = `
      <div>
        <span class="tag ${status}">${t.outcome}</span>
        <span>${t.task}</span>
        <div class="meta">${when} · ${t.model} · ${t.steps} steps · ${t.duration_s}s</div>
      </div>
    `;
    list.appendChild(row);
  }
}

// Models tab
async function loadModels() {
  const list = $('#models-list');
  list.innerHTML = '<div class="empty">Loading…</div>';
  const res = await fetch('/api/models');
  const models = await res.json();
  list.innerHTML = '';
  for (const m of models) {
    const row = document.createElement('div');
    row.className = 'list-row';
    const status = m.installed && m.fits_ram ? 'ok' : 'err';
    const statusLabel = !m.installed ? 'not installed' : !m.fits_ram ? 'too large for RAM' : 'ready';
    row.innerHTML = `
      <div>
        <span class="tag ${status}">${statusLabel}</span>
        <span>${m.model}</span>
        <div class="meta">${m.speed} · ${m.ram_gb} GB · ${m.strengths.join(', ')}</div>
      </div>
    `;
    list.appendChild(row);
  }
}

$('#reload-memory')?.addEventListener('click', loadMemory);
$('#reload-history')?.addEventListener('click', loadHistory);
$('#reload-models')?.addEventListener('click', loadModels);

loadModelOptions();
loadStatus();

async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const s = await res.json();
    $('#version').textContent = `v${s.version}`;
    $('#autostart-toggle').checked = !!s.autostart;
  } catch (e) { console.warn('status load failed', e); }
  checkForUpdate();
}

async function checkForUpdate() {
  try {
    const res = await fetch('/api/update-check');
    const info = await res.json();
    if (info.update_available) {
      const b = $('#update-banner');
      b.hidden = false;
      b.textContent = `Update: v${info.latest}`;
      b.onclick = () => window.open(info.url, '_blank');
    }
  } catch (e) { /* silent */ }
}

$('#autostart-toggle').addEventListener('change', async (e) => {
  const enabled = e.target.checked;
  const res = await fetch('/api/autostart', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled}),
  });
  const r = await res.json();
  if (!r.ok) {
    addMsg('error', `Autostart failed: ${r.error || 'unknown'}`);
    e.target.checked = !enabled;
  }
});

// ────────── Voice (Web Speech API + SpeechSynthesis) ──────────

const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;
let ttsQueue = [];
let ttsSpeaking = false;

function voiceEnabled() { return $('#voice-mode').checked; }
function ttsAvailable() { return 'speechSynthesis' in window; }
function sttAvailable() { return !!SpeechRecognitionClass; }

function setupVoiceUI() {
  const supported = sttAvailable();
  const micBtn = $('#mic');
  if (voiceEnabled() && supported) {
    micBtn.hidden = false;
  } else {
    micBtn.hidden = true;
  }
  if (voiceEnabled() && !supported) {
    addMsg('system', 'Voice input not supported in this browser. Chrome or Edge works best.');
    $('#voice-mode').checked = false;
  }
}

$('#voice-mode').addEventListener('change', setupVoiceUI);

$('#mic').addEventListener('click', () => {
  if (recognizer) {
    recognizer.stop();
    return;
  }
  startListening();
});

function startListening() {
  recognizer = new SpeechRecognitionClass();
  recognizer.continuous = false;
  recognizer.interimResults = true;
  recognizer.lang = 'en-US';

  const micBtn = $('#mic');
  micBtn.classList.add('listening');
  micBtn.textContent = '⏹';

  let finalText = '';
  recognizer.onresult = (e) => {
    let interim = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += t;
      else interim += t;
    }
    $('#input').value = (finalText + interim).trim();
  };
  recognizer.onerror = (e) => {
    console.warn('speech recog error', e.error);
  };
  recognizer.onend = () => {
    micBtn.classList.remove('listening');
    micBtn.textContent = '🎤';
    recognizer = null;
    if (finalText.trim()) {
      $('#composer').requestSubmit();
    }
  };
  recognizer.start();
}

function speak(text) {
  if (!voiceEnabled() || !ttsAvailable()) return;
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return;
  ttsQueue.push(clean);
  drainTTS();
}

function drainTTS() {
  if (ttsSpeaking || !ttsQueue.length) return;
  ttsSpeaking = true;
  const text = ttsQueue.shift();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.05;
  utter.pitch = 1.0;
  utter.volume = 1.0;
  utter.onend = () => { ttsSpeaking = false; drainTTS(); };
  utter.onerror = () => { ttsSpeaking = false; drainTTS(); };
  window.speechSynthesis.speak(utter);
}

function stopSpeaking() {
  ttsQueue = [];
  if (ttsAvailable()) window.speechSynthesis.cancel();
  ttsSpeaking = false;
}

// Hook TTS into the message flow — speak completed assistant turns.
// Buffer tokens, then speak the accumulated text once the turn ends.
let pendingSpeech = '';
const originalHandleEvent = null; // placeholder, real hook is inline below

// Patch: intercept assistant tokens to accumulate, then speak on assistant_done.
// We do this by wrapping addMsg's assistant body element.
const _origAddMsg = addMsg;
window.addEventListener('nova:assistant_done', () => {
  if (pendingSpeech.trim()) speak(pendingSpeech);
  pendingSpeech = '';
});
window.addEventListener('nova:assistant_token', (e) => {
  pendingSpeech += e.detail.text;
});

