"""Check exact replay, early completion, paper examples, video and responsive layouts."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]


def main():
    output=ROOT/'data/results/preview';output.mkdir(exist_ok=True)
    examples=json.loads((ROOT/'visualization/comparison_examples.json').read_text(encoding='utf-8'))
    errors=[];requests=[];steps=0
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.goto((ROOT/'visualization/index.html').as_uri(),wait_until='load')
        assert page.locator('#comparison').is_visible()
        for example in examples:
            page.select_option('#cmp-example',example['id'])
            total=max(len(example['baseline']['trace']),len(example['pruned']['trace']))
            for step in range(total+1):
                page.evaluate('(s)=>QueryComparison.seek(s)',step)
                for method in ['baseline','pruned']:
                    trace=example[method]['trace'];count=min(step,len(trace))
                    assert page.locator(f'#cmp-{method}-count').inner_text()==str(count)
                    assert page.locator(f'#cmp-{method}-matrix td.visited').count()==count
                    found=count==len(trace) and example['answer']
                    assert page.locator(f'#cmp-{method}-matrix td.accepted').count()==int(found)
                    if found:
                        assert '可达' in page.locator(f'#cmp-{method}-state').inner_text()
                        assert ' → '.join(map(str,example[method]['path'])) in page.locator(f'#cmp-{method}-path').inner_text()
                steps+=1
            assert '两种方法' in page.locator('#cmp-outcome').inner_text()
            page.screenshot(path=str(output/f'comparison-{example["id"]}.png'),full_page=True)
        page.select_option('#cmp-example','wiki-positive')
        page.evaluate('QueryComparison.seek(2)')
        assert '已找到' in page.locator('#cmp-pruned-state').inner_text()
        assert page.locator('#cmp-baseline-state').inner_text()=='检查中'
        page.screenshot(path=str(output/'comparison-early.png'),full_page=True)
        contrast=page.evaluate('''()=>{
          const luminance=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4})
            .reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
          const selectors=['header>span','.section-heading p','.figure-legend','#cmp-pruned-boundary',
            '#cmp-baseline-pair','#cmp-baseline-matrix th','#cmp-pruned-graph .node-id'];
          return Object.fromEntries(selectors.map(selector=>{
            const e=document.querySelector(selector),s=getComputedStyle(e),color=e.tagName==='text'?s.fill:s.color;
            const rgb=color.match(/[\\d.]+/g).slice(0,3).map(Number);
            return [selector,1.05/(luminance(rgb)+.05)];
          }));
        }''')
        assert min(contrast.values())>=4.5,contrast
        page.evaluate('QueryComparison.renderTime(2.0)')
        assert page.evaluate('QueryComparison.state().phase')=='pruning'
        page.evaluate('QueryComparison.renderTime(3.4)')
        assert page.locator('#cmp-baseline-graph circle').count()==2
        assert page.locator('#cmp-baseline-matrix td.scanning').count()==1
        page.evaluate('QueryComparison.renderTime(4.5)')
        assert page.locator('#cmp-pruned-count').inner_text()=='2'
        assert '已找到' in page.locator('#cmp-pruned-state').inner_text()
        page.click('#cmp-reset');page.select_option('#cmp-pace','400');page.click('#cmp-play')
        page.wait_for_function("document.getElementById('cmp-baseline-count').textContent!=='0'")
        page.click('[data-tab="algorithm"]')
        assert not page.evaluate('QueryComparison.state().playing')
        for case in range(1,5):
            page.click(f'#case{case}');page.click('#finish')
            assert page.locator('#case-value').inner_text()==f'Case {case}'
            assert 'TRUE' in page.locator('#decision').inner_text()
        page.click('#negative');page.click('#finish')
        for codec in ['csr','dense','adaptive']:
            page.select_option('#codec',codec);page.click('#finish')
            assert 'FALSE' in page.locator('#decision').inner_text()
        page.click('#case4');page.select_option('#codec','csr');page.click('#finish')
        assert int(page.locator('#comparisons-value').inner_text())>0
        page.screenshot(path=str(output/'paper-demo-query.png'),full_page=True)
        page.click('#reset');page.click('#step');page.click('#back')
        assert '步骤 1' in page.locator('#progress').inner_text()
        page.click('[data-tab="dominance"]')
        for case,budget,answer,kept in [(3,'2','TRUE','d'),(4,'1','FALSE','b')]:
            page.click(f'#dom-case{case}');page.click('#dom-next');page.click('#dom-next')
            assert page.locator('#dom-budget').inner_text()==budget
            assert page.locator('#dom-answer').inner_text()==answer
            assert page.locator('#dom-raw-probes').inner_text()=='2'
            assert page.locator('#dom-cut-probes').inner_text()=='1'
            assert page.locator('.dom-keep-row td').first.inner_text()==kept
        page.screenshot(path=str(output/'paper-demo-dominance.png'),full_page=True)
        page.click('[data-tab="results"]')
        assert page.locator('.result-table tbody tr').count()==3
        for image in ['speed-chart','density-chart']:
            assert page.locator('#'+image).evaluate('(e)=>e.complete&&e.naturalWidth>0')
        page.screenshot(path=str(output/'comparison-results.png'),full_page=True)
        page.click('.technical-details>summary')
        for dataset in ['wiki-Vote','p2p-Gnutella31','email-EuAll']:
            page.select_option('#storage-dataset',dataset)
            assert page.locator('#dense-row .row-details').count()==1
        page.click('[data-tab="comparison"]')
        page.click('#cmp-fullscreen')
        page.wait_for_function("document.fullscreenElement===document.getElementById('comparison')")
        assert not page.locator('#cmp-baseline-matrix').is_visible()
        page.evaluate('QueryComparison.renderTime(4.7)')
        page.screenshot(path=str(output/'comparison-presentation.png'),full_page=True)
        page.evaluate('document.exitFullscreen()')
        for width,height in [(1920,1080),(1440,900),(1366,768),(1280,720)]:
            page.set_viewport_size({'width':width,'height':height})
            page.click('#cmp-fullscreen')
            page.wait_for_function('!!document.fullscreenElement')
            assert page.locator('#comparison').evaluate('(e)=>e.scrollHeight<=e.clientHeight+1&&e.scrollWidth<=e.clientWidth'),(width,height)
            page.evaluate('document.exitFullscreen()')
            page.wait_for_function('!document.fullscreenElement')
        page.set_viewport_size({'width':1440,'height':1000})
        page.click('.video-export>summary')
        page.click('#open-video')
        page.wait_for_function("document.getElementById('comparison-video').videoWidth===1920")
        video=json.loads((ROOT/'data/results/comparison_video_check.json').read_text())
        assert abs(page.locator('#comparison-video').evaluate('(e)=>e.duration')-video['duration_seconds'])<.1
        page.locator('#comparison-video').evaluate('(e)=>{e.currentTime=3.7;e.pause()}')
        page.wait_for_function("document.getElementById('comparison-video').readyState>=2")
        page.screenshot(path=str(output/'comparison-video-player.png'),full_page=True)
        page.click('#close-video')
        assert page.locator('#comparison-video').evaluate('(e)=>e.paused')
        for width in [1440,800,480,360]:
            page.set_viewport_size({'width':width,'height':1000})
            for tab in ['comparison','algorithm','dominance','results']:
                page.click(f'[data-tab="{tab}"]')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,tab)
            if width==480:
                page.click('[data-tab="comparison"]')
                page.screenshot(path=str(output/'comparison-mobile.png'),full_page=True)
        browser.close()
    assert not errors,errors
    assert not [u for u in requests if u.startswith('http')],requests
    result=dict(status='PASS',page_errors=[],external_http_requests=0,replayed_steps=steps,
        minimum_text_contrast=min(contrast.values()),
        checks=['three real query traces','early completion','playback and pause on tab switch',
                'four paper query cases','positive/negative decisions','three codecs','budget reversal',
                'storage details','real result figures','continuous pruning and moving lookup cursor',
                'text contrast at least 4.5:1','fullscreen webpage presentation','local 1080p MP4 playback',
                '1440px, 800px, 480px and 360px layouts'])
    (ROOT/'data/results/paper_demo_browser_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

