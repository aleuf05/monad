# Integration Forge — Candidate Matrix (provisional)

| Candidate | Interface gap / adapter | Feedback signal | Smallest test | Main kill condition |
|---|---|---|---|---|
| Reality Debugger | Vision/manual context → grounded fault hypotheses and cited next checks | Diagnosis accuracy and unnecessary-step rate | One device/manual family, seeded faults | No improvement over manual search or generic vision QA |
| Universal Lab Front-End | Commodity instrument output → normalized cloud notebook and experiment plan | Reproducibility and setup-error reduction | One sensor, one assay, one structured notebook | Adapter loses calibration/provenance or adds operator work |
| World-to-CAD | Photogrammetry → constrained editable CAD with fabrication tolerances | Dimensional error and successful fabrication | One simple manufactured object | Geometry is not fabrication-valid without extensive manual repair |
| Skill Teleporter | Expert demonstration → state-aware multimodal coaching | Novice task success and correction count | One short motor skill with observable checkpoints | Coaching does not reduce correction debt against video-only control |
| Spatial Acoustic Tomograph | Synchronized commodity audio → spatial field estimate | Reconstruction error against known geometry | Small controlled room and known source positions | Inverse problem is non-identifiable at commodity SNR |

## Provisional ranking

1. **Reality Debugger** — cheapest proof-of-interface and clearest human value.
2. **Universal Lab Front-End** — strong measurement loop, but calibration is a
   serious early risk.
3. **World-to-CAD** — valuable and buildable, with a demanding physical test.
4. **Skill Teleporter** — promising correction-debt measurement, but human
   acceptance and safety make the first test slower.
5. **Spatial Acoustic Tomograph** — potentially novel, but identifiability
   should be established before investing in an interface.

## Selection rule

This ranking is a proposal, not a result. Advance Reality Debugger only if a
cheap test can compare it against ordinary manual lookup and generic vision
question-answering on the same seeded fault set.
