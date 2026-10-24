# frontend1/scripts/override_css.py
"""
Utility script to inject the landing‑page stylesheet into every
HTML page that isn’t part of the coach or admin sections, the
index page, or the student dashboard.
"""

import sys
from pathlib import Path

def main():
    root = Path('frontend1')
    landing_css = '../css/landing-page.css'

    # Walk through every *.html file
    for filepath in root.rglob('*.html'):
        # ---- Exclusions ---------------------------------------------
        # 1. Skip the landing page itself
        if filepath.name == 'landing-page.html':
            continue
        # 2. Skip the main index page
        if filepath.name == 'index.html':
            continue
        # 3. Skip the student‑dashboard page
        if filepath.parts[-1] == 'student-dashboard.html':
            continue
        # 4. Skip any page that lives inside a /coach or /admin folder
        if 'coach' in filepath.parts or 'admin' in filepath.parts:
            continue
        # ---- Find head tag -------------------------------------------
        content = filepath.read_text(encoding='utf-8')
        if landing_css in content:
            # Already linked – skip
            continue
        head_close_idx = content.lower().find('</head>')
        if head_close_idx == -1:
            print(f"❌ No </head> in {filepath}", file=sys.stderr)
            continue
        # ---- Insert landing‑page.css link --------------------------------
        new_tag = f'    <link rel="stylesheet" href="{landing_css}">\n'
        new_content = (
            content[:head_close_idx] + new_tag + content[head_close_idx:]
        )
        filepath.write_text(new_content, encoding='utf-8')
        print(f'✅ Updated {filepath}')

if __name__ == "__main__":
    main()
