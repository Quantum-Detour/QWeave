"""Build a polished 12-slide 16:9 PowerPoint presentation deck for QWeave.

Order & Structure:
1. Title & Team (Aaron, Calvin, Bhaskar - quanTA USask)
2. Problem Statement: The NISQ Routing Bottleneck
3. Setup: Simulation Rigor & Qiskit APIs (FakeSherbrooke, GenericBackendV2, Statevector proof)
4. Approach: Quantum Multipath Routing Protection (QMRP) & Accessible Math
5. Processor 1 & Circuit: 2016 Five-Node Reference (Cycle Topology, Ports 0 & 4)
6. Processor 2 & Circuit: IBM Heavy-Hex Architecture (127 Qubits, Ports 0 & 14)
7. Processor 3 & Circuit: Hyperbolic Lattice {7,3} (85 Qubits, Ports 0 & 84)
8. Routing Baselines: Why Multiple Compilers (Shortest Path, SABRE, Noise-Aware, Simulated C-MC)
9. Quantitative Results: Fidelity, Hardware Overhead & Physical Qubit Accounting
10. Scientific Interpretation: What QMRP Detects vs. What It Misses
11. System Recommendation: Selective, Geometry-Aware Routing Policy (Deliverable 05)
12. Future Horizons & Academic References

Calibrated strictly to 5-10 minutes (~8.5 minutes total).
Huge dedicated placeholders for all three processor circuits and result charts.
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE


# --- Color Palette ---
COLOR_BG = RGBColor(248, 250, 252)        # #F8FAFC (Slate 50)
COLOR_WHITE = RGBColor(255, 255, 255)     # #FFFFFF
COLOR_NAVY = RGBColor(15, 23, 42)          # #0F172A (Slate 900)
COLOR_TEXT_MUTED = RGBColor(71, 85, 105)  # #475569 (Slate 600)
COLOR_BLUE = RGBColor(37, 99, 235)         # #2563EB (Blue 600)
COLOR_BLUE_LIGHT = RGBColor(239, 246, 255)# #EFF6FF (Blue 50)
COLOR_BLUE_BORDER = RGBColor(191, 219, 254)# #BFDBFE (Blue 200)
COLOR_PURPLE = RGBColor(124, 58, 237)      # #7C3AED (Violet 600)
COLOR_TEAL = RGBColor(13, 148, 136)        # #0D9488 (Teal 600)
COLOR_AMBER = RGBColor(217, 119, 6)       # #D97706 (Amber 600)
COLOR_CARD_BORDER = RGBColor(226, 232, 240) # #E2E8F0 (Slate 200)


def create_deck(output_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide, color=COLOR_BG):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, category: str, title: str, subtitle: str = ""):
        # Category Badge
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.32))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.name = "Calibri"
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_BLUE

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.68), Inches(11.7), Inches(0.65))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = "Calibri"
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_NAVY

        if subtitle:
            p_sub = tf_title.add_paragraph()
            p_sub.text = subtitle
            p_sub.font.name = "Calibri"
            p_sub.font.size = Pt(12)
            p_sub.font.color.rgb = COLOR_TEXT_MUTED

    def add_card(slide, left, top, width, height, bg_color=COLOR_WHITE, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        return card

    def add_large_image_placeholder(slide, left, top, width, height, title: str, hint: str):
        ph = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        ph.fill.solid()
        ph.fill.fore_color.rgb = COLOR_BLUE_LIGHT
        ph.line.color.rgb = COLOR_BLUE_BORDER
        ph.line.width = Pt(1.5)
        tf = ph.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.25)
        p1 = tf.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        p1.text = "🖼️  LARGE SCREENSHOT PLACEHOLDER"
        p1.font.name = "Calibri"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_BLUE

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.text = title
        p2.font.name = "Calibri"
        p2.font.size = Pt(15)
        p2.font.bold = True
        p2.font.color.rgb = COLOR_NAVY

        p3 = tf.add_paragraph()
        p3.alignment = PP_ALIGN.CENTER
        p3.text = f"\n{hint}"
        p3.font.name = "Calibri"
        p3.font.size = Pt(11)
        p3.font.color.rgb = COLOR_TEXT_MUTED
        return ph

    def set_notes(slide, timing: str, script: str, subtext: str, questions: str):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = (
            f"⏱️ TARGET TIME: {timing}\n"
            "=====================================================\n"
            "🎤 WHAT TO SAY (Speaker Script - Read aloud):\n"
            "=====================================================\n"
            f"{script}\n\n"
            "=====================================================\n"
            "💡 SUBTEXT FOR YOUR UNDERSTANDING (Do NOT read aloud):\n"
            "=====================================================\n"
            f"{subtext}\n\n"
            "=====================================================\n"
            "❓ ANTICIPATED JUDGE QUESTIONS & QUICK REPLIES:\n"
            "=====================================================\n"
            f"{questions}"
        )

    # =========================================================================
    # SLIDE 1: Title & Team (0:00 - 0:30)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, COLOR_WHITE)

    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.2), Inches(0.12), Inches(4.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_BLUE
    bar.line.fill.background()

    tbox = s1.shapes.add_textbox(Inches(1.2), Inches(1.2), Inches(11.0), Inches(4.5))
    tf1 = tbox.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "QISKIT FALL FEST 2026 CHALLENGE: HYPERBOLIC FUTURES"
    p.font.name = "Calibri"; p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_BLUE

    p = tf1.add_paragraph()
    p.text = "QWeave: Geometry-Aware Quantum Routing\n& Parity Postselection"
    p.font.name = "Calibri"; p.font.size = Pt(36); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    p = tf1.add_paragraph()
    p.text = "\nAuditing Quantum Multipath Routing Protection (QMRP) across 2016, Heavy-Hex & Hyperbolic Lattices"
    p.font.name = "Calibri"; p.font.size = Pt(16); p.font.color.rgb = COLOR_TEXT_MUTED

    p = tf1.add_paragraph()
    p.text = "\nTeam Members: Aaron Huang  •  Calvin Cheng  •  Bhaskar Mahajan (bhaskarmahajan98@gmail.com)\nHost: quanTA, University of Saskatchewan (Prof. Steven Rayan)"
    p.font.name = "Calibri"; p.font.size = Pt(13); p.font.color.rgb = COLOR_NAVY

    set_notes(
        s1,
        timing="0:00 – 0:30 (30 seconds)",
        script=(
            "Hello everyone. Today we are presenting QWeave, our submission for the Qiskit Fall Fest 2026 Hyperbolic "
            "Futures challenge, hosted by quanTA at the University of Saskatchewan. "
            "Our team consists of Aaron Huang, Calvin Cheng, and myself, Bhaskar Mahajan. "
            "In near-term quantum processors, establishing long-distance entanglement requires routing qubits across noisy hardware. "
            "Our project investigates whether encoding quantum information across multiple disjoint hardware paths—known as QMRP—"
            "and taking advantage of hyperbolic chip geometry can protect Bell state fidelity against industry-standard compilers like Qiskit's SABRE."
        ),
        subtext="Keep opening confident, crisp, and under 30 seconds.",
        questions=(
            "Q: What is the main objective of your submission?\n"
            "A: To evaluate whether Quantum Multipath Routing Protection (QMRP) genuinely improves end-to-end Bell state "
            "fidelity when tested against industry-standard compilers on planar and hyperbolic lattices."
        )
    )

    # =========================================================================
    # SLIDE 2: Problem Statement & Motivation (0:30 - 1:15)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "01 Challenge Motivation", "The NISQ Routing Bottleneck: Noise vs. Connectivity",
               "Why long-distance entanglement distribution is the fundamental scaling bottleneck in quantum hardware.")

    add_card(s2, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
    tb = s2.shapes.add_textbox(Inches(1.1), Inches(1.7), Inches(5.0), Inches(5.0))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "The Physical Routing Bottleneck"
    p.font.size = Pt(18); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    items = [
        ("Limited Physical Connectivity: ", "Qubits only interact with immediate physical neighbors. Entangling distant ports requires cascades of intermediate SWAP gates."),
        ("Compounding Gate Noise: ", "Every SWAP requires 3 native CNOT gates. A 4-hop route demands 12 physical two-qubit operations, accumulating severe depolarizing and dephasing noise."),
        ("The Scaling Trap: ", "As chip sizes scale to hundreds of qubits, routing noise rapidly destroys output entanglement.")
    ]
    for title, desc in items:
        p = tf.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12); p2.font.color.rgb = COLOR_TEXT_MUTED

    add_card(s2, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.4))
    tb_r = s2.shapes.add_textbox(Inches(7.1), Inches(1.7), Inches(5.1), Inches(5.0))
    tf_r = tb_r.text_frame; tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "The Core Research Question"
    p.font.size = Pt(18); p.font.bold = True; p.font.color.rgb = COLOR_BLUE

    r_items = [
        ("Quantum Multipath Routing (QMRP): ", "Can encoding a traveling qubit across TWO parallel disjoint paths and checking parity at the destination protect fidelity?"),
        ("Hyperbolic Geometry: ", "Do hyperbolic lattices—with exponential boundary growth and high connectivity—provide the ideal architecture for multipath routing?"),
        ("The Trade-off Dilemma: ", "Does parity postselection improve fidelity enough to justify the extra SWAP gates and discarded shot yield?")
    ]
    for title, desc in r_items:
        p = tf_r.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf_r.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s2,
        timing="0:30 – 1:15 (45 seconds)",
        script=(
            "On physical quantum chips, qubits can only interact with adjacent neighbors. If we want to entangle two distant ports, "
            "the compiler must insert SWAP gates to move the quantum state across intermediate sites. "
            "However, every SWAP requires three physical CNOT gates. On near-term hardware with 1% gate error rates, routing a qubit "
            "just 4 or 5 hops away causes severe fidelity decay. "
            "The challenge explores a compelling idea: what if we split the traveling qubit across two parallel, disjoint paths using a "
            "two-qubit repetition code, and discard shots whenever an error is detected at the destination? "
            "And can novel hyperbolic processor geometries make this multipath approach practical?"
        ),
        subtext="Intuition: SWAPs are noisy because each takes 3 CNOTs. QMRP sends 2 copies down separate paths to catch bit-flips.",
        questions=(
            "Q: Why are SWAP gates such a problem in NISQ?\n"
            "A: SWAPs aren't physical hardware primitives; each SWAP decomposes into 3 CNOT gates, tripling two-qubit gate errors along the path."
        )
    )

    # =========================================================================
    # SLIDE 3: Experimental Setup & Qiskit APIs (1:15 - 2:00)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "02 Experimental Architecture", "Simulation Rigor & Extensive Qiskit API Integration",
               "Deliverable 01: Executing on Qiskit Aer simulators under reproducible, seeded physical noise models.")

    cards_data = [
        ("Qiskit Simulation Engine", [
            ("Local Aer Emulation: ", "Executed on local Qiskit Aer simulators (`AerSimulator`) to eliminate cloud queue latency and drift."),
            ("Fixed Seed Control: ", "Master simulation seed (`42`) and backend seed (`1234`) guarantee 100% deterministic reproducibility."),
            ("Locked Dependencies: ", "Pinned environment managed with Python 3.12+ and `uv`.")
        ]),
        ("Hardware Noise Models", [
            ("IBM FakeSherbrooke: ", "127-qubit heavy-hex backend snapshot with real calibration error profiles (T1, T2, readout error)."),
            ("GenericBackendV2: ", "Synthetic seeded calibration backends for custom five-node and hyperbolic graphs."),
            ("Native Gate Basis: ", "Strict compilation to superconducting basis: `rz`, `sx`, `cx`.")
        ]),
        ("Exact State Verification", [
            ("Zero-Tolerance Audit: ", "Before running noisy sampling, every circuit was verified via exact statevector simulation (`bell_fidelity`)."),
            ("Ideal Proof: ", "All circuits achieve exactly 1.000000000000 ideal fidelity, proving algorithmic correctness."),
            ("PassManager Level 3: ", "Used `generate_preset_pass_manager` with phase-preserving barrier boundaries.")
        ])
    ]

    for i, (title, items) in enumerate(cards_data):
        left = Inches(0.8 + i * 3.95)
        add_card(s3, left, Inches(1.5), Inches(3.8), Inches(5.4))
        tb = s3.shapes.add_textbox(left + Inches(0.25), Inches(1.7), Inches(3.3), Inches(4.9))
        tf = tb.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

        for item_title, desc in items:
            p = tf.add_paragraph()
            p.text = f"\n• {item_title}"
            p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = COLOR_BLUE
            p2 = tf.add_paragraph()
            p2.text = desc
            p2.font.size = Pt(11); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s3,
        timing="1:15 – 2:00 (45 seconds)",
        script=(
            "To evaluate this question systematically, we built a fully reproducible benchmark suite powered by Qiskit. "
            "We used Qiskit Aer with realistic calibration noise models, including IBM's 127-qubit FakeSherbrooke "
            "and seeded GenericBackendV2 instances. "
            "All circuits were compiled to superconducting native gates—Rz, √X, and CX—using Qiskit's PassManager at optimization level 3. "
            "Crucially, before executing any noisy shot measurements, every compiled circuit underwent an exact mathematical statevector audit. "
            "All circuits achieved an exact ideal Bell fidelity of 1.000000, confirming zero compilation bugs before introducing noise."
        ),
        subtext="Fulfills Deliverable 01. Emphasize that statevector verification proved 100% ideal correctness before noise was added.",
        questions=(
            "Q: Did you run on real hardware?\n"
            "A: No, we ran on realistic local Aer simulators as recommended by the challenge guidelines to ensure controlled, reproducible comparisons without queue drift."
        )
    )

    # =========================================================================
    # SLIDE 4: Our Approach: QMRP & Accessible Math (2:00 - 2:45)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "03 Methodology & Protection", "Our Approach: Quantum Multipath Routing Protection (QMRP)",
               "Encoding Bell states across two physical rails, checking parity at destination, and optimizing movement.")

    # Left Card: Step-by-Step Mechanism
    add_card(s4, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
    tb = s4.shapes.add_textbox(Inches(1.1), Inches(1.7), Inches(5.0), Inches(5.0))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "How QMRP Operates"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    qmrp_steps = [
        ("1. Bell Pair Generation: ", "Create entanglement at Port A: H on port A, CX to local launch qubit."),
        ("2. Two-Rail Repetition Encoding: ", "A local CX copies the traveling state onto two physical rails: |0⟩ → |00⟩ and |1⟩ → |11⟩."),
        ("3. Disjoint Dual-Rail Transport: ", "Rail 1 and Rail 2 travel along completely separate hardware paths."),
        ("4. Decoding & Parity Postselection: ", "Destination CX decodes to Port B and flips a syndrome ancilla (S) to |1⟩ if rails mismatch."),
        ("5. Shot Filtering: ", "Measure syndrome S in Z basis. If S=0, accept shot. If S=1 (error detected), discard shot!")
    ]
    for title, desc in qmrp_steps:
        p = tf.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10); p2.font.color.rgb = COLOR_TEXT_MUTED

    # Right Card: The Math & Zero-Input Optimization
    add_card(s4, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.4))
    tb_r = s4.shapes.add_textbox(Inches(7.1), Inches(1.7), Inches(5.1), Inches(5.0))
    tf_r = tb_r.text_frame; tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "Accessible Math & Optimization"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = COLOR_PURPLE

    math_opt = [
        ("Bell State Fidelity Formula:",
         "F(Φ⁺) = (1 + ⟨XX⟩ - ⟨YY⟩ + ⟨ZZ⟩) / 4\n"
         "Measured across 3 complementary Pauli bases (XX, YY, ZZ).\n"
         "Ideal: (1 + 1 - (-1) + 1)/4 = 1.0 (100% fidelity). Physical noise pushes expectation values toward 0, reducing fidelity."),
        ("How Parity Traps Bit-Flips:",
         "Both rails start in identical states (|00⟩ + |11⟩). If an X bit-flip occurs on Rail 1 during transit, the state becomes |10⟩ + |01⟩.\n"
         "The decoder detects this mismatch, flips syndrome S to |1⟩, and the shot is rejected."),
        ("Zero-Input Movement Optimization:",
         "Standard SWAP = 3 CNOTs. But routing ancillas start clean in |0⟩!\n"
         "Moving into an empty |0⟩ wire requires only 2 CNOTs, cutting movement gate overhead by 33% to 50%!")
    ]
    for title, desc in math_opt:
        p = tf_r.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf_r.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s4,
        timing="2:00 – 2:45 (45 seconds)",
        script=(
            "Here is our approach: Quantum Multipath Routing Protection. "
            "Instead of sending a single qubit down one noisy line of SWAPs, we encode it across two physical rails using a CNOT gate. "
            "Both rails travel along completely separate hardware paths to Port B. "
            "At the destination, a decoding CNOT checks if they still match. If a bit-flip error hit either rail during transit, "
            "the syndrome ancilla flips to 1, and we discard that shot. "
            "We measure fidelity across three bases—XX, YY, and ZZ—using the standard Bell formula: (1 + XX - YY + ZZ)/4. "
            "Crucially, we also optimized compiler movement: because empty routing ancillas start in clean zero states, "
            "moving a qubit into an empty wire only takes two CNOTs instead of three, cutting routing noise by up to 50%."
        ),
        subtext="Intuition: F = (1 + XX - YY + ZZ)/4. Ideal = 1.0. Noise pushes numbers toward 0. Parity throws away bit-flip errors.",
        questions=(
            "Q: Can QMRP correct errors or just detect them?\n"
            "A: It detects them. QMRP uses postselection, discarding corrupted shots rather than performing active feedback."
        )
    )

    # =========================================================================
    # SLIDE 5: Processor 1: 2016 Five-Node Reference (2:45 - 3:30)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "04 Hardware Benchmark 1", "Processor 1: 2016 Five-Node Reference (Multipath Cycle)",
               "Deliverable 02: 5-qubit testbed with ports (0, 4) enabling disjoint multipath routing at minimal scale.")

    # Top summary card (11.7" wide x 1.3" high)
    add_card(s5, Inches(0.8), Inches(1.5), Inches(11.7), Inches(1.2))
    tb_top = s5.shapes.add_textbox(Inches(1.0), Inches(1.58), Inches(11.3), Inches(1.0))
    tf_top = tb_top.text_frame; tf_top.word_wrap = True
    p = tf_top.paragraphs[0]
    p.text = "Topology & Circuit Overview: Five-Node Multipath Cycle"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
    p2 = tf_top.add_paragraph()
    p2.text = "• Ports: (0, 4)  |  Chip Capacity: 5 Qubits  |  Connectivity: ((0,1), (1,2), (2,3), (3,4), (4,1))\n" \
              "• Disjoint Paths: Path 1 (0→1→4, length 2) vs. Path 2 (0→1→2→3→4, length 4). Enables multipath benchmarking at minimal scale.\n" \
              "• Execution: Baselines use 1 SWAP (depth 8, 3/5 qubits). QMRP uses 2 SWAPs (depth 11, 5/5 qubits, 98.05% acceptance)."
    p2.font.size = Pt(11); p2.font.color.rgb = COLOR_TEXT_MUTED

    # Bottom HUGE Image Placeholder (11.7" wide x 4.3" high!)
    add_large_image_placeholder(
        s5, Inches(0.8), Inches(2.85), Inches(11.7), Inches(4.2),
        title="Five-Node Coupling Graph & Transpiled Circuit Diagram",
        hint="Insert the Five-Node diagrams here:\n• Left: 5-node cycle topology graph with Ports 0 and 4 highlighted\n• Right: Transpiled native circuit (rz, sx, cx) showing the 4 phases\n(Exported from results/visual_summary.html or Circuit Diag.jpg)"
    )

    set_notes(
        s5,
        timing="2:45 – 3:30 (45 seconds)",
        script=(
            "Our first benchmark processor is the 2016 Five-Node reference. "
            "In the original 2016 tree topology, there is only one acyclic path between ports 0 and 4, making disjoint multipath routing "
            "topologically impossible. To test QMRP at 5-qubit scale, we used a 5-node cycle topology. "
            "This creates two disjoint paths: Path 1 goes 0 to 1 to 4, while Path 2 goes 0 to 1 to 2 to 3 to 4. "
            "As shown in the transpiled circuit below, baselines require just 1 SWAP at depth 8 using 3 physical qubits. "
            "QMRP requires 2 SWAPs at depth 11, utilizing all 5 physical qubits with a 98% acceptance yield."
        ),
        subtext="Fulfills Deliverable 02 for Processor 1. Ample space for both the 5-node graph and its transpiled circuit.",
        questions=(
            "Q: Why did you modify the original 2016 tree graph?\n"
            "A: The original tree has no alternate paths between ports 0 and 4. The cycle topology preserves the 5-qubit scale while enabling two vertex-disjoint routes."
        )
    )

    # =========================================================================
    # SLIDE 6: Processor 2: IBM Heavy-Hex Architecture (3:30 - 4:15)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "05 Hardware Benchmark 2", "Processor 2: IBM Heavy-Hex Architecture (FakeSherbrooke)",
               "Deliverable 02: 127-qubit commercial planar layout with ports (0, 14) modeling realistic hardware bottlenecks.")

    # Top summary card (11.7" wide x 1.3" high)
    add_card(s6, Inches(0.8), Inches(1.5), Inches(11.7), Inches(1.2))
    tb_top = s6.shapes.add_textbox(Inches(1.0), Inches(1.58), Inches(11.3), Inches(1.0))
    tf_top = tb_top.text_frame; tf_top.word_wrap = True
    p = tf_top.paragraphs[0]
    p.text = "Topology & Circuit Overview: IBM 127-Qubit Heavy-Hex"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
    p2 = tf_top.add_paragraph()
    p2.text = "• Ports: (0, 14)  |  Chip Capacity: 127 Qubits  |  Layout: Low average degree (2–3) planar heavy-hex lattice\n" \
              "• Planar Congestion: Narrow corridors force the second rail into wide peripheral detours (8 SWAPs vs. 4 SWAPs for baselines).\n" \
              "• Execution: SABRE achieves depth 30 with 6/127 qubits. QMRP depth balloons to 113 with 8/127 qubits (87.43% acceptance yield)."
    p2.font.size = Pt(11); p2.font.color.rgb = COLOR_TEXT_MUTED

    # Bottom HUGE Image Placeholder (11.7" wide x 4.3" high!)
    add_large_image_placeholder(
        s6, Inches(0.8), Inches(2.85), Inches(11.7), Inches(4.2),
        title="IBM Heavy-Hex Coupling Graph & Transpiled Circuit Diagram",
        hint="Insert the IBM Heavy-Hex diagrams here:\n• Left: 127-qubit Heavy-Hex topology graph with Ports 0 and 14 highlighted\n• Right: Transpiled native circuit showing the dual-rail routing paths\n(Exported from results/visual_summary.html or Circuit Diag.jpg)"
    )

    set_notes(
        s6,
        timing="3:30 – 4:15 (45 seconds)",
        script=(
            "Our second processor is IBM's 127-qubit Heavy-Hex architecture, using calibration data from FakeSherbrooke. "
            "This represents commercial superconducting processors, characterized by low node degree—mostly degree 2 and 3. "
            "Between ports 0 and 14, this low connectivity creates a severe planar bottleneck: forcing two disjoint paths pushes the "
            "second rail far into peripheral qubits, requiring 8 SWAPs instead of 4. "
            "While SABRE optimizes circuit depth down to 30, QMRP's depth balloons to 113, and shot yield drops to 87.4%."
        ),
        subtext="Fulfills Deliverable 02 for Processor 2. Highlights the planar routing bottleneck of IBM Heavy-Hex chips.",
        questions=(
            "Q: Why did QMRP perform poorly on Heavy-Hex?\n"
            "A: The low degree of planar heavy-hex grids forces multipath rails into long peripheral detours, accumulating excess SWAP gate noise."
        )
    )

    # =========================================================================
    # SLIDE 7: Processor 3: Hyperbolic Lattice {7,3} (4:15 - 5:00)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "06 Hardware Benchmark 3", "Processor 3: Hyperbolic Lattice {7,3} (85 Qubits)",
               "Deliverable 02: Regular heptagonal tiling with exponential boundary growth and abundant short disjoint paths.")

    # Top summary card (11.7" wide x 1.3" high)
    add_card(s7, Inches(0.8), Inches(1.5), Inches(11.7), Inches(1.2))
    tb_top = s7.shapes.add_textbox(Inches(1.0), Inches(1.58), Inches(11.3), Inches(1.0))
    tf_top = tb_top.text_frame; tf_top.word_wrap = True
    p = tf_top.paragraphs[0]
    p.text = "Topology & Circuit Overview: Hyperbolic {7,3} Poincaré Disk"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
    p2 = tf_top.add_paragraph()
    p2.text = "• Ports: (0, 84)  |  Chip Capacity: 85 Qubits  |  Generated via HYPERTILING (Mahmoud & Rayan, quanTA USask)\n" \
              "• Negative Curvature Advantage: Area expands exponentially, creating abundant alternative disjoint paths without spatial detours!\n" \
              "• Execution: SABRE achieves 0.9258 fidelity (depth 22, 7/85 qubits). QMRP achieves 0.9208 (depth 93, 9/85 qubits, 90.69% yield)."
    p2.font.size = Pt(11); p2.font.color.rgb = COLOR_TEXT_MUTED

    # Bottom HUGE Image Placeholder (11.7" wide x 4.3" high!)
    add_large_image_placeholder(
        s7, Inches(0.8), Inches(2.85), Inches(11.7), Inches(4.2),
        title="Hyperbolic {7,3} Lattice Graph & Transpiled Circuit Diagram",
        hint="Insert the Hyperbolic {7,3} diagrams here:\n• Left: Heptagonal Poincaré disk tiling with Ports 0 and 84 highlighted\n• Right: Transpiled native circuit showing parallel dual-rail transport\n(Exported from results/visual_summary.html or Circuit Diag.jpg)"
    )

    set_notes(
        s7,
        timing="4:15 – 5:00 (45 seconds)",
        script=(
            "Our third processor is the star of the challenge: an 85-qubit Hyperbolic {7,3} lattice, generated using the "
            "open-source HYPERTILING library developed by Ahmed Adel Mahmoud and Professor Steven Rayan at quanTA. "
            "Hyperbolic geometry has negative spatial curvature: area expands exponentially with radius rather than quadratically. "
            "This creates abundant, short alternative paths between distant ports 0 and 84, making it theoretically ideal for multipath routing. "
            "On this chip, SABRE achieved the highest overall fidelity of 0.9258 at depth 22. QMRP achieved 0.9208 at depth 93 with 90.7% yield."
        ),
        subtext="Fulfills Deliverable 02 for Processor 3. Emphasize that hyperbolic geometry solves spatial congestion.",
        questions=(
            "Q: How was the hyperbolic lattice generated?\n"
            "A: Using the HYPERTILING package, which generates heptagonal tilings in the hyperbolic Poincaré disk, frozen in JSON for reproducibility."
        )
    )

    # =========================================================================
    # SLIDE 8: Routing Algorithms: Why Multiple Baselines (5:00 - 5:45)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "07 Benchmark Methodology", "Deliverable 04: Why We Evaluated Multiple Routing Baselines",
               "Benchmarking against industry-standard lookahead and calibration-adaptive routing to avoid strawman comparisons.")

    algos = [
        ("Method A: Shortest Path", COLOR_BLUE, [
            ("Concept: ", "Dijkstra minimum hop count."),
            ("Strengths: ", "Minimal compile time; topological shortest path."),
            ("Limitation: ", "Blind to hardware calibration noise; may route through bad links.")
        ]),
        ("Method B: SABRE Routing", COLOR_PURPLE, [
            ("Concept: ", "Qiskit's industry-standard SabreSwap with decay lookahead."),
            ("Strengths: ", "Optimizes global circuit depth and SWAP count via lookahead."),
            ("Limitation: ", "Does not explicitly optimize for calibrated gate error rates.")
        ]),
        ("Method C & C-MC: Noise-Aware", COLOR_TEAL, [
            ("C (Static Calibration): ", "ASPLOS '19 (Murali et al.) weights edges by -log(1 - ε_gate)."),
            ("C-MC (Simulation-Assisted): ", "Pre-screens candidate paths using Monte Carlo trial shots on the simulator to discover best route empirically!"),
            ("Key Impact: ", "On Hyperbolic, C-MC avoided bad detours (6 vs 7 SWAPs), lifting fidelity from 0.9028 to 0.9185.")
        ]),
        ("Method D: QMRP Protected", COLOR_AMBER, [
            ("Concept: ", "Two-rail repetition encoding with destination parity postselection."),
            ("Mechanism: ", "Encodes state on 2 rails; discards shots if parity syndrome = 1."),
            ("Limitation: ", "Doubles 2-qubit gate count and discards 9–13% of shots.")
        ])
    ]

    for i, (title, color, items) in enumerate(algos):
        left = Inches(0.8 + i * 2.95)
        add_card(s8, left, Inches(1.5), Inches(2.8), Inches(5.4))
        tb = s8.shapes.add_textbox(left + Inches(0.2), Inches(1.7), Inches(2.4), Inches(4.9))
        tf = tb.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = color

        for item_title, desc in items:
            p = tf.add_paragraph()
            p.text = f"\n• {item_title}"
            p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
            p2 = tf.add_paragraph()
            p2.text = desc
            p2.font.size = Pt(10); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s8,
        timing="5:00 – 5:45 (45 seconds)",
        script=(
            "To evaluate QMRP fairly, we didn't compare it against a single naive baseline. We tested three distinct routing paradigms: "
            "Method A is Shortest Path, minimizing physical hops. "
            "Method B is SABRE, Qiskit's state-of-the-art lookahead router designed to minimize circuit depth. "
            "Method C is Noise-Aware routing, inspired by the ASPLOS 2019 paper by Murali and collaborators, which steers routes "
            "around noisy physical links based on calibration data. "
            "We also built a novel Simulation-Assisted variant, C-MC, which pre-screens candidate paths using noisy trial shots on the simulator. "
            "On the Hyperbolic lattice, C-MC prevented an overly conservative detour, improving fidelity from 0.9028 up to 0.9185! "
            "Benchmarking against multiple competitive baselines is essential: it avoids strawman comparisons and proves whether QMRP offers a genuine advantage."
        ),
        subtext="Fulfills Deliverable 04 requirement: 'Why multiple baselines were evaluated'. Highlight C-MC trial shot pre-screening.",
        questions=(
            "Q: What is the difference between Method C and Method C-MC?\n"
            "A: Method C uses static calibration logs to compute a theoretical path cost, while C-MC uses Monte Carlo trial shots on the simulator to discover the highest-fidelity route empirically."
        )
    )

    # =========================================================================
    # SLIDE 9: Quantitative Results: Fidelity, Cost & Qubits (5:45 - 6:35)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "08 Quantitative Comparison", "Deliverable 03: Comprehensive Benchmark Results Across All Core Cases",
               "Audited under identical experimental controls: 3,072 shots per algorithm, seeds 42 / 1234.")

    # Left Card: Exact Audit Numbers (4.4 inches wide)
    add_card(s9, Inches(0.8), Inches(1.5), Inches(4.4), Inches(5.4))
    tb = s9.shapes.add_textbox(Inches(1.0), Inches(1.65), Inches(4.0), Inches(5.1))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Audit Summary (3,072 Shots)"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    audit_summary = [
        ("Five-Node Multipath:",
         "• Baselines (A, B, C, C-MC): 0.9751 | Depth: 8 | Qubits: 3/5 (60%) | Yield: 100%\n"
         "• QMRP Protected (D): 0.9711 | Depth: 11 | Qubits: 5/5 (100%) | Yield: 98.05%"),
        ("IBM Heavy-Hex (FakeSherbrooke):",
         "• Shortest (A) / Noise-Aware (C, C-MC): 0.7842 | Depth: 56 | Qubits: 6/127 (4.7%)\n"
         "• SABRE (B): 0.7710 | Depth: 30 | Qubits: 6/127 (4.7%) | Yield: 100%\n"
         "• QMRP Protected (D): 0.7709 | Depth: 113 | Qubits: 8/127 (6.3%) | Yield: 87.43%"),
        ("Hyperbolic {7,3} Lattice:",
         "• SABRE (B): 0.9258 (HIGHEST!) | Depth: 22 | Qubits: 7/85 (8.2%)\n"
         "• Shortest Path (A): 0.9219 | Depth: 34 | Qubits: 7/85 (8.2%)\n"
         "• Simulation-Assisted (C-MC): 0.9185 | Depth: 54 | Qubits: 7/85\n"
         "• Static Noise-Aware (C): 0.9028 | Depth: 58 | Qubits: 8/85\n"
         "• QMRP Protected (D): 0.9208 | Depth: 93 | Qubits: 9/85 (10.6%) | Yield: 90.69%")
    ]
    for section_title, desc in audit_summary:
        p = tf.add_paragraph()
        p.text = f"\n{section_title}"
        p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = COLOR_BLUE
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9.5); p2.font.color.rgb = COLOR_NAVY

    # Right: Dedicated HUGE Image Placeholder for Results Charts (7.1" wide x 5.4" high!)
    add_large_image_placeholder(
        s9, Inches(5.4), Inches(1.5), Inches(7.1), Inches(5.4),
        title="Fidelity & Hardware Overhead Visual Charts",
        hint="Insert the Plotly comparison charts here:\n• Top: Measured Bell State Fidelity with 95% Confidence Intervals\n• Bottom: Circuit Depth and Native 2-Qubit Gate Count Comparison\n(Exported from results/visual_summary.html)"
    )

    set_notes(
        s9,
        timing="5:45 – 6:35 (50 seconds)",
        script=(
            "Here are the quantitative results across all core cases audited with 3,072 shots per algorithm: "
            "On the Five-Node graph, baselines achieve 0.9751 fidelity with depth 8. QMRP reaches 0.9711 with depth 11 and 98% yield. "
            "On IBM Heavy-Hex, SABRE keeps circuit depth down to 30. QMRP reaches 0.7709, but circuit depth balloons to 113, and yield drops to 87.4%. "
            "On the Hyperbolic lattice, SABRE achieves the highest overall fidelity of 0.9258 at a minimal depth of 22. "
            "Simulation-Assisted Noise-Aware (C-MC) achieved 0.9185, while QMRP achieved 0.9208 at depth 93 with 90.7% acceptance. "
            "As explicitly required by the rubric, we tracked physical qubits: QMRP uses 5 qubits on the 5-node chip (100%), 8 qubits on IBM "
            "Heavy-Hex (6.3%), and 9 qubits on Hyperbolic (10.6%). "
            "Across all processors, QMRP's gate overhead cancels out the postselection gain, failing to beat single-path SABRE."
        ),
        subtext="Fulfills Deliverables 03 and 04. Emphasize that confidence intervals for SABRE and QMRP overlap.",
        questions=(
            "Q: Did QMRP beat SABRE on the Hyperbolic lattice?\n"
            "A: No, SABRE achieved 0.9258 while QMRP achieved 0.9208. Their 95% confidence intervals overlap ([0.8447, 0.9786] vs [0.8548, 0.9968])."
        )
    )

    # =========================================================================
    # SLIDE 10: Scientific Interpretation (6:35 - 7:20)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "09 Scientific Interpretation", "Deliverable 04: What QMRP Detects vs. What It Misses",
               "Unpacking the quantum noise physics behind why postselection fell short of single-path baselines.")

    add_card(s10, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
    tb = s10.shapes.add_textbox(Inches(1.1), Inches(1.7), Inches(5.0), Inches(5.0))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "What QMRP Detects (Syndrome S = 1)"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = COLOR_TEAL

    p = tf.add_paragraph()
    p.text = "\n✔ Single Bit-Flip Errors (Pauli X):\n" \
             "If an X error strikes Rail 1 or Rail 2 during transit, the destination decoder flips the syndrome qubit S to 1. The shot is discarded, successfully purifying the accepted sample pool."
    p.font.size = Pt(12); p.font.color.rgb = COLOR_NAVY

    p = tf.add_paragraph()
    p.text = "\n✔ Proof of Conditional Purification:\n" \
             "Within its own circuit, postselection works:\n" \
             "• Hyperbolic unpostselected fidelity: 0.8564\n" \
             "• Hyperbolic postselected fidelity: 0.9208 (+0.0644 lift!)\n" \
             "Filtering out the 9.31% failing shots genuinely improves output purity."
    p.font.size = Pt(12); p.font.color.rgb = COLOR_NAVY

    add_card(s10, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.4))
    tb_r = s10.shapes.add_textbox(Inches(7.1), Inches(1.7), Inches(5.1), Inches(5.0))
    tf_r = tb_r.text_frame; tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "What QMRP Misses (Syndrome S = 0)"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = COLOR_AMBER

    misses = [
        ("Phase-Flip Errors (Pauli Z): ", "Z errors commute directly through CNOT encoding/decoding gates and leave the syndrome qubit in |0⟩. Parity postselection is completely blind to dephasing!"),
        ("Correlated Double Bit-Flips (X ⊗ X): ", "Simultaneous errors on both rails preserve even parity and pass undetected."),
        ("Idle Decoherence on Port A: ", "While the two rails traverse multi-hop paths, the stationary reference qubit at port A suffers idle T1/T2 thermal relaxation."),
        ("Encoding & Decoding Gate Faults: ", "Errors occurring during the encoding and decoding CX gates directly poison the quantum state.")
    ]
    for title, desc in misses:
        p = tf_r.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf_r.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(11); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s10,
        timing="6:35 – 7:20 (45 seconds)",
        script=(
            "Why didn't QMRP beat SABRE? The answer lies in the quantum noise physics of what this code detects versus what it misses. "
            "Within its own circuit, postselection works as mathematically designed: on the Hyperbolic chip, raw unpostselected fidelity is 0.8564. "
            "When we discard the 9.3% failing shots, fidelity jumps to 0.9208—a lift of over 6 percentage points! It successfully purifies single Pauli X bit-flips. "
            "However, this simple repetition code has fundamental blind spots: "
            "First, it is completely blind to phase-flip (Z) errors. Z errors commute right through CNOT gates and leave the syndrome at 0. "
            "Second, the stationary reference qubit at Port A sits idle waiting for both rails to travel, accumulating thermal relaxation. "
            "And third, the extra CNOT gates used to encode and decode introduce new faults directly into the state."
        ),
        subtext="Fulfills Deliverable 04. Bit-flips (X) are caught, but phase dephasing (Z) slips right past undetected.",
        questions=(
            "Q: Can QMRP protect against phase errors?\n"
            "A: Not in its current form. Protecting against phase errors requires a full CSS code with dual syndromes, which requires significantly more qubits and gates."
        )
    )

    # =========================================================================
    # SLIDE 11: Hardware & Software Recommendation (7:20 - 8:05)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "10 System Recommendation", "Deliverable 05: Recommendation for Future Cloud Systems",
               "One actionable, data-driven design choice for future quantum compilers and cloud schedulers.")

    add_card(s11, Inches(1.5), Inches(1.5), Inches(10.3), Inches(5.4), bg_color=COLOR_WHITE, border_color=COLOR_BLUE)
    tb = s11.shapes.add_textbox(Inches(1.8), Inches(1.7), Inches(9.7), Inches(5.0))
    tf = tb.text_frame; tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Geometry- and Distance-Aware Selective Routing Policy"
    p.font.size = Pt(20); p.font.bold = True; p.font.color.rgb = COLOR_BLUE

    p = tf.add_paragraph()
    p.text = "Quantum cloud compilers should NEVER enable multipath repetition protection as a default transport mechanism. Instead, compilers should enforce a two-tier selective routing policy:"
    p.font.size = Pt(13); p.font.color.rgb = COLOR_NAVY

    rec_tiers = [
        ("Tier 1: Short-to-Medium Distances (d ≤ 4 hops):",
         "Enforce single-path noise-adaptive routing (e.g. SABRE or calibration-weighted Dijkstra). Over short distances, the gate and SWAP overhead of encoding, dual-rail transport, and syndrome extraction invariably exceeds the transport error rate."),
        ("Tier 2: High-Connectivity Geometries (Hyperbolic Lattices, d ≥ 5 hops):",
         "Expose multipath parity postselection as an OPT-IN compiler flag strictly when TWO criteria are met:\n"
         "  1. The user explicitly prioritizes output fidelity over runtime and can absorb a 5% to 15% shot discard penalty.\n"
         "  2. Physical two-qubit gate error rates (ε_gate) are substantially lower than cumulative link errors along the path, preventing encoding/decoding gates from dominating the noise budget.")
    ]
    for title, desc in rec_tiers:
        p = tf.add_paragraph()
        p.text = f"\n{title}"
        p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s11,
        timing="7:20 – 8:05 (45 seconds)",
        script=(
            "Based on our results, here is our key recommendation for future quantum cloud systems: "
            "Cloud compilers should NEVER enable multipath repetition protection as a default transport mechanism. "
            "Instead, compilers should implement a Geometry- and Distance-Aware Selective Routing Policy: "
            "For distances of 4 hops or fewer, compilers should strictly enforce single-path noise-adaptive routing like SABRE. "
            "Multipath postselection should only be exposed as an opt-in pass for long-distance transport on high-connectivity "
            "architectures like hyperbolic lattices, provided the user can tolerate a 10 to 15 percent shot discard penalty. "
            "This ensures that users only pay the gate and shot-yield overhead when physical geometry genuinely warrants it."
        ),
        subtext="Fulfills Deliverable 05 (Hardware or Software Recommendation). Deliver with confidence.",
        questions=(
            "Q: Under what hardware conditions would QMRP clearly beat SABRE?\n"
            "A: If physical two-qubit gate fidelity improves (e.g. error < 0.01%) while qubit routing paths remain long, "
            "the encoding/decoding gate penalty would shrink, allowing the parity postselection gain to dominate."
        )
    )

    # =========================================================================
    # SLIDE 12: Future Horizons & References (8:05 - 8:35)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12)
    add_header(s12, "11 Looking Forward", "Future Horizons & Academic References",
               "Extending multipath routing towards fault-tolerant architectures and acknowledging foundational literature.")

    add_card(s12, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
    tb = s12.shapes.add_textbox(Inches(1.1), Inches(1.7), Inches(5.0), Inches(5.0))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Future Research Directions"
    p.font.size = Pt(18); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    futures = [
        ("Full CSS Surface Encodings: ", "Extend beyond simple bit-flip repetition to dual-syndrome codes that detect both bit-flip (X) and phase-flip (Z) errors during routing."),
        ("Arbitrary Circuit Multi-Qubit Routing: ", "Generalize from 2-qubit Bell pair transport to full quantum algorithm compilation (e.g. Trotterized Hamiltonians, QAOA)."),
        ("Physical Hardware Validation: ", "Execute the benchmark suite on physical IBM Quantum QPUs and emerging neutral-atom hyperbolic hardware platforms.")
    ]
    for title, desc in futures:
        p = tf.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(11); p2.font.color.rgb = COLOR_TEXT_MUTED

    add_card(s12, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.4))
    tb_r = s12.shapes.add_textbox(Inches(7.1), Inches(1.7), Inches(5.1), Inches(5.0))
    tf_r = tb_r.text_frame; tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "Foundational References"
    p.font.size = Pt(18); p.font.bold = True; p.font.color.rgb = COLOR_PURPLE

    refs = [
        ("Noise-Aware Compiler Mappings (ASPLOS '19)",
         "P. Murali, J. M. Baker, A. Javadi-Abhari, F. T. Chong, M. Martonosi\n"
         "arXiv:1901.11054 [quant-ph] | DOI: 10.48550/arXiv.1901.11054"),
        ("Hyperbolic Codes & QMRP (quanTA USask, 2026)",
         "A. A. Mahmoud, S. Rayan\n"
         "Geometry-optimized hyperbolic codes for modular fault-tolerant quantum architectures\n"
         "arXiv:2610.10948v1 [quant-ph] | CC BY-NC-ND 4.0"),
        ("Acknowledgements:",
         "We thank quanTA, University of Saskatchewan, and Professor Steven Rayan for hosting this challenge.\nThank you!")
    ]
    for title, desc in refs:
        p = tf_r.add_paragraph()
        p.text = f"\n• {title}"
        p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
        p2 = tf_r.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10.5); p2.font.color.rgb = COLOR_TEXT_MUTED

    set_notes(
        s12,
        timing="8:05 – 8:35 (30 seconds)",
        script=(
            "Looking forward, we aim to extend this work to dual-syndrome CSS surface codes that protect against both "
            "bit-flips and phase-flips during routing, and test arbitrary multi-qubit circuits. "
            "We want to thank our host quanTA, Professor Steven Rayan, and the organizers. "
            "Thank you so much, and we welcome any questions!"
        ),
        subtext="Conclude with energy and open for questions. Total presentation time is 8 minutes 35 seconds.",
        questions=(
            "Q: Thank you for your presentation!\n"
            "A: Thank you! We are happy to walk through any specific circuit or data point."
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    print(f"PowerPoint presentation generated successfully: {output_path}")


if __name__ == "__main__":
    out_file = Path("presentation/QWeave_Presentation.pptx")
    create_deck(out_file)
