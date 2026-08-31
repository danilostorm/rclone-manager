#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-api-layout.py SOURCE_ROOT")

root = Path(sys.argv[1])
template = root / "app" / "templates" / "api_manager.html"

if not template.exists():
    print("API layout overlay: api_manager.html ausente; ignorando")
    raise SystemExit(0)

text = template.read_text(encoding="utf-8")
marker = "RM_API_LAYOUT_FIX_V1"

if marker in text:
    print("API layout overlay: já aplicado")
    raise SystemExit(0)

overlay = r'''
<!-- RM_API_LAYOUT_FIX_V1 -->
<style id="rm-api-layout-fix-v1">
  /*
   * Keep the API queue inside the card/viewport. The task table can be wider
   * than the content area because of the action buttons, so its own wrapper
   * scrolls instead of being clipped by the page/card.
   */
  main,
  .main,
  .main-content,
  .page-content,
  .content,
  .content-wrapper {
    min-width: 0 !important;
    max-width: 100% !important;
    box-sizing: border-box;
  }

  .rm-api-table-scroll {
    display: block;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow-x: auto;
    overflow-y: visible;
    box-sizing: border-box;
    -webkit-overflow-scrolling: touch;
    scrollbar-gutter: stable;
  }

  .rm-api-table-scroll > table {
    width: 100% !important;
    min-width: 1080px;
    max-width: none !important;
    table-layout: fixed;
    box-sizing: border-box;
  }

  .rm-api-table-scroll th,
  .rm-api-table-scroll td {
    min-width: 0 !important;
    box-sizing: border-box;
    overflow-wrap: anywhere;
  }

  /* Seven columns used by API / Extensão. Reserve real room for AÇÕES. */
  .rm-api-table-scroll th:nth-child(1),
  .rm-api-table-scroll td:nth-child(1) { width: 8%; }
  .rm-api-table-scroll th:nth-child(2),
  .rm-api-table-scroll td:nth-child(2) { width: 28%; }
  .rm-api-table-scroll th:nth-child(3),
  .rm-api-table-scroll td:nth-child(3) { width: 21%; }
  .rm-api-table-scroll th:nth-child(4),
  .rm-api-table-scroll td:nth-child(4) { width: 20%; }
  .rm-api-table-scroll th:nth-child(5),
  .rm-api-table-scroll td:nth-child(5) { width: 10%; }
  .rm-api-table-scroll th:nth-child(6),
  .rm-api-table-scroll td:nth-child(6) { width: 6%; }
  .rm-api-table-scroll th:nth-child(7),
  .rm-api-table-scroll td:nth-child(7) {
    width: 7%;
    min-width: 96px !important;
    white-space: normal !important;
    overflow: visible !important;
  }

  .rm-api-table-scroll td:nth-child(7) .btn,
  .rm-api-table-scroll td:nth-child(7) button,
  .rm-api-table-scroll td:nth-child(7) a {
    max-width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }

  @media (max-width: 1450px) {
    .rm-api-table-scroll > table {
      min-width: 1040px;
      font-size: 0.94em;
    }
    .rm-api-table-scroll th,
    .rm-api-table-scroll td {
      padding-left: 8px !important;
      padding-right: 8px !important;
    }
  }
</style>
<script>
(() => {
  const applyApiTableLayoutFix = () => {
    const tables = Array.from(document.querySelectorAll('table'));
    const table = tables.find((candidate) => {
      const text = (candidate.textContent || '').toUpperCase();
      return text.includes('ORIGEM / DESTINO')
        && text.includes('PROGRESSO')
        && text.includes('TRÁFEGO')
        && text.includes('AÇÕES');
    });

    if (!table || table.closest('.rm-api-table-scroll')) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'rm-api-table-scroll';
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyApiTableLayoutFix, { once: true });
  } else {
    applyApiTableLayoutFix();
  }
})();
</script>
'''

block = re.search(r"{%\s*block\s+content\s*%}", text)
if block:
    insert_at = block.end()
    text = text[:insert_at] + "\n" + overlay + text[insert_at:]
elif "</head>" in text.lower():
    pos = text.lower().find("</head>")
    text = text[:pos] + overlay + "\n" + text[pos:]
else:
    text = overlay + "\n" + text

template.write_text(text, encoding="utf-8")
print("API layout overlay OK: table responsive + actions visible")
