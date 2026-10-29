"""Acquire primary public inputs and record exact content hashes."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
JOBS=[
 ('https://snap.stanford.edu/data/wiki-Vote.txt.gz','data/raw/wiki-Vote.txt.gz'),
 ('https://snap.stanford.edu/data/p2p-Gnutella31.txt.gz','data/raw/p2p-Gnutella31.txt.gz'),
 ('https://snap.stanford.edu/data/email-EuAll.txt.gz','data/raw/email-EuAll.txt.gz'),
 ('https://www1.se.cuhk.edu.hk/~hcheng/paper/vldb2012.pdf','docs/papers/k-reach-2012.pdf'),
 ('https://mdpi-res.com/d_attachment/applsci/applsci-13-03470/article_deploy/applsci-13-03470.pdf','docs/papers/vcrea-2023.pdf'),
 ('https://arxiv.org/pdf/2311.03542','docs/papers/reachability-survey-2025.pdf'),
 ('https://raw.githubusercontent.com/sonnyhcl/beamerthemefdu/master/resources/background.pdf','docs/slides/resources/background.pdf'),
 ('https://raw.githubusercontent.com/sonnyhcl/beamerthemefdu/master/resources/fudan.pdf','docs/slides/resources/fudan.pdf'),
 ('https://raw.githubusercontent.com/sonnyhcl/beamerthemefdu/master/beamerthemefdu.sty','docs/slides/vendor-fdu/beamerthemefdu.sty'),
 ('https://raw.githubusercontent.com/sonnyhcl/beamerthemefdu/master/LICENSE','docs/slides/vendor-fdu/LICENSE'),
 ('https://raw.githubusercontent.com/sonnyhcl/beamerthemefdu/master/README.md','docs/slides/vendor-fdu/README.original.md'),
]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--proxy',help='Optional HTTP(S) proxy URL; default uses environment variables.')
    args=parser.parse_args()
    def fetch(job):
        url,relative=job;path=ROOT/relative
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':args.proxy,'https':args.proxy}))if args.proxy else urllib.request.build_opener()
            request=urllib.request.Request(url,headers={'User-Agent':'GraphCourseProject/2.0'})
            with opener.open(request,timeout=90)as response:content=response.read()
            if relative.endswith('.pdf')and not content.startswith(b'%PDF'):
                raise ValueError(f'Expected PDF: {url}')
            path.write_bytes(content)
        content=path.read_bytes()
        return dict(url=url,path=relative,bytes=len(content),sha256=hashlib.sha256(content).hexdigest())
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:
        for record in pool.map(fetch,JOBS):
            records.append(record)
            print(f"OK {record['path']} {record['bytes']:,}",flush=True)
    (ROOT/'data/source_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')


if __name__=='__main__':main()

