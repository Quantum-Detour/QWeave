"""Generate dynamic interactive HTML visual reports for QWeave execution runs."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from importlib.resources import files
import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .processors import PROCESSOR_CONFIGS, get_processor


PROCESSOR_LABELS = {
    "five_node_multipath": "Five-node Multipath (5Q)",
    "five_node": "Five-node Tree (5Q)",
    "ibm_heavy_hex": "IBM Sherbrooke Heavy-Hex (127Q)",
    "hyperbolic_inspired": "Hyperbolic {7,3} Lattice (85Q)",
}

PROCESSOR_DESCRIPTIONS = {
    "five_node_multipath": "5-qubit cycle topology with alternate routing paths. Output Ports: Qubit 0 (Port R, green) and Qubit 4 (Port D, orange) separated by 2 hops.",
    "five_node": "5-qubit branching-tree layout. Output Ports: Qubit 0 (Port R, green) and Qubit 4 (Port D, orange).",
    "ibm_heavy_hex": "127-qubit IBM Eagle heavy-hexagonal architecture (FakeSherbrooke). Output Ports: Qubit 0 (Port R, green) and Qubit 15 (Port D, orange) across 6 hardware hops.",
    "hyperbolic_inspired": "85-qubit Poincaré disk heptagonal hyperbolic tiling {7,3} with interior degree 7. Output Ports: Qubit 5 (Port R, green) and Qubit 31 (Port D, orange) across the 6-hop graph diameter.",
}

ALGORITHM_LABELS = {
    "shortest_path": "A: Shortest path",
    "sabre": "B: SABRE",
    "noise_aware": "C: Noise-aware",
    "noise_aware_mc": "C-MC: Sim-assisted",
    "qmrp": "D: QMRP",
}

ALGORITHM_COLORS = {
    "shortest_path": "#3b82f6",     # Blue
    "sabre": "#6366f1",             # Indigo
    "noise_aware": "#8b5cf6",       # Purple
    "noise_aware_mc": "#a855f7",    # Light Purple
    "qmrp": "#059669",              # Emerald Green
}


def _get_hyperbolic_centers() -> dict[int, tuple[float, float]] | None:
    """Load precomputed Poincaré disk coordinates for hyperbolic cell centers."""
    try:
        raw = files("qweave").joinpath("data/hyperbolic_7_3_cells.json").read_bytes()
        data = json.loads(raw)
        centers = data.get("poincare_cell_centers", [])
        return {i: (c[0], c[1]) for i, c in enumerate(centers)}
    except Exception:
        return None


def build_processor_figure(name: str, processor=None, ports: tuple[int, int] | None = None) -> go.Figure:
    """Generate an interactive NetworkX + Plotly layout for a processor coupling graph.

    Gives ample space and proper aspect ratio for each processor architecture.
    """
    if processor is None:
        processor = get_processor(name)
    graph = processor.graph()

    if ports is None:
        ports = processor.output_ports
    r, d = ports

    # Determine node positions and axis bounds
    xaxis_kwargs: dict[str, Any] = dict(showgrid=False, zeroline=False, showticklabels=False)
    yaxis_kwargs: dict[str, Any] = dict(showgrid=False, zeroline=False, showticklabels=False)

    if name == "hyperbolic_inspired":
        poincare_pos = _get_hyperbolic_centers()
        if poincare_pos and len(poincare_pos) == processor.num_qubits:
            pos = poincare_pos
        else:
            pos = nx.spring_layout(graph, seed=42, k=0.2, iterations=60)
        xaxis_kwargs.update(dict(range=[-1.18, 1.18]))
        yaxis_kwargs.update(dict(range=[-1.18, 1.18], scaleanchor="x", scaleratio=1))
        fig_height = 540
    elif name == "five_node_multipath":
        # Symmetric circular layout centered at origin
        pos = nx.circular_layout(graph)
        xaxis_kwargs.update(dict(range=[-1.35, 1.35]))
        yaxis_kwargs.update(dict(range=[-1.35, 1.35], scaleanchor="x", scaleratio=1))
        fig_height = 460
    elif name == "five_node":
        pos = nx.spring_layout(graph, seed=42)
        xaxis_kwargs.update(dict(range=[-1.35, 1.35]))
        yaxis_kwargs.update(dict(range=[-1.35, 1.35], scaleanchor="x", scaleratio=1))
        fig_height = 460
    elif name == "ibm_heavy_hex":
        pos = nx.spring_layout(graph, seed=42, k=0.15, iterations=80)
        fig_height = 520
    else:
        pos = nx.spring_layout(graph, seed=42)
        fig_height = 480

    # Edge traces
    edge_x = []
    edge_y = []
    for u, v in graph.edges():
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.4, color="#cbd5e1"),
        hoverinfo="none",
        mode="lines",
        name="Coupling Edges",
    )

    # Node traces categorized by role
    node_x = []
    node_y = []
    node_colors = []
    node_text = []
    node_sizes = []
    marker_labels = []

    for node in graph.nodes():
        if node not in pos:
            continue
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        if node == r:
            node_colors.append("#10b981")  # Green for Reference Port R
            node_text.append(f"Qubit {node} (Port R: Reference)")
            node_sizes.append(26)
            marker_labels.append(str(node))
        elif node == d:
            node_colors.append("#f97316")  # Orange for Target Port D
            node_text.append(f"Qubit {node} (Port D: Target)")
            node_sizes.append(26)
            marker_labels.append(str(node))
        else:
            node_colors.append("#64748b")  # Slate gray for regular sites
            node_text.append(f"Qubit {node}")
            if processor.num_qubits <= 5:
                node_sizes.append(24)
                marker_labels.append(str(node))
            else:
                node_sizes.append(10)
                marker_labels.append("")

    has_text = any(bool(label) for label in marker_labels)
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text" if has_text else "markers",
        hoverinfo="text",
        text=marker_labels if has_text else None,
        textposition="middle center",
        textfont=dict(color="#ffffff", size=12, family="sans-serif"),
        hovertext=node_text,
        marker=dict(
            color=node_colors,
            size=node_sizes,
            line=dict(width=1.8, color="#0f172a"),
        ),
        name="Qubits",
    )

    title_label = PROCESSOR_LABELS.get(name, name.replace("_", " ").title())
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f"<b>{title_label}</b> ({processor.num_qubits} Qubits, Output Ports: {r} & {d})",
                font=dict(size=16, color="#0f172a"),
                x=0.02,
                y=0.96,
            ),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=30, l=30, r=30, t=55),
            xaxis=xaxis_kwargs,
            yaxis=yaxis_kwargs,
            plot_bgcolor="#f8fafc",
            paper_bgcolor="#ffffff",
            height=fig_height,
        ),
    )
    return fig


def build_fidelity_comparison_figure(summary_rows: list[dict[str, Any]], noise: str = "backend") -> go.Figure:
    """Build grouped bar chart comparing measured fidelity with 95% error bounds dynamically."""
    proc_keys = []
    for r in summary_rows:
        if r["processor"] not in proc_keys:
            proc_keys.append(r["processor"])
    proc_labels = [PROCESSOR_LABELS.get(p, p) for p in proc_keys]

    algo_keys = []
    for r in summary_rows:
        if r["algorithm"] not in algo_keys:
            algo_keys.append(r["algorithm"])

    index = {(r["processor"], r["algorithm"]): r for r in summary_rows}
    fig = go.Figure()

    for algo in algo_keys:
        algo_label = ALGORITHM_LABELS.get(algo, algo)
        color = ALGORITHM_COLORS.get(algo, "#64748b")

        y_vals = []
        err_plus = []
        err_minus = []
        text_labels = []
        hover_texts = []

        for proc in proc_keys:
            row = index.get((proc, algo))
            if row is not None:
                val = row.get("noisy_fidelity")
                if val is None or noise != "backend":
                    val = row.get("fidelity")
                if val is None:
                    val = row.get("noiseless_fidelity")

                if val is not None:
                    y_vals.append(val)
                    text_labels.append(f"{val:.4f}")
                    interval = row.get("fidelity_interval") or row.get("noisy_interval")
                    if interval:
                        low, high = interval
                        err_minus.append(max(0.0, val - low))
                        err_plus.append(max(0.0, high - val))
                        hover_texts.append(
                            f"<b>{algo_label}</b><br>"
                            f"Processor: {PROCESSOR_LABELS.get(proc, proc)}<br>"
                            f"Fidelity: {val:.4f}<br>"
                            f"95% CI: [{low:.4f}, {high:.4f}]"
                        )
                    else:
                        err_minus.append(0.0)
                        err_plus.append(0.0)
                        hover_texts.append(f"<b>{algo_label}</b><br>Fidelity: {val:.4f}")
                else:
                    y_vals.append(0.0)
                    text_labels.append("N/A")
                    err_minus.append(0.0)
                    err_plus.append(0.0)
                    hover_texts.append(f"<b>{algo_label}</b>: N/A")
            else:
                y_vals.append(None)
                text_labels.append("")
                err_minus.append(0.0)
                err_plus.append(0.0)
                hover_texts.append("")

        fig.add_trace(go.Bar(
            name=algo_label,
            x=proc_labels,
            y=y_vals,
            error_y=dict(
                type="data",
                array=err_plus,
                arrayminus=err_minus,
                visible=any(e > 0 for e in err_plus),
            ),
            marker_color=color,
            text=text_labels,
            textposition="auto",
            hovertext=hover_texts,
            hoverinfo="text",
        ))

    fig.update_layout(
        title="<b>Measured Bell State Fidelity Across Architectures</b> (with 95% Confidence Intervals)",
        barmode="group",
        yaxis=dict(title="Bell State Fidelity F(Φ+)", range=[0.60, 1.02], gridcolor="#e2e8f0"),
        xaxis=dict(title="Hardware Processor Architecture"),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=440,
        margin=dict(t=80, b=40, l=50, r=20),
    )
    return fig


def build_overhead_comparison_figure(summary_rows: list[dict[str, Any]]) -> go.Figure:
    """Build overhead charts comparing Native 2-Qubit Gate counts and Depth dynamically."""
    proc_keys = []
    for r in summary_rows:
        if r["processor"] not in proc_keys:
            proc_keys.append(r["processor"])
    proc_labels = [PROCESSOR_LABELS.get(p, p) for p in proc_keys]

    algo_keys = []
    for r in summary_rows:
        if r["algorithm"] not in algo_keys:
            algo_keys.append(r["algorithm"])

    index = {(r["processor"], r["algorithm"]): r for r in summary_rows}

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("<b>Native Two-Qubit Gates (ZZ Circuit)</b>", "<b>Circuit Depth (ZZ Circuit)</b>"),
    )

    for algo in algo_keys:
        algo_label = ALGORITHM_LABELS.get(algo, algo)
        color = ALGORITHM_COLORS.get(algo, "#64748b")
        gates = []
        depths = []
        for proc in proc_keys:
            row = index.get((proc, algo))
            if row is not None:
                gates.append(row.get("native_two_qubit_gates", 0))
                depths.append(row.get("depth", 0))
            else:
                gates.append(None)
                depths.append(None)

        fig.add_trace(
            go.Bar(name=algo_label, x=proc_labels, y=gates, marker_color=color, text=gates, textposition="auto"),
            row=1, col=1,
        )
        fig.add_trace(
            go.Bar(name=algo_label, x=proc_labels, y=depths, marker_color=color, text=depths, textposition="auto", showlegend=False),
            row=1, col=2,
        )

    fig.update_layout(
        barmode="group",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        height=400,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    fig.update_yaxes(gridcolor="#e2e8f0")
    return fig


def generate_html_report(
    summary_rows: list[dict[str, Any]],
    output_path: Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Generate a self-contained interactive HTML report using actual execution results."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if metadata is None:
        metadata = {}

    # Discover unique processors from the run
    proc_keys = []
    for r in summary_rows:
        if r["processor"] not in proc_keys:
            proc_keys.append(r["processor"])

    # Build processor network figures (each given spacious full-width card, plotted one after the other)
    proc_cards_html = []
    for i, name in enumerate(proc_keys):
        try:
            fig = build_processor_figure(name)
            html = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn" if i == 0 else False,
                config={"displayModeBar": False, "responsive": True},
            )
            desc = PROCESSOR_DESCRIPTIONS.get(name, "")
            proc_cards_html.append(
                f'<div class="topology-card">\n'
                f'    <p class="topology-desc">{desc}</p>\n'
                f'    {html}\n'
                f'</div>'
            )
        except Exception as exc:
            proc_cards_html.append(f'<div class="topology-card"><p>Could not render graph for {name}: {exc}</p></div>')

    # Build benchmark comparison figures
    noise_setting = metadata.get("noise", "backend")
    fidelity_fig = build_fidelity_comparison_figure(summary_rows, noise=noise_setting)
    fidelity_fig_html = fidelity_fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if len(proc_cards_html) == 0 else False,
        config={"displayModeBar": False, "responsive": True},
    )
    overhead_fig = build_overhead_comparison_figure(summary_rows)
    overhead_fig_html = overhead_fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": False, "responsive": True},
    )

    # Build dynamic results table rows
    table_rows_html = []
    previous_proc = None

    # Pre-calculate best noisy fidelity per processor
    best_fidelity_by_proc: dict[str, float] = {}
    for r in summary_rows:
        proc = r["processor"]
        nf = r.get("noisy_fidelity")
        if nf is not None:
            if proc not in best_fidelity_by_proc or nf > best_fidelity_by_proc[proc]:
                best_fidelity_by_proc[proc] = nf

    # Count rows per processor for HTML rowspan
    row_count_by_proc: dict[str, int] = {}
    for r in summary_rows:
        row_count_by_proc[r["processor"]] = row_count_by_proc.get(r["processor"], 0) + 1

    for r in summary_rows:
        proc = r["processor"]
        is_first_for_proc = (proc != previous_proc)

        proc_label = PROCESSOR_LABELS.get(proc, proc)
        algo_label = ALGORITHM_LABELS.get(r["algorithm"], r["algorithm"])
        ports_str = str(r.get("output_ports", "(?)"))
        num_q = r.get("num_qubits", "?")
        active_q = r.get("active_qubits", "?")
        if isinstance(active_q, int) and isinstance(num_q, int) and num_q > 0:
            usage_str = f"{active_q} / {num_q} ({100*active_q/num_q:.1f}%)"
        else:
            usage_str = f"{active_q} / {num_q}"

        noiseless_val = r.get("noiseless_fidelity")
        noiseless_str = f"{noiseless_val:.4f}" if noiseless_val is not None else "—"

        noisy_val = r.get("noisy_fidelity")
        if noisy_val is not None:
            is_best = abs(noisy_val - best_fidelity_by_proc.get(proc, -1)) < 1e-6
            noisy_formatted = f"<b>{noisy_val:.4f}</b>" if is_best else f"{noisy_val:.4f}"
        else:
            noisy_formatted = "—"

        swaps = r.get("swaps", 0)
        two_q_gates = r.get("native_two_qubit_gates", 0)
        depth = r.get("depth", 0)

        attempted = r.get("attempted", 0)
        accepted = r.get("accepted", 0)
        yield_str = f"{100*accepted/attempted:.2f}%" if attempted > 0 else "100.00%"

        border_style = ' style="border-top: 2px solid #cbd5e1;"' if (is_first_for_proc and previous_proc is not None) else ""
        row_html = f"<tr{border_style}>\n"

        if is_first_for_proc:
            span = row_count_by_proc[proc]
            row_html += f'    <td rowspan="{span}"><b>{proc_label}</b><br><small style="color:#64748b;">{num_q} Sites, Ports {ports_str}</small></td>\n'

        row_html += f"    <td>{algo_label}</td>\n"
        row_html += f'    <td class="num">{noiseless_str}</td>\n'
        row_html += f'    <td class="num">{noisy_formatted}</td>\n'
        row_html += f'    <td class="num">{usage_str}</td>\n'
        row_html += f'    <td class="num">{swaps}</td>\n'
        row_html += f'    <td class="num">{two_q_gates}</td>\n'
        row_html += f'    <td class="num">{depth}</td>\n'
        row_html += f'    <td class="num">{yield_str}</td>\n'
        row_html += "</tr>"

        table_rows_html.append(row_html)
        previous_proc = proc

    table_body = "\n".join(table_rows_html)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    shots_val = metadata.get("shots", 3072)
    seed_val = metadata.get("seed", 42)
    backend_seed_val = metadata.get("backend_seed", 1234)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QWeave: Quantum Routing & QMRP Experimental Report</title>
    <style>
        :root {{
            --primary: #0f172a;
            --accent: #2563eb;
            --success: #059669;
            --warning: #d97706;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #334155;
            --text-heading: #0f172a;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.6;
            margin: 0;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: white;
            padding: 35px 40px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
            margin-bottom: 30px;
        }}
        header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        header p {{
            margin: 0;
            color: #94a3b8;
            font-size: 1.1rem;
        }}
        .badge {{
            display: inline-block;
            background: rgba(37, 99, 235, 0.25);
            color: #93c5fd;
            border: 1px solid rgba(147, 197, 253, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 15px;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 1.35rem;
            color: var(--text-heading);
            border-bottom: 2px solid var(--bg);
            padding-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .topology-stack {{
            display: flex;
            flex-direction: column;
            gap: 24px;
            margin-top: 18px;
        }}
        .topology-card {{
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 18px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}
        .topology-desc {{
            margin: 0 0 12px 0;
            color: #64748b;
            font-size: 0.92rem;
        }}
        .phase-flow {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }}
        .phase-step {{
            background: #f1f5f9;
            border-left: 4px solid var(--accent);
            border-radius: 6px;
            padding: 16px;
        }}
        .phase-step.protected {{
            border-left-color: var(--success);
            background: #ecfdf5;
        }}
        .phase-step h4 {{
            margin: 0 0 8px 0;
            color: var(--text-heading);
            font-size: 0.95rem;
        }}
        .phase-step p {{
            margin: 0;
            font-size: 0.85rem;
            color: #475569;
        }}
        table.results-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
            margin: 15px 0;
        }}
        table.results-table th {{
            background: #f8fafc;
            color: var(--text-heading);
            text-align: left;
            padding: 12px 14px;
            font-weight: 600;
            border-bottom: 2px solid var(--border);
        }}
        table.results-table td {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
        }}
        table.results-table tr:hover td {{
            background-color: #f8fafc;
        }}
        .num {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        .meta-bar {{
            display: flex;
            gap: 20px;
            font-size: 0.85rem;
            color: #64748b;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .meta-bar span {{
            background: #f1f5f9;
            padding: 4px 10px;
            border-radius: 6px;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            color: #64748b;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <h1>QWeave: Visual Routing & QMRP Analysis</h1>
        <p>Qiskit Fall Fest 2026 Challenge: Hyperbolic Futures — quanTA, University of Saskatchewan</p>
        <span class="badge">Deliverables 02 & 03: Live Interactive Figures & Audited Quantitative Results</span>
    </header>

    <div class="meta-bar">
        <span><b>Run Timestamp:</b> {now_str}</span>
        <span><b>Shot Budget:</b> {shots_val} shots / basis</span>
        <span><b>Master Seed:</b> {seed_val}</span>
        <span><b>Backend Seed:</b> {backend_seed_val}</span>
        <span><b>Noise Mode:</b> {noise_setting}</span>
    </div>

    <!-- 1. Processor Coupling Graphs -->
    <div class="card">
        <h2>🌐 1. Processor Coupling Graphs & Designated Ports</h2>
        <p>Green node represents <b>Port R</b> (Stationary Reference). Orange node represents <b>Port D</b> (Entangled Partner Destination). Gray nodes are intermediate routing and ancilla sites.</p>
        <div class="topology-stack">
            {"\n".join(proc_cards_html)}
        </div>
    </div>

    <!-- 2. Circuit Phases & Operation Flow -->
    <div class="card">
        <h2>⚡ 2. Circuit Operation Flow & Execution Phases</h2>
        <p>All methods prepare the Bell state |Φ⁺⟩ from all-zero physical inputs across designated ports. Method D (QMRP) inserts a 2-qubit repetition encoding and extraction block protected by phase barriers:</p>
        
        <div class="phase-flow">
            <div class="phase-step">
                <h4>Phase 1: Local Bell Prep</h4>
                <p>Applies <code>H(R)</code> and <code>CX(R, launch_A)</code> locally on adjacent sites without zero-state prepositioning.</p>
            </div>
            <div class="phase-step protected">
                <h4>Phase 2: Repetition Encoding</h4>
                <p>Encodes traveling qubit across two physical rails using local <code>CX(launch_A, launch_B)</code>.</p>
            </div>
            <div class="phase-step protected">
                <h4>Phase 3: Disjoint Transport</h4>
                <p>Moves the two rails outward along capacity-constrained vertex-disjoint paths discovered via min-cost flow.</p>
            </div>
            <div class="phase-step protected">
                <h4>Phase 4: Decoding & Parity</h4>
                <p>Applies <code>CX(D, S)</code> at destination, extracting pre-decoding Z_a Z_b parity into syndrome qubit S.</p>
            </div>
            <div class="phase-step">
                <h4>Phase 5: Basis Rotation</h4>
                <p>Rotates ports into XX (H), YY (Sdg + H), or ZZ basis, measuring S in Z and postselecting on S=0.</p>
            </div>
        </div>
    </div>

    <!-- 3. Quantitative Comparison Charts -->
    <div class="card">
        <h2>📊 3. Quantitative Comparison Charts (Live Execution Data)</h2>
        <div>{fidelity_fig_html}</div>
        <div style="margin-top: 25px;">{overhead_fig_html}</div>
    </div>

    <!-- 4. Complete Verification Summary Table -->
    <div class="card">
        <h2>📋 4. Complete Verification & Resource Summary</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Processor Family</th>
                    <th>Algorithm</th>
                    <th class="num">Noiseless F</th>
                    <th class="num">Noisy F</th>
                    <th class="num">Physical Qubits Used / Total</th>
                    <th class="num">SWAPs</th>
                    <th class="num">Native 2Q Gates</th>
                    <th class="num">Depth</th>
                    <th class="num">Accepted Yield</th>
                </tr>
            </thead>
            <tbody>
                {table_body}
            </tbody>
        </table>
    </div>

    <footer>
        QWeave Submission • Generated with Qiskit 2.x & Plotly • Qiskit Fall Fest 2026
    </footer>
</div>

</body>
</html>
"""

    output_path.write_text(html_content)
    return output_path
