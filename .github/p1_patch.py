# -*- coding: utf-8 -*-
s = open('index.html', encoding='utf-8').read()

def rep(old, new):
    global s
    assert s.count(old) == 1, old[:50]
    s = s.replace(old, new)

rep('<script src="https://ai-empower-hub.netlify.app/assets/bridge.js" data-app="studio" data-quiet defer></script>',
    '<script src="https://pjkuo.github.io/ai-empower/assets/bridge.js" data-app="studio" data-quiet defer></script>')
rep('href="https://ai-empower-hub.netlify.app/" target="_blank"',
    'href="https://pjkuo.github.io/" target="_blank"')
rep("const AE_HUB_URL = 'https://ai-empower-hub.netlify.app';",
    "const AE_HUB_URL = 'https://pjkuo.github.io/ai-empower';   // 2026-09-19 改指 GitHub（Netlify 僅凍結保留）")
open('index.html', 'w', encoding='utf-8').write(s)
print('OK')
