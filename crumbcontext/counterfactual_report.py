from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from .counterfactual_models import CounterfactualResult


def write_counterfactual_report(result: CounterfactualResult, path: Path) -> None:
    b = result.baseline
    r = result.routed
    status = "PASS" if result.passed else "CHECK FAILED"
    status_class = "pass" if result.passed else "fail"
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CrumbContext counterfactual</title>
<style>
:root{{--bg:#070b13;--panel:#101827;--line:#29344a;--text:#f8fafc;--muted:#94a3b8;--cyan:#22d3ee;--green:#53f2a3;--red:#ff6b7a}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 85% 0,#172554 0,transparent 32%),var(--bg);color:var(--text);font:16px/1.55 Inter,system-ui;padding:42px}}main{{max-width:1180px;margin:auto}}h1{{font-size:54px;line-height:1.05;margin:10px 0}}h2{{margin-top:38px}}.eyebrow{{color:var(--cyan);letter-spacing:.16em;font-weight:700}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}.card{{background:rgba(16,24,39,.94);border:1px solid var(--line);border-radius:18px;padding:22px}}.big{{font-size:40px;font-weight:800}}.muted{{color:var(--muted)}}.pass{{color:var(--green)}}.fail{{color:var(--red)}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;border-bottom:1px solid var(--line);text-align:left}}code,pre{{font-family:ui-monospace,Menlo,monospace}}pre{{white-space:pre-wrap;word-break:break-word;background:#060912;border:1px solid var(--line);border-radius:14px;padding:16px;max-height:360px;overflow:auto}}
</style></head><body><main>
<div class="eyebrow">SAME TASK · TWO PAYLOADS · ONE SCORECARD</div><h1>CrumbContext counterfactual</h1>
<p class="muted">The identical task was executed against the uncompressed baseline and routed context bundle.</p>
<div class="grid"><div class="card"><div class="muted">SELF-CHECK</div><div class="big {status_class}">{status}</div></div><div class="card"><div class="muted">INPUT TOKEN DELTA</div><div class="big">{result.input_token_reduction_percent:.1f}%</div></div><div class="card"><div class="muted">ROUTED EXACT RECALL</div><div class="big">{r.evaluation.exact_recall*100:.1f}%</div></div><div class="card"><div class="muted">RESPONSE SIMILARITY</div><div class="big">{result.response_similarity*100:.1f}%</div></div></div>
<h2>Side-by-side</h2><div class="card"><table><thead><tr><th>Metric</th><th>Baseline</th><th>Routed</th></tr></thead><tbody><tr><td>Input tokens</td><td>{b.response['input_tokens']:,}</td><td>{r.response['input_tokens']:,}</td></tr><tr><td>Output tokens</td><td>{b.response['output_tokens']:,}</td><td>{r.response['output_tokens']:,}</td></tr><tr><td>Total tokens</td><td>{b.response['total_tokens']:,}</td><td>{r.response['total_tokens']:,}</td></tr><tr><td>Latency</td><td>{b.response['latency_ms']:.3f} ms</td><td>{r.response['latency_ms']:.3f} ms</td></tr><tr><td>Exact recall</td><td>{b.evaluation.exact_found}/{b.evaluation.exact_expected}</td><td>{r.evaluation.exact_found}/{r.evaluation.exact_expected}</td></tr><tr><td>Task complete</td><td>{str(b.evaluation.task_complete).lower()}</td><td>{str(r.evaluation.task_complete).lower()}</td></tr></tbody></table></div>
<h2>Integrity</h2><div class="grid"><div class="card"><div class="muted">TASK SHA-256</div><code>{result.task_sha256}</code></div><div class="card"><div class="muted">SOURCE SHA-256</div><code>{result.source_sha256}</code></div><div class="card"><div class="muted">BASELINE REQUEST</div><code>{b.request_sha256}</code></div><div class="card"><div class="muted">ROUTED REQUEST</div><code>{r.request_sha256}</code></div></div>
<h2>Responses</h2><div class="grid"><div class="card"><pre>{escape(str(b.response['text']))}</pre></div><div class="card"><pre>{escape(str(r.response['text']))}</pre></div></div><h2>Important limitation</h2><div class="card"><p>{escape(result.disclaimer)}</p></div>
</main></body></html>"""
    path.write_text(html, encoding="utf-8")


def write_counterfactual_card(result: CounterfactualResult, path: Path) -> None:
    status = "PASS" if result.passed else "CHECK FAILED"
    status_fill = "#53f2a3" if result.passed else "#ff6b7a"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><defs><linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#070b13"/><stop offset="1" stop-color="#172554"/></linearGradient><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#8b5cf6"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs><rect width="1200" height="630" rx="34" fill="url(#bg)"/><circle cx="1080" cy="80" r="220" fill="#8b5cf6" opacity=".12"/><text x="72" y="88" fill="#94a3b8" font-family="Inter,Arial" font-size="23" letter-spacing="4">CRUMBCONTEXT COUNTERFACTUAL</text><text x="72" y="166" fill="#fff" font-family="Inter,Arial" font-size="58" font-weight="800">Same task. Less context.</text><text x="72" y="214" fill="#aab6cc" font-family="Inter,Arial" font-size="25">Baseline and routed payloads compared under one evaluation contract.</text><g transform="translate(72 276)"><rect width="315" height="170" rx="22" fill="#101827" stroke="#29344a"/><text x="28" y="46" fill="#8fa0ba" font-family="Inter,Arial" font-size="18">INPUT TOKEN DELTA</text><text x="28" y="120" fill="url(#g)" font-family="Inter,Arial" font-size="64" font-weight="800">{result.input_token_reduction_percent:.1f}%</text></g><g transform="translate(414 276)"><rect width="315" height="170" rx="22" fill="#101827" stroke="#29344a"/><text x="28" y="46" fill="#8fa0ba" font-family="Inter,Arial" font-size="18">EXACT RECALL</text><text x="28" y="120" fill="#fff" font-family="Inter,Arial" font-size="64" font-weight="800">{result.routed.evaluation.exact_recall*100:.0f}%</text></g><g transform="translate(756 276)"><rect width="372" height="170" rx="22" fill="#101827" stroke="#29344a"/><text x="28" y="46" fill="#8fa0ba" font-family="Inter,Arial" font-size="18">SELF-CHECK</text><text x="28" y="120" fill="{status_fill}" font-family="Inter,Arial" font-size="56" font-weight="800">{status}</text></g><text x="72" y="526" fill="#8fa0ba" font-family="ui-monospace,Menlo" font-size="20">crumbcontext counterfactual --provider mock --out proof</text><text x="72" y="572" fill="#65738b" font-family="Inter,Arial" font-size="17">Mock usage is simulated, not provider billed · github.com/XioAISolutions/CrumbContext</text></svg>"""
    path.write_text(svg, encoding="utf-8")
