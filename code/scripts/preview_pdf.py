"""Raster previews and contact sheets for visual inspection, plus text bounds."""
from pathlib import Path
import json
import fitz
from PIL import Image,ImageOps,ImageDraw

ROOT=Path(__file__).resolve().parents[2]

def main():
    doc=fitz.open(ROOT/'docs/第十三组-期中汇报.pdf')
    out=ROOT/'data/results/preview/slides'
    out.mkdir(parents=True,exist_ok=True)
    thumbnails=[];issues=[]
    for i,page in enumerate(doc):
        pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        image.save(out/f'page-{i+1:02}.png')
        thumb=image.resize((640,360))
        canvas=Image.new('RGB',(660,392),'#e8edf2')
        canvas.paste(thumb,(10,10));ImageDraw.Draw(canvas).text((12,374),f'PAGE {i+1:02}',fill='#112442')
        thumbnails.append(canvas)
        for block in page.get_text('dict')['blocks']:
            if 'lines'not in block:continue
            for line in block['lines']:
                for span in line['spans']:
                    rect=fitz.Rect(span['bbox'])
                    if rect.x0<0 or rect.y0<0 or rect.x1>page.rect.width+.5 or rect.y1>page.rect.height+.5:
                        issues.append(dict(page=i+1,text=span['text'],bbox=list(rect)))
        assert '\ufffd'not in page.get_text(),f'Broken text on page {i+1}'
    for start in range(0,len(thumbnails),6):
        sheet=Image.new('RGB',(1320,1176),'white')
        for j,thumb in enumerate(thumbnails[start:start+6]):sheet.paste(thumb,((j%2)*660,(j//2)*392))
        sheet.save(out/f'contact-{start//6+1}.png')
    result=dict(pages=len(doc),text_outside_page=issues,contact_sheets=(len(thumbnails)+5)//6)
    (ROOT/'data/results/pdf_visual_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
