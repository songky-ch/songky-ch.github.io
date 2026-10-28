from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1] / 'docs/.vitepress/dist'
entries = []

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and urlsplit(attrs.get('href', '')).path == '/demos/agent-lab/index.html':
            entries.append((page.relative_to(root).as_posix(), attrs.get('target')))

for page in root.rglob('*.html'):
    Links().feed(page.read_text())

assert entries, 'No laboratory entry links found in built pages'
unsafe = [page for page, target in entries if target != '_self']
assert not unsafe, f'Laboratory links intercepted by the document router: {unsafe}'
assert (root / 'demos/agent-lab/index.html').is_file()
print(f'PASS: {len(entries)} laboratory entries use full-page navigation')
