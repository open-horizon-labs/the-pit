"""Build the portable hosted package without local credentials or release drafts."""
from pathlib import Path
import json
from zipfile import ZipFile, ZIP_DEFLATED
root = Path(__file__).resolve().parents[1]
package = root / 'plugin'
manifest = json.loads((package / 'plugin.json').read_text())
version = manifest['version']
files = [package/'plugin.json', package/'mcp.json', package/'.app.json', package/'INSTALL.md']
files += sorted((package/'skills').rglob('SKILL.md'))
files += sorted((package/'assets').glob('*.svg'))
assert len(list((package/'skills').rglob('SKILL.md'))) == 2
for name in ('plugin.json','mcp.json','.app.json'):
    json.loads((package/name).read_text())
for field in ('logo','composerIcon'):
    assert (package / manifest['extensions']['com.openai']['interface'][field]).is_file()
out=root/'dist'/f'the-pit-hosted-{version}.zip'
out.parent.mkdir(exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as archive:
    for file in files:
        archive.write(file,file.relative_to(package))
print(out)
