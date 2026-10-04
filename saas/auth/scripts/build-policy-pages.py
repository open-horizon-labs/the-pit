"""Render the public information routes from the same text used by the SPA."""
from pathlib import Path
import ast
import html
root = Path(__file__).resolve().parents[1]
source = (root / 'src/main.ts').read_text()
pages = ast.literal_eval(source.split('const info:Record<string,string[]>=',1)[1].split(';\nasync function main()',1)[0])
for route, paragraphs in pages.items():
    destination = root / 'public' / route.strip('/') / 'index.html'
    destination.parent.mkdir(parents=True, exist_ok=True)
    body = '<h1>The Pit</h1><nav><a href="/">Account</a> · <a href="/support">Support</a> · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></nav><h2>' + html.escape(paragraphs[0]) + '</h2>'
    body += ''.join('<p>' + html.escape(line) + '</p>' for line in paragraphs[1:])
    destination.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(paragraphs[0]) + ' — The Pit</title><style>body{font:17px system-ui;background:#171918;color:#eee;max-width:720px;margin:48px auto;padding:0 24px;line-height:1.65}a{color:#d1ecda}h1{font-size:3rem;letter-spacing:-.06em}</style><main>' + body + '</main></html>')
