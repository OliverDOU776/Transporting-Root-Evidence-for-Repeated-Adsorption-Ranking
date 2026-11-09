#!/usr/bin/env python3
"""Render the project's three silent, evidence-grounded research demonstrations.

Run from any directory: python scripts/render_demos.py
Requires Pillow and FFmpeg/ffprobe. Uses recorded native outputs and published
result summaries; the frame pacing never represents numerical execution time.
No new benchmark measurements or interpolated measurements are generated.
"""
from __future__ import annotations

import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "media"
W, H, FPS = 1280, 720, 12
BG, INK, MUTED = "#FAFBFC", "#122B3A", "#5C6C77"
TEAL, PURPLE, COPPER = "#117C78", "#72628D", "#A15F37"
RULE, LIGHT = "#D8E2E7", "#EEF4F5"
FONTDIR = Path("/usr/share/fonts/truetype/dejavu")


def font(size, bold=False, serif=False):
    stem = "DejaVuSerif" if serif else "DejaVuSans"
    path = FONTDIR / (stem + ("-Bold" if bold else "") + ".ttf")
    return ImageFont.truetype(str(path), size)


def txt(d, x, y, value, size=25, color=INK, bold=False, anchor=None, serif=False):
    d.text((x, y), str(value), font=font(size, bold, serif), fill=color, anchor=anchor)


def box(d, xy, fill="white", outline=RULE, radius=12):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2)


def base(number, title, subtitle):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    txt(d, 48, 23, "Repeated adsorption ranking", 17, MUTED, False)
    txt(d, 1232, 23, f"DEMO {number} / 03", 17, MUTED, anchor="ra")
    txt(d, 48, 65, title, 37, INK, True, serif=True)
    txt(d, 48, 119, subtitle, 23, MUTED)
    d.line((48, 158, 1232, 158), fill=RULE, width=2)
    return im, d


def footer(d, line1, line2):
    d.line((48, 634, 1232, 634), fill=RULE, width=2)
    txt(d, 48, 650, line1, 19, MUTED)
    txt(d, 48, 680, line2, 18, MUTED)


def vtt_time(seconds):
    ms = round(seconds * 1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}"


def encode(name, stages, poster_index=-1):
    """Stages are (image, duration seconds, plain-language caption)."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
           "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-metadata", "artist=Zijia Wang", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert p.stdin is not None
    for im, duration, _ in stages:
        raw = im.tobytes()
        for _ in range(round(duration * FPS)):
            p.stdin.write(raw)
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"FFmpeg failed for {name}")
    # Scientific states are held rather than tweened. A GIF needs one frame per
    # actual revealed state; duration preserves the same reading time as MP4.
    gifs = [im.resize((800, 450), Image.Resampling.LANCZOS).quantize(colors=128)
            for im, _, _ in stages]
    gifs[0].save(OUT / f"{name}.gif", save_all=True, append_images=gifs[1:],
                 duration=[round(s * 1000) for _, s, _ in stages], loop=0,
                 optimize=True, disposal=2)
    stages[poster_index][0].save(OUT / f"{name}-poster.png", optimize=True)
    t, captions = 0.0, ["WEBVTT", ""]
    for _, duration, caption in stages:
        captions.extend([f"{vtt_time(t)} --> {vtt_time(t+duration)}", caption, ""])
        t += duration
    (OUT / f"{name}.vtt").write_text("\n".join(captions), encoding="utf-8")
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,width,height,pix_fmt:format=duration", "-of", "json", str(path)]))
    return {"name": name, "duration_seconds": t, "width": W, "height": H,
            "fps": FPS, "audio": False, "encoding": probe,
            "files": {p.name: {"bytes": p.stat().st_size,
                                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(set(OUT.glob(name + ".*")) | {OUT / f"{name}-poster.png"})}}


def query_replay():
    data = json.loads((OUT / "query-replay-data.json").read_text())
    a, queries = data["acquisition"], data["queries"]
    seed_roots, seed_probes = int(a["root_solves"]), int(a["pi_probes"])
    stages = []
    total_t = int(data["setup"]["transport_pi_probes"]) + seed_probes
    total_f = int(data["setup"]["reference_pi_probes"])
    for index in range(-1, len(queries)):
        acquisition = index < 0
        q = None if acquisition else queries[index]
        if q is not None:
            assert q["matches_reference"] is True
            assert q["k"] == len(q["winner_ids"]) == len(q["scores"]) == 5
        im, d = base(1, "Repeated-query execution on synthetic isotherms",
                     "Recorded native execution on 144 synthetic piecewise-linear curve pairs")
        box(d, (48, 181, 686, 609))
        box(d, (710, 181, 1232, 609))
        if acquisition:
            txt(d, 74, 207, "First, acquire root evidence", 28, INK, True)
            txt(d, 74, 255, f"P = {a['pressure']:.3f} bar     y = {a['feed']:.3f}", 25)
            txt(d, 74, 328, "A complete initial query establishes", 25, MUTED)
            txt(d, 74, 368, "the source root enclosures.", 25, MUTED)
            txt(d, 74, 454, "This numerical work is paid once.", 27, TEAL, True)
            txt(d, 74, 529, "A same-state check, then five changes.", 23, MUTED)
        else:
            total_t += int(q["transport"]["pi_probes"])
            total_f += int(q["full_reference"]["pi_probes"])
            assert q["cumulative_pi_probes_including_setup_and_acquisition"] == {"transport": total_t, "full_reference": total_f}
            label = f"QUERY {index+1} / {len(queries)}" + (" · same-state check" if index == 0 else " · changed state")
            txt(d, 74, 205, label, 20, TEAL, True)
            txt(d, 74, 239, f"P = {q['pressure']:.3f} bar     y = {q['feed']:.3f}", 27, INK, True)
            txt(d, 74, 287, "Rank / pair ID", 20, MUTED)
            txt(d, 654, 287, "Selectivity", 20, MUTED, anchor="ra")
            max_s = max(q["scores"])
            for j, (pid, score) in enumerate(zip(q["winner_ids"], q["scores"])):
                y = 334 + j * 49
                txt(d, 74, y, f"{j+1:02}   #{pid}", 24, INK, True)
                d.rounded_rectangle((252, y+4, 252 + 245*score/max_s, y+27),
                                    radius=3, fill=TEAL)
                txt(d, 654, y, f"{score:.4f}", 24, INK, anchor="ra")
            txt(d, 74, 585, "IDs and scores match full solve; bars scale per query.", 19, TEAL)
        txt(d, 735, 207, "PAID INITIAL ACQUISITION", 18, MUTED, True)
        txt(d, 735, 241, f"{seed_roots:,} roots  ·  {seed_probes:,} probes", 24, INK, True)
        d.line((735, 288, 1207, 288), fill=RULE, width=2)
        if not acquisition:
            txt(d, 735, 307, "THIS QUERY", 18, MUTED, True)
            txt(d, 735, 346, "", 22)
            txt(d, 1207, 341, "Roots / probes", 19, MUTED, anchor="ra")
            txt(d, 735, 379, "Transport", 24, TEAL, True)
            txt(d, 1207, 379, f"{q['transport']['root_solves']:,} / {q['transport']['pi_probes']:,}", 24, TEAL, True, anchor="ra")
            txt(d, 735, 420, "Cold full solve", 24, MUTED)
            txt(d, 1207, 420, f"{q['full_reference']['root_solves']:,} / {q['full_reference']['pi_probes']:,}", 24, MUTED, anchor="ra")
            d.line((735, 466, 1207, 466), fill=RULE, width=2)
        txt(d, 735, 490, "CUMULATIVE PROBES (SETUP + SEED + QUERIES)", 16, MUTED, True)
        txt(d, 735, 528, f"Transport  {total_t:,}", 25, TEAL, True)
        txt(d, 735, 568, f"Cold full solve  {total_f:,}", 25, MUTED)
        footer(d, "Synthetic demonstration, not the CRAFTED benchmark. Probes are spreading-pressure API calls.",
               "Schematic pacing, not elapsed solver time. Cumulative probes include native setup and paid acquisition.")
        caption = (f"Paid acquisition: {seed_roots} root solves and {seed_probes} spreading-pressure probes."
                   if acquisition else
                   f"Query {index+1} ({'same-state check' if index==0 else 'changed state'}): recorded top-5 IDs and scores agree with a cold full solve. "
                   f"Transport uses {q['transport']['root_solves']} roots and {q['transport']['pi_probes']} probes. "
                   f"Cumulative probes include setup and acquisition: Transport {total_t}; cold full solve {total_f}.")
        stages.append((im, 3, caption))
    return encode("query-replay", stages)


def root_transport():
    # Exact analytic Henry example, identical to the manuscript figure.
    x0 = Fraction(1, 3)
    gamma = Fraction(11, 10)
    lo, hi = 1-gamma*(1-x0), gamma*x0
    upper = hi/(1-hi)
    assert (lo, hi, upper) == (Fraction(4,15), Fraction(11,30), Fraction(11,19))
    (OUT / "root-transport-data.json").write_text(json.dumps({
        "kind": "Exact analytical illustration, not a timing result",
        "curves": ["q1(p)=p", "q2(p)=2p"], "support": [0,10], "feed": "1/2",
        "source_pressure": "1", "target_pressure": "11/10", "source_root": str(x0),
        "transported_lower": str(lo), "transported_upper": str(hi),
        "score_upper": str(upper), "score_cut": "1",
        "derivation": "gamma1=gamma2=11/10; lower=1-gamma2*(1-x0); upper=gamma1*x0; score=x/(1-x) at equal feed"
    }, indent=2)+"\n")
    stages = []
    titles = ["1. Solve once at the source state", "2. Change pressure; transport the interval",
              "3. Compare its upper bound with the rank cut", "4. Exclude before a new integral evaluation"]
    captions = [
        "Analytical illustration: q1(p)=p and q2(p)=2p, equal feed, finite support 0 to 10. At pressure 1, the root is exactly one third.",
        "At pressure 1.1 and unchanged feed, arithmetic transport maps the exact source root to the interval [4/15,11/30]. The actual target root remains 1/3 in this Henry example.",
        "The selectivity upper bound is (11/30)/(1-11/30)=11/19, below an established destination score cut of 1.",
        "Given supported equilibrium and a valid eligible rank witness at score 1, this candidate can be excluded without probing its destination integral. This is an analytical mechanism illustration, not a new timing result."]
    for stage in range(4):
        im, d = base(2, "Transporting an equilibrium-root enclosure",
                     "An exact Henry-curve illustration: q₁(p) = p, q₂(p) = 2p; 0 ≤ p ≤ 10; y = 1/2")
        txt(d, 48, 184, titles[stage], 27, TEAL, True)
        box(d, (48, 234, 411, 595))
        txt(d, 73, 259, "SOURCE STATE", 19, MUTED, True)
        txt(d, 73, 300, "P = 1", 34, INK, True, serif=True)
        txt(d, 73, 359, "Solved root", 24, MUTED)
        txt(d, 73, 395, "x* = 1/3", 39, TEAL, True, serif=True)
        txt(d, 73, 478, "A source enclosure is", 23, MUTED)
        txt(d, 73, 513, "evidence we can reuse.", 23, MUTED)
        if stage >= 1:
            box(d, (440, 234, 1232, 595))
            txt(d, 466, 259, "DESTINATION STATE", 19, MUTED, True)
            txt(d, 466, 299, "P′ = 1.1     γ₁ = γ₂ = 11/10", 31, INK, True, serif=True)
            ax0, ax1, ay = 480, 1190, 425
            d.line((ax0, ay, ax1, ay), fill=INK, width=2)
            for val, label in [(0,"0"),(.5,"1/2"),(1,"1")]:
                xx = ax0+(ax1-ax0)*val
                d.line((xx,ay-5,xx,ay+6),fill=INK,width=2)
                txt(d,xx,ay+17,label,22,MUTED,anchor="ma")
            lx, ux = ax0+(ax1-ax0)*float(lo), ax0+(ax1-ax0)*float(hi)
            d.line((lx, ay-27, ux, ay-27), fill=TEAL, width=12)
            d.ellipse((lx-6,ay-33,lx+6,ay-21),fill=TEAL)
            d.ellipse((ux-6,ay-33,ux+6,ay-21),fill=TEAL)
            txt(d,(lx+ux)/2,ay-75,"[4/15, 11/30]",24,TEAL,True,anchor="ma")
            xx=ax0+(ax1-ax0)/3
            d.ellipse((xx-5,ay-5,xx+5,ay+5),fill=INK)
            if stage >= 2:
                xx=ax0+(ax1-ax0)*.5
                for yy in range(350,432,12):d.line((xx,yy,xx,yy+6),fill=COPPER,width=2)
                txt(d,xx+17,357,"cut x = 1/2",22,COPPER)
                txt(d,466,488,"Score upper = 11/19 < 1",31,TEAL,True,serif=True)
            else:
                txt(d,466,490,"Arithmetic only; no destination integral.",25,TEAL,True)
            if stage >= 3:
                d.rounded_rectangle((466,540,1207,580),radius=5,fill="#E3F1ED")
                txt(d,836,546,"Excluded by transported score bound",23,TEAL,True,anchor="ma")
        footer(d,"Exact analytical illustration; the source/target are not new benchmark measurements.",
               "Exclusion assumes supported equilibrium, a valid source enclosure, and an established eligible rank witness.")
        stages.append((im,4,captions[stage]))
    return encode("root-transport",stages)


def acquisition_cost():
    source=ROOT/"evidence"/"published_results.csv"
    rows=[r for r in csv.DictReader(source.open()) if r["study"]=="original" and r["dataset"]=="crafted"
          and r["control"]=="LeanCap" and r["k"]=="1"]
    prefixes=[1,8,16,32,64]
    by={(r["regime"],int(r["queries"])):r for r in rows}
    stages=[]
    for count in range(1,6):
        im,d=base(3,"Acquisition cost across query horizons",
                  "Recorded CRAFTED CO₂/N₂, 298 K · 16,010 configuration pairs · top-1 · Transport / LeanCap")
        x0,x1,y0,y1=190,1190,560,225
        axleft=135
        ymin,ymax=.35,1.45
        xf=lambda j:x0+(x1-x0)*j/4
        yf=lambda val:y0-(y0-y1)*(val-ymin)/(ymax-ymin)
        for val in [.5,.75,1,1.25]:
            yy=yf(val)
            if val==1:
                for xx in range(axleft,x1,15):d.line((xx,yy,xx+7,yy),fill=COPPER,width=2)
            else:d.line((axleft,yy,x1,yy),fill=RULE,width=1)
            txt(d,axleft-18,yy,f"{val:.2f}",21,MUTED,anchor="rm")
        d.line((axleft,y1,axleft,y0,x1,y0),fill=INK,width=2)
        txt(d,48,184,"Paid-time ratio",21,INK,True)
        txt(d,1190,184,"Below 1 = faster",21,TEAL,True,anchor="ra")
        for j,p in enumerate(prefixes):
            txt(d,xf(j),y0+19,str(p),23,INK,anchor="ma")
            if j>=count:continue
            for regime,color,dx in [("near",TEAL,-9),("far",PURPLE,9)]:
                r=by[(regime,p)];xx=xf(j)+dx
                lo,hi,med=map(lambda key:float(r[key]),["min_paid_ratio","max_paid_ratio","median_paid_ratio"])
                d.line((xx,yf(lo),xx,yf(hi)),fill=color,width=3)
                for val in [lo,hi]:d.line((xx-6,yf(val),xx+6,yf(val)),fill=color,width=2)
                yy=yf(med);d.ellipse((xx-6,yy-6,xx+6,yy+6),fill=color)
                # Labels show measured medians; the observations are never joined
                # into a visually interpolated timing curve.
                offset=(47 if j==0 else 21) if regime=="near" else -30
                txt(d,xx+(45 if j==0 else 0),yy+offset,f"{med:.3f}",21,color,True,anchor="ma")
        txt(d,660,603,"Measured number of changed queries (categorical positions)",21,MUTED,anchor="ma")
        d.ellipse((451,177,463,189),fill=TEAL);txt(d,474,174,"Near",20,TEAL,True)
        d.ellipse((568,177,580,189),fill=PURPLE);txt(d,591,174,"Far",20,PURPLE,True)
        footer(d,"Medians and observed ranges of 3 paired technical blocks; setup, acquisition and teardown included.",
               "Only measured prefixes are shown. No confidence intervals, exact break-even estimate, or universal speedup claim.")
        if count==1:caption="At one changed query, acquisition makes Transport slower than LeanCap in all three blocks, for both shown regimes."
        elif count==5:caption="At 64 changed queries, paired median paid-time ratios are 0.500 for near and 0.601 for far. Both regimes favor Transport in all three measured blocks."
        else:caption=f"Reveal the measured prefix of {prefixes[count-1]} changed queries. Points are median within-block paid-time ratios; error bars show their observed minimum and maximum, not confidence intervals."
        stages.append((im,4,caption))
    return encode("acquisition-cost",stages)


def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("Install FFmpeg (including ffprobe) before rendering.")
    OUT.mkdir(parents=True,exist_ok=True)
    reports=[query_replay(),root_transport(),acquisition_cost()]
    (OUT/"media-manifest.json").write_text(json.dumps({
        "author":"Zijia Wang", "renderer":"scripts/render_demos.py",
        "scientific_note":"Demonstration pacing is schematic, never a solver clock. Synthetic native trace, exact analytic example, and measured benchmark prefixes are distinguished.",
        "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/"query-replay-data.json", ROOT/"evidence"/"published_results.csv"]},
        "demos":reports},indent=2)+"\n")
    for report in reports:
        print(report["name"],report["duration_seconds"],"s",sum(f["bytes"] for f in report["files"].values()),"bytes")


if __name__=="__main__":
    main()
