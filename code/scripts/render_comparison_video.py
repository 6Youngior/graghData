"""Export the deterministic SVG motion timeline as a 1080p, 60 fps video."""
from pathlib import Path
import json
import math
import shutil
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
FPS=60
PACE=.65


def main():
    ffmpeg=shutil.which('ffmpeg')
    ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise SystemExit('FFmpeg and ffprobe are required for video export.')
    output=ROOT/'visualization/方法对比.mp4'
    temporary=output.with_name('方法对比.tmp.mp4')
    examples=json.loads((ROOT/'visualization/comparison_examples.json').read_text(encoding='utf-8'))
    errors=[];frames=0;chapters=[]
    command=[ffmpeg,'-y','-hide_banner','-loglevel','error','-f','image2pipe','-framerate',str(FPS),
        '-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p',
        '-movflags','+faststart',str(temporary)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':1600,'height':900},device_scale_factor=1.2)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto((ROOT/'visualization/index.html').as_uri(),wait_until='load')
            page.evaluate("document.body.classList.add('recording')")
            page.evaluate('document.fonts.ready')
            for example in examples:
                page.evaluate('(id)=>QueryComparison.select(id)',example['id'])
                duration=page.evaluate('(pace)=>QueryComparison.duration(pace)',PACE)
                count=math.ceil(duration*FPS)
                chapters.append(dict(example=example['id'],start_seconds=frames/FPS,duration_seconds=count/FPS))
                for frame in range(count):
                    page.evaluate('([t,pace])=>QueryComparison.renderTime(t,pace)',[frame/FPS,PACE])
                    if frame%240==0:
                        bounds=page.locator('#comparison').bounding_box()
                        assert bounds['y']+bounds['height']<=900,(example['id'],bounds)
                        print(f"{example['id']}: {frame}/{count} frames",flush=True)
                    process.stdin.write(page.screenshot(type='png'))
                    frames+=1
                assert page.locator('#cmp-baseline-count').inner_text()==str(len(example['baseline']['trace']))
                assert page.locator('#cmp-pruned-count').inner_text()==str(len(example['pruned']['trace']))
            browser.close()
        assert not errors,errors
        process.stdin.close()
        diagnostic=process.stderr.read().decode('utf-8',errors='replace')
        assert process.wait(timeout=120)==0,diagnostic
    except BaseException:
        process.kill();process.wait()
        raise
    metadata=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(temporary)]))
    stream=metadata['streams'][0]
    assert stream['codec_name']=='h264' and stream['width']==1920 and stream['height']==1080
    assert stream['r_frame_rate']=='60/1' and int(stream['nb_frames'])==frames
    assert abs(float(metadata['format']['duration'])-frames/FPS)<.05
    temporary.replace(output)
    # A short preview lets the repository show the animation directly.
    gif=ROOT/'visualization/查询对比.gif'
    palette='fps=15,scale=1280:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3'
    subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-ss','1.1','-t','8.0','-i',str(output),
        '-filter_complex',palette,'-loop','0',str(gif)],check=True)
    report=dict(status='PASS',file=output.name,width=stream['width'],height=stream['height'],
        fps=stream['r_frame_rate'],duration_seconds=float(metadata['format']['duration']),
        bytes=output.stat().st_size,examples=[e['id'] for e in examples],unique_frames=frames,
        chapters=chapters,playback='Deterministic continuous SVG animation; one core lookup per shared step.',
        preview=gif.name)
    (ROOT/'data/results/comparison_video_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

