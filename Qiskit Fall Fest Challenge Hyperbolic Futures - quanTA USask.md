# | a a **Geometry-aware quantum cloud challenge** 

Hackathon overview 

**Qiskit Fall Fest 2026** Steven Rayan quanTA, University of Saskatchewan 

## **Connectivity, routing and noise** 

**Quantum circuits often require interactions between qubits that are not directly connected.** 

Routing introduces extra operations to realize those interactions. Under noise, these operations can reduce the quality of the result. 



Two designated ports 

Qiskit Fall Fest 2026 

quanTA / USask     02 

## **quanTA research and the cloud context** 

**Geometry and error protection** 

quanTA's research connects circuit diagrams and quantum error correction with questions about the geometry of physical implementations. 

**Hyperbolic superconducting architectures** 

Finite hyperbolic lattices motivate alternative patterns of connections and cycles. This challenge tests their consequences for routing and error-detection circuits. 

**A decade of cloud access** 

IBM opened its five-qubit cloud processor in 2016. Qiskit now provides a common framework for comparing historical, contemporary and hypothetical processor models. 

Qiskit Fall Fest 2026 

quanTA / USask     03 

## **Three processor models** 

**2016-inspired reference** 



<!-- Start of picture text -->
Five qubits<br><!-- End of picture text -->



Five-node reference graph Synthetic noise model 

**Contemporary IBM-style** Backend snapshot or fake backend 



Native target and gate set Contemporary compilation baseline 

**Hyperbolic-inspired model** 

Finite lattice-derived coupling graph 





<!-- Start of picture text -->
Hypothetical qubit<br>connectivity<br>Circuit-level model only<br><!-- End of picture text -->

Qiskit Fall Fest 2026 

quanTA / USask     04 

## **Challenge objective** 

**Create a verified Bell correlation between two designated ports on each processor model.** 

Establish an ideal and noisy baseline, then test one justified errordetection or protection strategy. 

Compare the resulting fidelity with the circuit cost and any discarded shots. Explain the differences between the three architectures. 

Qiskit Fall Fest 2026 

quanTA / USask     05 

## **The Bell-correlation task** 

**Target: |Φ⁺⟩ = (|00⟩ + |11⟩) / √2 at two designated ports** 



<!-- Start of picture text -->
Verification correlations<br>|0⟩ H<br>XX     YY     ZZ<br>compile and route<br>Together, these estimate<br>|0⟩<br>fidelity with the target Bell<br>state.<br><!-- End of picture text -->

A Bell pair gives a small, interpretable test of quantum coherence. Agreement in the Z basis alone would also occur for a classical mixture of 00 and 11. 

Qiskit Fall Fest 2026 

quanTA / USask     06 

## **Core comparison** 



<!-- Start of picture text -->
Noisy +<br>Processor model Ideal baseline Noisy baseline<br>protection<br>2016-inspired Case 1 Case 2 Case 3<br>Contemporary IBM-style Case 4 Case 5 Case 6<br>Hyperbolic-inspired Case 7 Case 8 Case 9<br><!-- End of picture text -->

For each model, compare the noisy baseline with the protected result and its additional cost. 

Qiskit Fall Fest 2026 

quanTA / USask     07 

## **Protection strategies** 

**Parity or stabilizer checks** 

Additional measurements can reveal particular errors without directly measuring the encoded information. 

**Syndrome postselection** 

Keep outcomes that pass a specified check. Any improvement in conditional fidelity must be reported together with the fraction of accepted shots. 

### **Geometry-aware encodings** 

More advanced teams can adapt an encoding or check network to the available connections, then measure its overhead. 

Qiskit Fall Fest 2026 

quanTA / USask     08 

## **Challenge rules** 

**Common requirements** 

Use the common processor definitions, fixed output ports and noise assumptions. 

Complete the three-model comparison and test one justified protection method. 

Report reproducible results, including added operations and postselection yield. 

**Choices and extensions** 

Choose the layout, routing method and protection strategy. 

Explore alternative noise models, larger circuits or geometry-aware encodings. 

Keep optional studies and QPU results separate from the common benchmark. 

Qiskit Fall Fest 2026 

quanTA / USask     09 

## **Required measurements** 

|**Bell fidelity**|**F(Φ⁺) = [1 + ⟨XX⟩ − ⟨YY⟩ + ⟨ZZ⟩] / 4**|
|---|---|
|**Measure**|**Report**|
|**Output quality**|Bell fidelity with uncertainty|
|**Circuit cost**|Depth and number of two-qubit gates|
|**Routing**|SWAP overhead|
|**Qubit use**|Physical qubits, including ancillas|
|**Postselection**|Acceptance fraction and discarded shots|



Qiskit Fall Fest 2026 

quanTA / USask     10 

## **Approaches for different experience levels** 



<!-- Start of picture text -->
Experience Suggested approach Main comparison<br>Bell preparation and a simple error-<br>Explorer Ideal, noisy and protected results<br>detection check<br>Placement, routing or improved<br>Builder Fidelity benefit versus extra operations<br>checks<br>Geometry-aware encoding or<br>Research Scaling and sensitivity to noise<br>stabilizer network<br><!-- End of picture text -->

Qiskit Fall Fest 2026 

quanTA / USask     11 

## **Interpreting the comparison** 

**Noise and compilation** 

Relate changes in fidelity to the operations introduced by compilation and to the assumed noise model. 

**Protection overhead** 

Assess whether the protection method compensates for its extra gates, ancillas and discarded shots. 

**Architectural conclusions** 

Distinguish connectivity effects from differences in gate sets or noise. A result from one finite model does not establish a universal advantage. 

Qiskit Fall Fest 2026 

quanTA / USask     12 

## **Required submission materials** 

**01 Reproducible notebook** 

Qiskit code, assumptions and recorded results 

**02 Graphs and circuits** 

The three coupling graphs with ports and the transpiled circuits 

- **03 Quantitative comparison** 

Fidelity, circuit cost and yield across the core cases 

- **04 Scientific interpretation Hardware or software** 

- **05 recommendation** 

An explanation of the results and their limitations 

One specific design choice for future cloud systems, supported by your results 

Qiskit Fall Fest 2026 

quanTA / USask     13 

## **Judging rubric** 

**Scientific correctness and reproducibility Quality of architecture comparison Protection or error-detection strategy** Effective use of Qiskit Evidence for the future-system recommendation Clarity of presentation 

**30% 20% 20% 15% 10% 5%** 

Qiskit Fall Fest 2026 

quanTA / USask     14 

