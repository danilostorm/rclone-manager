#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("uso: patch-responsive-layout.py SOURCE_ROOT")

root = Path(sys.argv[1])
templates = root / "app" / "templates"

if not templates.exists():
    print("Responsive layout overlay: templates ausentes; ignorando")
    raise SystemExit(0)

marker = "RM_GLOBAL_RESPONSIVE_V1"

overlay = r'''
<!-- RM_GLOBAL_RESPONSIVE_V1 -->
<style id="rm-global-responsive-v1">
  html,
  body {
    max-width: 100%;
  }

  body {
    overflow-x: hidden;
  }

  main,
  .main,
  .main-content,
  .page-content,
  .content,
  .content-wrapper {
    min-width: 0 !important;
    max-width: none !important;
    box-sizing: border-box;
  }

  .rm-shell-main {
    min-width: 0 !important;
    max-width: none !important;
    box-sizing: border-box !important;
  }

  .rm-fluid-page {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    box-sizing: border-box !important;
  }

  .rm-shell-main .container.rm-fluid-page,
  .rm-shell-main .container-fluid,
  .rm-shell-main > .container {
    max-width: none !important;
    width: 100% !important;
  }

  .rm-global-table-scroll {
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

  .rm-global-table-scroll > table {
    max-width: none !important;
  }

  .rm-shell-main img,
  .rm-shell-main video,
  .rm-shell-main canvas,
  .rm-shell-main svg {
    max-width: 100%;
  }

  .rm-shell-main input,
  .rm-shell-main select,
  .rm-shell-main textarea {
    max-width: 100%;
    box-sizing: border-box;
  }

  .rm-shell-main pre,
  .rm-shell-main code {
    max-width: 100%;
    overflow-wrap: anywhere;
  }

  .rm-responsive-grid {
    min-width: 0;
  }

  .rm-page-header {
    min-width: 0;
  }

  .rm-mobile-menu-button,
  .rm-mobile-menu-backdrop {
    display: none;
  }

  @media (max-width: 1180px) {
    .rm-shell-main {
      padding-left: 18px !important;
      padding-right: 18px !important;
    }

    .rm-global-table-scroll > table {
      min-width: 820px;
    }
  }

  @media (max-width: 900px) {
    body.rm-mobile-nav-open {
      overflow: hidden !important;
    }

    .rm-shell-sidebar {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      bottom: 0 !important;
      width: min(86vw, 320px) !important;
      max-width: 320px !important;
      height: 100dvh !important;
      z-index: 10001 !important;
      overflow-y: auto !important;
      overflow-x: hidden !important;
      transform: translateX(-105%) !important;
      transition: transform .22s ease !important;
      box-shadow: 12px 0 30px rgba(0, 0, 0, .35) !important;
    }

    body.rm-mobile-nav-open .rm-shell-sidebar {
      transform: translateX(0) !important;
    }

    .rm-shell-main {
      width: 100% !important;
      max-width: 100% !important;
      min-width: 0 !important;
      margin-left: 0 !important;
      margin-right: 0 !important;
      padding: 68px 12px 22px !important;
      box-sizing: border-box !important;
    }

    .rm-fluid-page {
      width: 100% !important;
      max-width: 100% !important;
    }

    .rm-mobile-menu-button {
      position: fixed;
      top: 12px;
      left: 12px;
      z-index: 10003;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border: 1px solid rgba(148, 163, 184, .24);
      border-radius: 10px;
      background: #171d27;
      color: #f8fafc;
      font: inherit;
      font-size: 22px;
      line-height: 1;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(0, 0, 0, .28);
    }

    .rm-mobile-menu-backdrop {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: block;
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      background: rgba(2, 6, 12, .62);
      transition: opacity .22s ease, visibility .22s ease;
    }

    body.rm-mobile-nav-open .rm-mobile-menu-backdrop {
      opacity: 1;
      visibility: visible;
      pointer-events: auto;
    }

    .rm-page-header {
      display: flex !important;
      flex-wrap: wrap !important;
      align-items: flex-start !important;
      gap: 10px !important;
    }

    .rm-responsive-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    }

    .rm-global-table-scroll {
      margin-left: 0;
      margin-right: 0;
      border-radius: inherit;
    }

    .rm-global-table-scroll > table {
      min-width: 760px;
    }

    .rm-shell-main .btn,
    .rm-shell-main button,
    .rm-shell-main a[role="button"] {
      max-width: 100%;
      box-sizing: border-box;
    }
  }

  @media (max-width: 640px) {
    .rm-shell-main {
      padding-left: 10px !important;
      padding-right: 10px !important;
    }

    .rm-responsive-grid {
      grid-template-columns: minmax(0, 1fr) !important;
    }

    .rm-page-header {
      flex-direction: column !important;
      align-items: stretch !important;
    }

    .rm-page-header > * {
      max-width: 100% !important;
    }

    .rm-shell-main h1 {
      font-size: clamp(1.45rem, 7vw, 2rem);
      line-height: 1.12;
    }

    .rm-shell-main h2 {
      font-size: clamp(1.18rem, 5.8vw, 1.55rem);
    }

    .rm-shell-main .card,
    .rm-shell-main .panel,
    .rm-shell-main section {
      max-width: 100%;
      min-width: 0;
      box-sizing: border-box;
    }

    .rm-shell-main form {
      max-width: 100%;
    }
  }
</style>
<script id="rm-global-responsive-script-v1">
(() => {
  const SIDEBAR_TEXT = ['Dashboard', 'Adicionar Drive', 'Media Pool / Union', 'API / Extensão'];

  const rect = (node) => {
    try { return node.getBoundingClientRect(); }
    catch (_) { return { width: 0, height: 0, left: 0, right: 0 }; }
  };

  const findSidebar = () => {
    const explicit = document.querySelector('aside, .sidebar, #sidebar, nav.sidebar');
    if (explicit) {
      const text = explicit.textContent || '';
      if (SIDEBAR_TEXT.filter((x) => text.includes(x)).length >= 2) return explicit;
    }

    const nodes = Array.from(document.querySelectorAll('aside, nav, body > div, body > section'));
    return nodes.find((node) => {
      const text = node.textContent || '';
      const hits = SIDEBAR_TEXT.filter((x) => text.includes(x)).length;
      const r = rect(node);
      return hits >= 3 && r.width >= 120 && r.width <= 360 && r.left < 40;
    }) || null;
  };

  const findMain = (sidebar) => {
    const explicit = document.querySelector('main, .main-content, .page-content, .content-wrapper');
    if (explicit && explicit !== sidebar && !sidebar?.contains(explicit)) return explicit;

    if (sidebar?.parentElement) {
      const siblings = Array.from(sidebar.parentElement.children).filter((el) => el !== sidebar);
      siblings.sort((a, b) => rect(b).width - rect(a).width);
      if (siblings[0]) return siblings[0];
    }

    return document.body;
  };

  const markFluidPage = (main) => {
    if (!main || main === document.body) return;
    main.classList.add('rm-shell-main');

    const heading = main.querySelector('h1, h2');
    if (!heading) return;

    let node = heading.parentElement;
    let best = null;

    while (node && node !== main && node !== document.body) {
      const parent = node.parentElement;
      if (!parent) break;
      const r = rect(node);
      const pr = rect(parent);
      if (r.width > 420 && pr.width > 0) {
        const ratio = r.width / pr.width;
        const nodeCenter = r.left + r.width / 2;
        const parentCenter = pr.left + pr.width / 2;
        const centered = Math.abs(nodeCenter - parentCenter) < 90;
        if (ratio < 0.88 && centered) best = node;
      }
      node = parent;
    }

    if (best) best.classList.add('rm-fluid-page');

    const directContainer = Array.from(main.children).find((el) =>
      el.classList?.contains('container') || el.classList?.contains('content')
    );
    if (directContainer) directContainer.classList.add('rm-fluid-page');
  };

  const wrapTables = (main) => {
    if (!main) return;
    main.querySelectorAll('table').forEach((table) => {
      if (table.closest('.rm-global-table-scroll, .rm-api-table-scroll')) return;
      const wrapper = document.createElement('div');
      wrapper.className = 'rm-global-table-scroll';
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  };

  const markResponsiveLayouts = (main) => {
    if (!main) return;

    main.querySelectorAll('div, section, article').forEach((node) => {
      const cs = getComputedStyle(node);
      if (cs.display === 'grid' && node.children.length >= 2) {
        node.classList.add('rm-responsive-grid');
      }
    });

    const heading = main.querySelector('h1, h2');
    if (heading) {
      let node = heading.parentElement;
      for (let i = 0; node && node !== main && i < 4; i += 1, node = node.parentElement) {
        const hasAction = node.querySelector('button, .btn, a[role="button"], a.btn');
        if (hasAction) {
          node.classList.add('rm-page-header');
          break;
        }
      }
    }
  };

  const installMobileMenu = (sidebar) => {
    if (!sidebar) return;
    sidebar.classList.add('rm-shell-sidebar');

    if (!document.querySelector('.rm-mobile-menu-button')) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'rm-mobile-menu-button';
      button.setAttribute('aria-label', 'Abrir menu');
      button.setAttribute('aria-expanded', 'false');
      button.textContent = '☰';
      document.body.appendChild(button);

      const backdrop = document.createElement('div');
      backdrop.className = 'rm-mobile-menu-backdrop';
      document.body.appendChild(backdrop);

      const close = () => {
        document.body.classList.remove('rm-mobile-nav-open');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-label', 'Abrir menu');
        button.textContent = '☰';
      };

      const toggle = () => {
        const open = !document.body.classList.contains('rm-mobile-nav-open');
        document.body.classList.toggle('rm-mobile-nav-open', open);
        button.setAttribute('aria-expanded', String(open));
        button.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
        button.textContent = open ? '×' : '☰';
      };

      button.addEventListener('click', toggle);
      backdrop.addEventListener('click', close);
      sidebar.addEventListener('click', (event) => {
        if (event.target.closest('a')) close();
      });
      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') close();
      });
      window.addEventListener('resize', () => {
        if (window.innerWidth > 900) close();
      });
    }
  };

  const apply = () => {
    const sidebar = findSidebar();
    const main = findMain(sidebar);
    if (main && main !== document.body) main.classList.add('rm-shell-main');
    installMobileMenu(sidebar);
    markFluidPage(main);
    wrapTables(main);
    markResponsiveLayouts(main);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', apply, { once: true });
  } else {
    apply();
  }
})();
</script>
'''

patched = 0
for template in sorted(templates.rglob("*.html")):
    text = template.read_text(encoding="utf-8", errors="replace")
    if marker in text:
        continue

    lower = text.lower()
    # Inject only in complete documents. Child Jinja templates inherit the
    # base document and automatically receive this block through the base.
    if "<html" not in lower or "</body>" not in lower:
        continue

    pos = lower.rfind("</body>")
    text = text[:pos] + overlay + "\n" + text[pos:]
    template.write_text(text, encoding="utf-8")
    patched += 1

# Some builds use only child templates plus one uncommon shell name. If no
# complete document was found, inject into the template that visibly owns the
# sidebar/navigation.
if patched == 0:
    for template in sorted(templates.rglob("*.html")):
        text = template.read_text(encoding="utf-8", errors="replace")
        if marker in text:
            patched += 1
            continue
        if all(token in text for token in ("Dashboard", "Adicionar Drive", "API / Extensão")):
            block_end = text.lower().rfind("</body>")
            if block_end >= 0:
                text = text[:block_end] + overlay + "\n" + text[block_end:]
            else:
                text = text + "\n" + overlay + "\n"
            template.write_text(text, encoding="utf-8")
            patched += 1
            break

print(f"Responsive layout overlay OK: {patched} template(s) atualizado(s)")
