"""
模擬學生實際操作智慧專題創作平台（v4）全流程，並蒐集實際產出的作品檔案。
使用 Playwright（Chromium headless）；CDN 函式庫與 Pyodide 以本機 vendor 目錄替代（沙盒無法連 CDN）。
"""
import asyncio, json, os, re, sys, time, pathlib
from playwright.async_api import async_playwright

ROOT = pathlib.Path('/home/claude')
SITE = ROOT / 'AI-empower-platform'
VENDOR = ROOT / 'vendor'
OUT = ROOT / 'sim' / 'out'
SHOTS = OUT / 'screenshots'
OUT.mkdir(parents=True, exist_ok=True); SHOTS.mkdir(exist_ok=True)

CDN_MAP = {
    'https://cdn.jsdelivr.net/gh/gitbrent/pptxgenjs@3.12.0/dist/pptxgen.bundle.js': VENDOR / 'node_modules/pptxgenjs/dist/pptxgen.bundle.js',
    'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js': VENDOR / 'node_modules/xlsx/dist/xlsx.full.min.js',
    'https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js': VENDOR / 'node_modules/jszip/dist/jszip.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js': VENDOR / 'node_modules/jspdf/dist/jspdf.umd.min.js',
    'https://cdn.jsdelivr.net/npm/jspdf-autotable@3.8.2/dist/jspdf.plugin.autotable.min.js': VENDOR / 'node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.min.js',
    'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js': VENDOR / 'node_modules/html2canvas/dist/html2canvas.min.js',
    'https://cdn.jsdelivr.net/npm/docx@8.5.0/build/index.umd.min.js': VENDOR / 'node_modules/docx/build/index.umd.js',
    'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js': VENDOR / 'node_modules/mermaid/dist/mermaid.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js': VENDOR / 'node_modules/chart.js/dist/chart.umd.js',
}
PYODIDE_PREFIX = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/'
LOG = []
def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"; print(line, flush=True); LOG.append(line)

async def route_handler(route):
    url = route.request.url
    if url in CDN_MAP:
        p = CDN_MAP[url]
        await route.fulfill(path=str(p), content_type='application/javascript'); return
    if url.startswith(PYODIDE_PREFIX):
        p = VENDOR / 'pyodide' / url[len(PYODIDE_PREFIX):].split('?')[0]
        if p.exists():
            ct = 'application/javascript' if p.suffix in ('.js', '.mjs') else 'application/wasm' if p.suffix == '.wasm' else 'application/octet-stream'
            await route.fulfill(path=str(p), content_type=ct); return
        await route.fulfill(status=404, body='not found'); return
    if 'ai-empower-hub.netlify.app' in url or 'cdn.jsdelivr.net' in url or 'cdnjs.cloudflare.com' in url:
        await route.fulfill(status=404, body=''); return
    await route.continue_()

async def download(page, trigger_js, name_hint, timeout=120000):
    async with page.expect_download(timeout=timeout) as dl:
        await page.evaluate(trigger_js)
    d = await dl.value
    fn = d.suggested_filename or name_hint
    dest = OUT / fn
    await d.save_as(str(dest))
    log(f"  ⬇ 下載 {fn} ({dest.stat().st_size:,} bytes)")
    return dest

async def main():
    results = {'steps': [], 'files': [], 'console_errors': []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--autoplay-policy=no-user-gesture-required', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'])
        ctx = await browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True, locale='zh-TW')
        await ctx.route('**/*', route_handler)
        page = await ctx.new_page()
        page.on('console', lambda m: results['console_errors'].append(m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: results['console_errors'].append('PAGEERROR ' + str(e)))
        page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))

        t0 = time.time()
        # ---- 0. 學生以 Hub 連結進入（帶學號／班級）----
        await page.goto('http://127.0.0.1:8765/index.html?sid=6010&cls=MIS', wait_until='load')
        await page.wait_for_timeout(1500)
        ident = await page.evaluate("JSON.parse(localStorage.getItem('ae.identity.v1'))")
        card = await page.inner_text('#identityCard')
        log(f"0. 進入平台，身分卡：{card.strip().replace(chr(10),' / ')} ； localStorage={ident}")
        assert ident['sid'] == '6010' and ident['cls'] == 'MIS'
        results['steps'].append({'step': '身分帶入', 'ok': True, 'detail': ident})
        await page.screenshot(path=str(SHOTS / '00_entry.png'))

        # AI：無金鑰 → 自動離線引擎（同時驗證設定介面）
        await page.evaluate("openAISettings()")
        await page.select_option('#aiProvider', 'offline')
        await page.evaluate("updateAIModelHint(); saveAISettings()")
        status = await page.inner_text('#aiStatusText')
        log(f"   AI 狀態：{status}")
        await page.screenshot(path=str(SHOTS / '00b_ai_settings.png'))

        # ---- 1. 心智圖 ----
        await page.fill('#proj-title', '校園圖書館智慧借閱推薦系統')
        await page.fill('#proj-desc', '分析同學的借閱紀錄與館藏分類，推薦適合的書籍並提醒逾期，提升圖書館使用率。')
        await page.evaluate("generateMindOneClick()")
        await page.wait_for_function("document.querySelector('#branch-input').value.split('\\n').filter(Boolean).length>=3", timeout=20000)
        await page.wait_for_selector('#mindCanvasCard', state='visible', timeout=10000)
        mind = await page.evaluate("({i:$('#branch-input').value.split('\\n'),p:$('#branch-process').value.split('\\n'),o:$('#branch-output').value.split('\\n')})")
        log(f"1. 一鍵生成心智圖：INPUT {len(mind['i'])} 項 / PROCESS {len(mind['p'])} 項 / OUTPUT {len(mind['o'])} 項")
        for k, v in mind.items(): log(f"   {k}: {'、'.join(v)}")
        png_len = await page.evaluate("state.assets.mindmap.length")
        await page.screenshot(path=str(SHOTS / '01_mindmap.png'), full_page=True)
        f = await download(page, "downloadMindCanvasPng()", 'mindmap.png'); results['files'].append(str(f))
        await page.evaluate("aiReviewMind()"); await page.wait_for_timeout(300)
        review = await page.inner_text('#mindReviewBody')
        log(f"   離線審稿：{review[:80].replace(chr(10),' ')}…")
        await page.evaluate("renderMermaidMind()"); await page.wait_for_timeout(1500)
        mermaid_ok = await page.evaluate("!!document.querySelector('#mermaidMindContainer svg')")
        log(f"   Mermaid 心智圖渲染：{'OK' if mermaid_ok else '失敗'}")
        await page.evaluate("saveMindAndAdvance()")
        await page.wait_for_timeout(500)
        results['steps'].append({'step': '心智圖', 'ok': True, 'detail': mind, 'mindmapPngChars': png_len, 'mermaid': mermaid_ok})

        # ---- 2. IPO ----
        rows = await page.evaluate("state.ipo.rows.length")
        await page.evaluate("autoFillIpoNotes()")
        await page.wait_for_function("state.ipo.rows.every(r=>r.note)", timeout=10000)
        notes = await page.evaluate("state.ipo.rows.map(r=>r.stage+' | '+r.name+' | '+r.note)")
        log(f"2. IPO 表 {rows} 列，自動補充說明完成：")
        for n in notes[:4]: log(f"   {n}")
        await page.screenshot(path=str(SHOTS / '02_ipo.png'), full_page=True)
        f = await download(page, "downloadIpoXlsx()", 'ipo.xlsx'); results['files'].append(str(f))
        f = await download(page, "downloadIpoMarkdown()", 'ipo.md'); results['files'].append(str(f))
        await page.evaluate("saveIpoAndAdvance()")
        results['steps'].append({'step': 'IPO', 'ok': True, 'rows': rows, 'notes': notes})

        # ---- 3. Python 生成 + 執行 ----
        await page.select_option('#codeMode', 'template'); await page.select_option('#codeLang', 'python')
        await page.evaluate("generateCode()")
        await page.wait_for_function("state.code.full.length>500", timeout=10000)
        n_lines = await page.evaluate("state.code.full.split('\\n').length")
        log(f"3. 生成 Python 程式 {n_lines} 行")
        f = await download(page, "downloadCode()", 'code.py'); results['files'].append(str(f))
        f = await download(page, "downloadIpynb()", 'code.ipynb'); results['files'].append(str(f))
        t1 = time.time()
        await page.evaluate("runPythonInBrowser()")
        await page.wait_for_function("state.run && state.run.ts", timeout=240000)
        run = await page.evaluate("({ok:state.run.ok, err:state.run.error, charts:state.run.charts.map(c=>c.title), elapsed:state.run.elapsed, out:state.run.stdout.slice(0,1500)})")
        log(f"   瀏覽器內執行 Python：{'成功' if run['ok'] else '失敗 '+str(run['err'])}，耗時 {run['elapsed']/1000:.1f} 秒（含首次載入 Pyodide 共 {time.time()-t1:.1f} 秒），圖表 {len(run['charts'])} 張：{run['charts']}")
        for l in run['out'].split('\n')[:14]: log(f"   │ {l}")
        await page.screenshot(path=str(SHOTS / '03_python_run.png'), full_page=True)
        # 存出圖表 PNG
        n_ch = await page.evaluate("state.run.charts.length")
        for i in range(n_ch):
            b64 = await page.evaluate(f"state.run.charts[{i}].png.split(',')[1]")
            import base64; (OUT / f'chart_{i+1}.png').write_bytes(base64.b64decode(b64)); results['files'].append(str(OUT / f'chart_{i+1}.png'))
        (OUT / 'run_stdout.txt').write_text(await page.evaluate("state.run.stdout"), encoding='utf-8')
        results['steps'].append({'step': 'Python 生成與執行', 'ok': run['ok'], 'lines': n_lines, 'charts': run['charts'], 'elapsed_ms': run['elapsed']})
        assert run['ok'], run['err']
        await page.evaluate("saveCodeAndAdvance()")

        # ---- 4. PPT ----
        await page.fill('#pptAuthor', '資管系一年級 第 3 組')
        await page.evaluate("refreshOutline()")
        outline = await page.evaluate("state.ppt.outline.map(s=>s.slot+':'+s.title)")
        log(f"4. 簡報大綱 {len(outline)} 頁：{outline}")
        await page.screenshot(path=str(SHOTS / '04_ppt.png'), full_page=True)
        f = await download(page, "buildAndDownloadPPTX()", 'deck.pptx', timeout=180000); results['files'].append(str(f))
        results['steps'].append({'step': 'PPT', 'ok': True, 'slides': len(outline), 'outline': outline})

        # ---- 5. 影片 ----
        await page.evaluate("goStep(5)")
        await page.fill('#vidLen', '30'); await page.fill('#vidT1', '5'); await page.fill('#vidT2', '10'); await page.fill('#vidT3', '8')
        await page.evaluate("generateScript()")
        await page.wait_for_function("state.video.script && state.video.srt", timeout=20000)
        stages = await page.evaluate("parseScriptStages(state.video.script).map(s=>s.name+' '+s.time)")
        segs = await page.evaluate("narrationSegments().length")
        log(f"5. 影音腳本：{stages}；旁白 {segs} 句；SRT {await page.evaluate('state.video.srt.split(chr(10)).length') if False else ''}")
        await page.screenshot(path=str(SHOTS / '05_script.png'), full_page=True)
        f = await download(page, "downloadSubtitle('srt')", 'sub.srt'); results['files'].append(str(f))
        f = await download(page, "downloadScriptAll()", 'script.md'); results['files'].append(str(f))
        await page.evaluate("document.querySelector('#vidMic').checked=false; document.querySelector('#vidBgm').checked=true")
        t2 = time.time()
        await page.evaluate("makeVideo()")
        await page.wait_for_timeout(6000)
        await page.screenshot(path=str(SHOTS / '05b_video_recording.png'))
        await page.wait_for_function("state.video.made && state.video.made.ts", timeout=90000)
        made = await page.evaluate("state.video.made")
        log(f"   影片製作完成：{made['len']} 秒，{made['size']/1024:.0f} KB，{made['mime']}，實際耗時 {time.time()-t2:.1f} 秒")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(SHOTS / '05c_video_done.png'), full_page=True)
        f = await download(page, "downloadVideo()", 'video.webm'); results['files'].append(str(f))
        # 抓幾張影片畫格
        for tt, nm in [(2, 'act1'), (10, 'act2'), (19, 'act3'), (27, 'act4')]:
            await page.evaluate(f"(async()=>{{const c=$('#videoCanvas');const a=await prepareVideoAssets();drawVideoFrame(c.getContext('2d'),1280,720,{tt},buildScenes(),narrationSegments(),a);}})()")
            await page.wait_for_timeout(200)
            b64 = await page.evaluate("$('#videoCanvas').toDataURL('image/png').split(',')[1]")
            import base64; (SHOTS / f'frame_{nm}.png').write_bytes(base64.b64decode(b64))
        results['steps'].append({'step': '影片', 'ok': True, 'made': made, 'stages': stages, 'narration_lines': segs})

        # ---- 6. 打包 + 雲端紀錄 ----
        f = await download(page, "finalExport()", 'package.zip', timeout=180000); results['files'].append(str(f))
        overview = await page.inner_text('#progressOverview')
        logrec = await page.evaluate("state.log.map(l=>l.kind+':'+l.score+'/'+l.max+' sid='+l.sid)")
        log(f"6. 成果總覽：{overview.strip().replace(chr(10),' | ')}")
        log(f"   學習歷程紀錄（未連 Hub 時存本地，連上後由 bridge.js 鏡射）：{logrec}")
        await page.screenshot(path=str(SHOTS / '06_overview.png'), full_page=True)
        results['steps'].append({'step': '打包與紀錄', 'ok': True, 'log': logrec})

        # ---- 7. 重新整理後資料仍在（localStorage 持久化）----
        await page.reload(wait_until='load'); await page.wait_for_timeout(1200)
        persisted = await page.evaluate("({title:state.mind.title, completed:state.completed, hasRun:!!state.run, hasMind:!!state.assets.mindmap, step:state.step})")
        log(f"7. 重新整理後：{persisted}")
        results['steps'].append({'step': '重新整理持久化', 'ok': persisted['title'] != '' and persisted['hasRun'], 'detail': persisted})
        results['total_seconds'] = round(time.time() - t0, 1)
        await browser.close()
    results['log'] = LOG
    (OUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    log(f"完成，總耗時 {results['total_seconds']} 秒；console errors: {len(results['console_errors'])}")
    for e in results['console_errors'][:20]: print('  console:', e[:200])

if __name__ == "__main__":
    asyncio.run(main())
