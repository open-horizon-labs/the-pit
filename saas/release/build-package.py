"""Build the portable hosted package from an explicit, credential-free allowlist."""
from pathlib import Path
import json,shutil
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]
package=root/'plugin'
companion=root.parent/'plugin'
# Share reviewed local runtime code; do not ship legacy auth, migration or personal state.
shared=['hooks/hooks.json','hooks/precompact.py','hooks/retrieval_context.py',
        'metrics/pit_metrics.py','metrics/scan_usage.py',
        'skills/export-to-pit/scripts/export_session.py',
        'skills/export-to-pit/scripts/hosted_client.py',
        'skills/export-to-pit/scripts/pit_support.py']
for rel in shared:
    source=companion/rel
    if source.is_symlink():raise ValueError('Shared package source cannot be a symlink')
    target=package/rel;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
manifest=json.loads((package/'plugin.json').read_text())
version=manifest['version']
files=[package/name for name in ['plugin.json','mcp.json','.app.json','INSTALL.md','LOCAL.md']+shared]
files+=sorted((package/'skills').rglob('SKILL.md'))
files+=sorted((package/'assets').glob('*.svg'))
assert len(list((package/'skills').rglob('SKILL.md')))==3
for name in ('plugin.json','mcp.json','.app.json','hooks/hooks.json'):
    json.loads((package/name).read_text())
assert manifest['extensions']['com.openai']['hooks']=='./hooks/hooks.json'
for field in ('logo','composerIcon'):
    assert (package/manifest['extensions']['com.openai']['interface'][field]).is_file()
for file in files:
    assert file.is_file() and not file.is_symlink()
    assert file.resolve().is_relative_to(package.resolve())
out=root/'dist'/f'the-pit-hosted-{version}.zip';out.parent.mkdir(exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as archive:
    for file in files:archive.write(file,file.relative_to(package))
print(out)
