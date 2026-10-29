"""Compile twice, record logs, and place the named final PDF at project root."""
from pathlib import Path
import shutil
import subprocess
import sys
import json
import re
import fitz

ROOT=Path(__file__).resolve().parents[2]

def main():
    slide=ROOT/'docs/slides'
    for run in range(2):
        result=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-file-line-error','main.tex'],
                              cwd=slide,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        text=result.stdout.decode('utf-8',errors='replace')
        (slide/f'build-pass-{run+1}.txt').write_text(text,encoding='utf-8')
        if result.returncode:
            print(text[-6000:]);raise SystemExit(result.returncode)
    log=(slide/'main.log').read_text(encoding='utf-8',errors='replace')
    warnings=[line for line in log.splitlines()if any(s in line for s in ['Overfull','Missing character','undefined','Warning:'])]
    pdf=fitz.open(slide/'main.pdf')
    output=ROOT/'docs/第十三组-期中汇报.pdf'
    shutil.copyfile(slide/'main.pdf',output)
    info=dict(pages=len(pdf),page_size_points=list(pdf[0].rect),warnings=warnings,
              file=output.name,bytes=output.stat().st_size)
    (ROOT/'data/results/pdf_build_check.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
