"""Generate a blinded local human-review queue with timing and JSON export."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json


def blinded_order(candidate_ids: list[str], seed: int) -> list[str]:
    rng = np.random.default_rng(seed)
    return [candidate_ids[index] for index in rng.permutation(len(candidate_ids))]


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _dilate(mask: np.ndarray, radius: int = 1) -> np.ndarray:
    """Small dependency-free dilation used only to keep overlays legible."""
    padded = np.pad(mask.astype(bool), radius)
    result = np.zeros_like(mask, dtype=bool)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            result |= padded[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return result


def _draw_candidate_bounds(rgb: np.ndarray, oy: int, ox: int, height: int, width: int) -> None:
    color = np.asarray([255, 184, 0], dtype=np.uint8)
    rgb[oy:oy + 2, ox:ox + width] = color
    rgb[oy + height - 2:oy + height, ox:ox + width] = color
    rgb[oy:oy + height, ox:ox + 2] = color
    rgb[oy:oy + height, ox + width - 2:ox + width] = color


def preview_views(
    prediction: np.ndarray,
    bounds: dict[str, int],
    component: np.ndarray,
    skeleton: np.ndarray,
    halo: int,
) -> dict[str, np.ndarray]:
    """Build independent evidence, mask, and overlay views for human review."""
    y0, y1, x0, x1 = bounds["y0"], bounds["y1"], bounds["x0"], bounds["x1"]
    py0, py1 = max(0, y0 - halo), min(prediction.shape[0], y1 + halo)
    px0, px1 = max(0, x0 - halo), min(prediction.shape[1], x1 + halo)
    raw = prediction[py0:py1, px0:px1].astype(np.uint8)
    values = raw.astype(np.float32)
    low, high = np.quantile(values, [0.01, 0.99])
    enhanced_gray = np.clip((values - low) * (255.0 / max(1.0, high - low)), 0, 255).astype(np.uint8)
    raw_rgb = np.repeat(raw[..., None], 3, axis=2)
    enhanced = np.repeat(enhanced_gray[..., None], 3, axis=2)
    overlay = enhanced.copy()
    mask_view = np.full_like(enhanced, 18)
    oy, ox = y0 - py0, x0 - px0
    region_overlay = overlay[oy:oy + component.shape[0], ox:ox + component.shape[1]]
    region_mask = mask_view[oy:oy + component.shape[0], ox:ox + component.shape[1]]
    component_bool = component.astype(bool)
    skeleton_bold = _dilate(skeleton.astype(bool), 1)
    # Opaque mask view and alpha-blended overlay remain visible over saturated white.
    region_mask[component_bool] = np.asarray([225, 42, 92], dtype=np.uint8)
    region_overlay[component_bool] = (
        0.35 * region_overlay[component_bool] + 0.65 * np.asarray([225, 42, 92])
    ).astype(np.uint8)
    region_mask[skeleton_bold] = np.asarray([0, 235, 255], dtype=np.uint8)
    region_overlay[skeleton_bold] = np.asarray([0, 235, 255], dtype=np.uint8)
    for view in (raw_rgb, enhanced, mask_view, overlay):
        _draw_candidate_bounds(view, oy, ox, component.shape[0], component.shape[1])
    return {"raw": raw_rgb, "enhanced": enhanced, "mask": mask_view, "overlay": overlay}


def _html(queue: list[dict[str, Any]], options: list[str], experiment_id: str) -> str:
    payload = json.dumps(queue, separators=(",", ":"))
    labels = {
        "plausible_structure": ("Struttura plausibile", "Vedo una traccia localizzata e il ciano ne segue il centro."),
        "imaging_or_model_artifact": ("Artefatto", "Vedo soprattutto una macchia, un bordo o un gradiente esteso."),
        "no_coherent_signal": ("Nessun segnale coerente", "Non vedo una traccia continua sostenuta dall'immagine."),
        "uncertain": ("Incerto", "Le viste non permettono una decisione affidabile."),
    }
    option_buttons = "".join(
        f'<button class="response" data-value="{option}"><strong>{labels[option][0]}</strong><small>{labels[option][1]}</small></button>'
        for option in options
    )
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>InkSurf — revisione cieca</title>
<style>:root{{--bg:#11151b;--panel:#1a2029;--line:#344050;--text:#f3f5f7;--muted:#aeb8c5;--accent:#ffb800;--cyan:#00ebff;--mask:#e12a5c}}
*{{box-sizing:border-box}}body{{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);max-width:1280px;margin:0 auto;padding:24px}}
h1{{margin-bottom:4px}}h2{{font-size:1.15rem}}.muted,small{{color:var(--muted)}}.notice,.guide,.decision{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin:14px 0}}
.notice strong{{color:var(--accent)}}.views{{display:grid;grid-template-columns:repeat(2,minmax(280px,1fr));gap:14px}}figure{{margin:0;background:var(--panel);padding:10px;border-radius:8px}}
figcaption{{font-weight:650;margin-bottom:8px}}figure small{{display:block;font-weight:400;margin-top:2px}}img{{display:block;width:100%;border:1px solid var(--line)}}
.questions{{display:grid;gap:10px}}.question{{display:grid;grid-template-columns:minmax(260px,1fr) auto;align-items:center;gap:12px}}.choices button{{margin:2px;padding:7px 12px;background:#27313e;color:var(--text);border:1px solid #526174;border-radius:6px}}
.choices button.selected{{background:#174c59;border-color:var(--cyan)}}#suggestion{{border-left:4px solid var(--accent);padding:8px 12px;margin:12px 0;background:#202733}}
.responses{{display:grid;grid-template-columns:repeat(2,minmax(220px,1fr));gap:8px}}button.response{{text-align:left;padding:12px;background:#283342;color:var(--text);border:1px solid #526174;border-radius:7px;cursor:pointer}}
button.response:hover{{border-color:var(--accent)}}button.response small{{display:block;margin-top:4px}}label{{display:block;margin:12px 0}}input[type=number]{{width:60px;padding:6px}}textarea{{width:100%;height:70px;background:#f8fafc;color:#111;padding:8px}}
.nav{{display:flex;justify-content:space-between;align-items:center}}button.secondary{{padding:8px 12px;background:transparent;color:var(--text);border:1px solid #526174;border-radius:6px}}#done{{display:none;text-align:center;padding:60px 10px}}#export{{padding:12px 18px}}
@media(max-width:760px){{.views,.responses{{grid-template-columns:1fr}}.question{{grid-template-columns:1fr}}body{{padding:12px}}}}</style></head>
<body><h1>InkSurf — revisione strutturale cieca</h1><p class="muted">Il rango, lo score e le label sono nascosti. La revisione valuta la qualità strutturale, non prova la presenza di inchiostro.</p>
<div class="notice"><strong>Regola principale:</strong> decidi prima dalle due immagini in grigio. Usa maschera e skeleton soltanto per verificare se l'algoritmo ha seguito una struttura realmente visibile. Arancione = area candidata; magenta = maschera; ciano = skeleton.</div>
<div id="review"><div class="nav"><h2 id="progress"></h2><button id="back" class="secondary" type="button">← Indietro</button></div>
<div class="views">
<figure><figcaption>1. Predizione originale<small>Scala fissa 0–255; permette confronti tra candidati.</small></figcaption><img id="raw" alt="Predizione originale senza elaborazione"></figure>
<figure><figcaption>2. Contrasto locale<small>Contrasto migliorato solo per rendere visibili variazioni deboli.</small></figcaption><img id="enhanced" alt="Predizione con contrasto locale"></figure>
<figure><figcaption>3. Estrazione dell'algoritmo<small>Magenta: area sopra soglia. Ciano: asse centrale derivato.</small></figcaption><img id="mask" alt="Maschera e skeleton su fondo scuro"></figure>
<figure><figcaption>4. Controllo di corrispondenza<small>Verifica se i colori seguono qualcosa di visibile nel grigio.</small></figcaption><img id="overlay" alt="Sovrapposizione di maschera e skeleton"></figure>
</div>
<div class="guide"><h2>Tre domande guida</h2><div class="questions">
<div class="question"><span>1. Nelle immagini grigie vedi una traccia localizzata, distinta dallo sfondo?</span><div class="choices" data-question="localized"><button data-answer="yes">Sì</button><button data-answer="no">No</button><button data-answer="uncertain">Non so</button></div></div>
<div class="question"><span>2. Il segnale sembra soprattutto una grande macchia, un bordo o un gradiente?</span><div class="choices" data-question="broad"><button data-answer="yes">Sì</button><button data-answer="no">No</button><button data-answer="uncertain">Non so</button></div></div>
<div class="question"><span>3. Lo skeleton ciano segue il centro della traccia visibile, invece di inventarne la forma?</span><div class="choices" data-question="supported"><button data-answer="yes">Sì</button><button data-answer="no">No</button><button data-answer="uncertain">Non so</button></div></div>
</div><div id="suggestion">Rispondi alle tre domande: comparirà un suggerimento non vincolante.</div></div>
<div class="decision"><h2>Valutazione finale</h2><div class="responses">{option_buttons}</div>
<label>Confidenza (1 = ipotesi, 3 = moderata, 5 = evidente): <input id="confidence" type="number" min="1" max="5" value="3"></label>
<textarea id="notes" placeholder="Nota facoltativa: descrivi ciò che vedi, senza cercare di riconoscere lettere."></textarea></div></div>
<div id="done"><h2>Revisione completata</h2><p>I risultati sono rimasti nel browser. Esportali per consegnarli a InkSurf.</p><button id="export">Esporta review JSON</button><p><button id="reopen" class="secondary">Rivedi l'ultimo candidato</button></p></div>
<script>const experiment={json.dumps(experiment_id)}, queue={payload}, storageKey='inksurf-review:'+experiment;
let saved=JSON.parse(localStorage.getItem(storageKey)||'null'), index=saved?.index||0, results=saved?.results||[], started=performance.now(), answers={{}};
const ids=['raw','enhanced','mask','overlay'];
function persist(){{localStorage.setItem(storageKey,JSON.stringify({{index,results}}));}}
function resetForm(){{answers={{}};document.querySelectorAll('.choices button').forEach(b=>b.classList.remove('selected'));document.getElementById('suggestion').textContent='Rispondi alle tre domande: comparirà un suggerimento non vincolante.';document.getElementById('notes').value='';document.getElementById('confidence').value=3;}}
function suggest(){{if(Object.keys(answers).length<3)return;let text='Suggerimento: Incerto.';if(answers.broad==='yes')text='Suggerimento: Artefatto — prevale una struttura estesa o un bordo.';else if(answers.localized==='no')text='Suggerimento: Nessun segnale coerente — manca una traccia localizzata.';else if(answers.localized==='yes'&&answers.supported==='yes')text='Suggerimento: Struttura plausibile — la traccia è visibile e sostiene lo skeleton.';document.getElementById('suggestion').textContent=text;}}
function show(){{const review=document.getElementById('review'),done=document.getElementById('done');if(index>=queue.length){{review.style.display='none';done.style.display='block';persist();return;}}review.style.display='block';done.style.display='none';document.getElementById('progress').textContent=`Candidato ${{index+1}} di ${{queue.length}} · ID cieco ${{queue[index].blind_id}}`;ids.forEach(id=>document.getElementById(id).src=queue[index].previews[id]);document.getElementById('back').disabled=index===0;resetForm();started=performance.now();persist();}}
document.querySelectorAll('.choices').forEach(group=>group.querySelectorAll('button').forEach(button=>button.onclick=()=>{{group.querySelectorAll('button').forEach(b=>b.classList.remove('selected'));button.classList.add('selected');answers[group.dataset.question]=button.dataset.answer;suggest();}}));
document.querySelectorAll('.response').forEach(button=>button.onclick=()=>{{if(Object.keys(answers).length<3){{alert('Rispondi prima alle tre domande guida.');return;}}const confidence=Number(document.getElementById('confidence').value);if(confidence<1||confidence>5){{alert('La confidenza deve essere compresa tra 1 e 5.');return;}}results.push({{blind_id:queue[index].blind_id,candidate_id:queue[index].candidate_id,response:button.dataset.value,confidence,diagnostic_answers:answers,notes:document.getElementById('notes').value,elapsed_seconds:(performance.now()-started)/1000}});index++;show();}});
function goBack(){{if(index===0)return;index--;results.pop();show();}}document.getElementById('back').onclick=goBack;document.getElementById('reopen').onclick=goBack;
document.getElementById('export').onclick=()=>{{const body={{experiment_id:experiment,completed_at:new Date().toISOString(),ui_version:2,results}};const blob=new Blob([JSON.stringify(body,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=experiment+'_review.json';a.click();}};show();</script></body></html>"""


def run(config_path: Path) -> dict[str, Any]:
    import tifffile
    from PIL import Image

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["regime"] != "DEV":
        raise PermissionError("review queue currently permits DEV only")
    root = config_path.resolve().parent.parent
    package = json.loads((root / config["candidate_package"]).read_text(encoding="utf-8"))
    artifacts = json.loads((root / config["artifact_manifest"]).read_text(encoding="utf-8"))
    if package["surface_id"] != artifacts["surface_id"] or package["geometry_tier"] != "G2":
        raise ValueError("review inputs do not identify the same G2 surface")
    artifact_by_id = {item["candidate_id"]: item for item in artifacts["candidates"]}
    prediction = tifffile.imread(root / config["prediction_tif"], key=0)
    output_dir = root / config["local_output_directory"]
    preview_dir = output_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    order = blinded_order([item["candidate_id"] for item in package["candidates"]], int(config["seed"]))
    candidates = {item["candidate_id"]: item for item in package["candidates"]}
    queue = []
    for number, candidate_id in enumerate(order, 1):
        candidate = candidates[candidate_id]
        artifact = artifact_by_id[candidate_id]
        path = root / artifact["artifact_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {candidate_id}")
        with np.load(path) as arrays:
            views = preview_views(
                prediction, candidate["bounds_yx"], arrays["component_mask"], arrays["skeleton"],
                int(config["context_halo_pixels"]),
            )
        blind_id = f"B{number:03d}"
        preview_paths = {}
        for view_name, preview in views.items():
            preview_path = preview_dir / f"{blind_id}_{view_name}.png"
            fd, temporary = tempfile.mkstemp(prefix=preview_path.name + ".", suffix=".tmp", dir=preview_dir)
            os.close(fd)
            try:
                Image.fromarray(preview).save(temporary, format="PNG", optimize=True)
                os.replace(temporary, preview_path)
            except BaseException:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass
                raise
            preview_paths[view_name] = f"previews/{preview_path.name}"
        queue.append({"blind_id": blind_id, "candidate_id": candidate_id, "previews": preview_paths})
    queue_path = output_dir / "queue.json"
    _atomic_text(queue_path, json.dumps(queue, indent=2) + "\n")
    html_path = output_dir / "index.html"
    _atomic_text(html_path, _html(queue, config["response_options"], config["experiment_id"]))
    order_hash = hashlib.sha256("\n".join(item["candidate_id"] for item in queue).encode()).hexdigest()
    report = {
        "experiment_id": config["experiment_id"], "track": config["track"], "regime": "DEV",
        "geometry_tier": "G2", "surface_id": package["surface_id"], "status": "awaiting_human_review",
        "candidate_count": len(queue), "seed": config["seed"], "blinded_order_sha256": order_hash,
        "response_options": config["response_options"], "rank_and_score_visible": False,
        "local_html": str(html_path.relative_to(root)).replace("\\", "/"),
        "local_queue": str(queue_path.relative_to(root)).replace("\\", "/"),
        "preview_publication_status": "local_ignored", "label_inputs_used": False,
        "ui_version": 2, "preview_views": ["raw", "enhanced", "mask", "overlay"],
        "validation_files_accessed": 0,
    }
    _atomic_json(root / config["outputs"]["report_json"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
