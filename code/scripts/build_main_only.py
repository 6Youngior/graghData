"""Build the main presentation plus references, preserving the complete PDF."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

import fitz


ROOT = Path(__file__).resolve().parents[2]


def main():
    slides = ROOT / 'docs/slides'
    original = ROOT / 'docs/第十三组-期中汇报.pdf'
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    report = (slides / 'report.tex').read_text(encoding='utf-8')
    appendix = (slides / 'qa.tex').read_text(encoding='utf-8')
    references = re.search(
        r'\\begin\{frame\}\{参考文献\}.*?\\end\{frame\}', appendix, re.S
    )
    if references is None or report.count(r'\appendix') != 1:
        raise RuntimeError('Cannot identify the main presentation and references')
    source = (
        report.split(r'\appendix', 1)[0]
        + '\\section{参考文献}\n'
        + references.group(0)
        + '\n\\end{document}\n'
    )
    output = ROOT / 'docs/第十三组-期中汇报-无附录版.pdf'
    with tempfile.TemporaryDirectory(prefix='main-only-', dir=slides) as directory:
        build = Path(directory)
        tex = build / 'main-only.tex'
        tex.write_text(source, encoding='utf-8')
        for _ in range(2):
            result = subprocess.run(
                ['xelatex', '-interaction=nonstopmode', '-halt-on-error',
                 '-file-line-error', f'-output-directory={build}', str(tex)],
                cwd=slides, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            if result.returncode:
                raise RuntimeError(result.stdout.decode('utf-8', errors='replace')[-6000:])
        log = (build / 'main-only.log').read_text(encoding='utf-8', errors='replace')
        warnings = [line for line in log.splitlines() if any(
            token in line for token in ('Overfull', 'Missing character', 'undefined', 'Warning:')
        )]
        if warnings:
            raise RuntimeError('\n'.join(warnings))
        with fitz.open(build / 'main-only.pdf') as pdf, fitz.open(original) as full:
            assert len(pdf) == 14
            for i, page in enumerate(pdf):
                text = page.get_text()
                assert '附录' not in text
                assert f'{i + 1} / 14' in text
                assert '\ufffd' not in text
            assert '参考文献' in pdf[-1].get_text()
            # Compare all slide content below the navigation and above the footer.
            def body_text(page):
                area = fitz.Rect(0, 16, page.rect.width, page.rect.height - 16)
                return re.sub(r'\s+', '', page.get_text(clip=area))
            for i in range(13):
                assert body_text(pdf[i]) == body_text(full[i]), f'Slide {i + 1} changed'
            assert body_text(pdf[-1]) == body_text(full[-1]), 'References changed'
            info = dict(
                status='PASS', file=output.name, pages=len(pdf),
                main_pages=13, reference_pages=1, warnings=warnings,
                original_unchanged=True, original_sha256=original_hash,
                body_and_references_unchanged=True,
            )
        shutil.copyfile(build / 'main-only.pdf', output)
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
    info['bytes'] = output.stat().st_size
    info['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    (ROOT / 'data/results/pdf_main_only_check.json').write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
