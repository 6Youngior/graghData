"""Validate that every page actually uses the original FDU Beamer theme."""
from pathlib import Path
import hashlib,json,re
import fitz
ROOT=Path(__file__).resolve().parents[2]
EXPECTED='9f6115ae955c02b47d26df5bff00a2a9c687bbb1'


def main():
    sty=(ROOT/'docs/slides/vendor-fdu/beamerthemefdu.sty').read_bytes()
    blob=hashlib.sha1(f'blob {len(sty)}\0'.encode()+sty).hexdigest()
    assert blob==EXPECTED,'FDU upstream theme modified'
    source=(ROOT/'docs/slides/report.tex').read_text(encoding='utf-8')
    assert r'\usetheme{fdu}'in source and r'\titlepage'in source
    for name in ['background','background canvas','frametitle','footline','headline','title page']:
        assert not re.search(r'\\setbeamertemplate\s*\{'+re.escape(name)+r'\}',source),name
    pdf=fitz.open(ROOT/'docs/第十三组-期中汇报.pdf')
    marked=[];forms=[]
    for i,page in enumerate(pdf):
        text=re.sub(r'\s+','',page.get_text())
        assert '第十三组'in text,(i+1,'Missing group name in native footer')
        assert '第十三组(复旦大学)'not in text and '第十三组（复旦大学）'not in text
        assert '10分钟报告'not in text and '2分钟问答'not in text
        # XeLaTeX may emit a distinct xref for the same imported PDF on each
        # page. Compare decoded form content rather than object numbers.
        forms.append({hashlib.sha256(pdf.xref_stream(x[0])or b'').hexdigest()
                      for x in page.get_xobjects()})
        marked.append(i+1)
    shared=set.intersection(*forms)
    assert shared,'No shared FDU watermark form across all pages'
    result=dict(status='PASS',theme='sonnyhcl/beamerthemefdu',license='Apache-2.0',
        upstream_git_blob_sha=blob,upstream_sty_unmodified=True,
        native_templates_preserved=['title page','headline','frametitle','footline','background canvas'],
        group_identity_pages=marked,shared_watermark_stream_sha256=sorted(shared))
    (ROOT/'data/results/theme_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

