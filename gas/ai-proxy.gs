/**
 * 智慧專題創作平台 — 老師代管 AI 代理（Google Apps Script）
 * -----------------------------------------------------------------
 * 目的：老師把 Gemini 金鑰放在雲端，學生只要輸入「班級碼」就能用 AI；
 *       金鑰不會出現在學生端，且每位學生每日有呼叫上限，並記錄用量。
 *
 * 部署步驟（約 5 分鐘）：
 *  1. https://script.google.com → 新增專案 → 貼上本檔案內容。
 *  2. 專案設定（齒輪）→ 指令碼屬性，新增：
 *       GEMINI_API_KEY = 你的 Gemini 金鑰（https://aistudio.google.com/app/apikey）
 *       CLASS_CODES    = MIS2026,IM2026     （多個班級碼用逗號分隔）
 *       DAILY_LIMIT    = 60                 （每位學生每日呼叫上限，選填，預設 60）
 *       MODEL          = gemini-2.5-flash   （選填）
 *  3. 部署 → 新增部署作業 → 類型「網頁應用程式」→ 執行身分「我」→ 存取權「所有人」→ 部署。
 *  4. 複製 /exec 網址，貼到 index.html 的 AI_PROXY_URL_DEFAULT（或讓學生在「設定 AI」貼上）。
 *  5. 改程式後：部署 → 管理部署作業 → 編輯 → 版本「新版本」→ 部署（網址不變）。
 *
 * 用量紀錄：第一次呼叫時會自動在雲端硬碟建立試算表「智慧專題平台 AI 用量」。
 */

var DEFAULT_MODEL = 'gemini-2.5-flash';

function doGet(e) {
  var a = (e && e.parameter && e.parameter.action) || 'ping';
  if (a === 'ping') return out_({ ok: true, service: 'ai-proxy', ts: new Date().toISOString() });
  if (a === 'usage') return out_(usageSummary_(e.parameter.code));
  return out_({ ok: false, error: 'unknown action' });
}

function doPost(e) {
  var body;
  try { body = JSON.parse(e.postData.contents || '{}'); }
  catch (err) { return out_({ ok: false, error: 'bad json' }); }
  if (body.action !== 'ai') return out_({ ok: false, error: 'unknown action' });

  var props = PropertiesService.getScriptProperties();
  var key = props.getProperty('GEMINI_API_KEY');
  if (!key) return out_({ ok: false, error: '老師尚未設定 GEMINI_API_KEY' });

  var codes = (props.getProperty('CLASS_CODES') || '').split(',').map(function (s) { return s.trim(); }).filter(String);
  var code = String(body.code || '').trim();
  if (!codes.length || codes.indexOf(code) < 0) return out_({ ok: false, error: '班級碼錯誤' });

  var sid = String(body.sid || 'anon').trim() || 'anon';
  var limit = parseInt(props.getProperty('DAILY_LIMIT') || '60', 10);
  var used = countToday_(code, sid);
  if (used >= limit) return out_({ ok: false, error: '今日 AI 使用次數已達上限（' + limit + ' 次），請明天再試或改用離線模式' });

  var model = String(body.model || props.getProperty('MODEL') || DEFAULT_MODEL).trim();
  var maxTokens = Math.min(Math.max(parseInt(body.max || 2000, 10) || 2000, 256), 8192);
  var t0 = Date.now();
  var result = callGemini_(key, model, String(body.system || ''), String(body.user || ''), maxTokens);
  log_(code, sid, String(body.cls || ''), model, result.ok, (result.text || '').length, Date.now() - t0, result.error || '');
  return out_(result);
}

function callGemini_(key, model, system, user, maxTokens) {
  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + encodeURIComponent(model) + ':generateContent?key=' + encodeURIComponent(key);
  var payload = {
    systemInstruction: { parts: [{ text: system }] },
    contents: [{ role: 'user', parts: [{ text: user }] }],
    generationConfig: { maxOutputTokens: maxTokens, temperature: 0.5 },
    safetySettings: ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']
      .map(function (c) { return { category: c, threshold: 'BLOCK_NONE' }; })
  };
  if (/(^|[^\d])2\.?5/.test(model)) payload.generationConfig.thinkingConfig = { thinkingBudget: 0 };
  try {
    var resp = UrlFetchApp.fetch(url, { method: 'post', contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true });
    var data = JSON.parse(resp.getContentText());
    if (data.error) return { ok: false, error: data.error.message || 'Gemini API 錯誤' };
    var cands = data.candidates || [];
    if (!cands.length) return { ok: false, error: 'Gemini 沒有回傳內容' + (data.promptFeedback && data.promptFeedback.blockReason ? '（' + data.promptFeedback.blockReason + '）' : '') };
    var text = (cands[0].content && cands[0].content.parts || []).map(function (p) { return p.text || ''; }).join('');
    return { ok: true, text: text, model: model };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

// ---------- 用量紀錄 ----------
function sheet_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty('LOG_SHEET_ID');
  var ss;
  if (id) { try { ss = SpreadsheetApp.openById(id); } catch (e) { ss = null; } }
  if (!ss) { ss = SpreadsheetApp.create('智慧專題平台 AI 用量'); props.setProperty('LOG_SHEET_ID', ss.getId()); }
  var sh = ss.getSheetByName('log');
  if (!sh) {
    sh = ss.insertSheet('log');
    sh.appendRow(['ts', 'date', 'code', 'sid', 'cls', 'model', 'ok', 'chars', 'ms', 'error']);
    sh.getRange('D:D').setNumberFormat('@');
  }
  return sh;
}
function today_() { return Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyy-MM-dd'); }
function log_(code, sid, cls, model, ok, chars, ms, error) {
  try { sheet_().appendRow([new Date(), today_(), code, sid, cls, model, ok ? 1 : 0, chars, ms, error]); } catch (e) {}
}
function countToday_(code, sid) {
  try {
    var sh = sheet_(); var last = sh.getLastRow(); if (last < 2) return 0;
    var rows = sh.getRange(Math.max(2, last - 2000), 1, Math.min(2000, last - 1), 4).getValues();
    var d = today_(), n = 0;
    for (var i = 0; i < rows.length; i++) if (rows[i][1] === d && rows[i][2] === code && String(rows[i][3]) === sid) n++;
    return n;
  } catch (e) { return 0; }
}
function usageSummary_(code) {
  var sh = sheet_(); var last = sh.getLastRow(); if (last < 2) return { ok: true, today: 0, total: 0 };
  var rows = sh.getRange(2, 1, last - 1, 8).getValues(); var d = today_();
  var today = 0, total = 0, bySid = {};
  rows.forEach(function (r) { if (code && r[2] !== code) return; total++; if (r[1] === d) { today++; bySid[r[3]] = (bySid[r[3]] || 0) + 1; } });
  return { ok: true, today: today, total: total, bySidToday: bySid };
}

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
