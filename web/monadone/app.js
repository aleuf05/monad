/**
 * Productive Self-Application — Interactive Engine
 * Clean-room implementation for:
 * 1. Instrument component inspector
 * 2. Slide lightbox modal
 * 3. Citation copying
 * 4. Fully Functional Experimental Protocol Testbed
 */

document.addEventListener('DOMContentLoaded', () => {
  initInstrumentInspector();
  initSlideLightbox();
  initCitationCopy();
  initSmoothScroll();
  initExperimentalTestbed();
});

/* ==========================================================================
   1. Instrument Component Inspector
   ========================================================================== */
const INSTRUMENT_COMPONENTS = {
  X: {
    name: "X — State / Object Space",
    desc: "The objects, theories, reasoning prompts, or candidate states currently under consideration. In an ordinary pass, transformations act directly upon elements of X."
  },
  O: {
    name: "O — Operations",
    desc: "The space of available transformations and reasoning actions that can be applied to the current state representation."
  },
  S: {
    name: "S — Selection Policy",
    desc: "The policy or selector that chooses a transformation from O under the current context Σ: S : Σ → O."
  },
  E: {
    name: "E — Evaluation Map",
    desc: "The evaluation map producing feedback Φ regarding a transformed candidate state: E : X × Σ → Φ."
  },
  A: {
    name: "A — Abstraction Map",
    desc: "The meta-control or abstraction map that converts evaluation feedback into a higher-level rule, revision proposal, or heuristic: A : Φ → Λ."
  },
  C: {
    name: "C — Collapse / Reintegration",
    desc: "The reintegration map returning the abstract result back to the object level as an updated successor state or executable procedure: C : Λ → X."
  }
};

function initInstrumentInspector() {
  const buttons = document.querySelectorAll('.comp-btn');
  const headerEl = document.getElementById('comp-detail-header');
  const descEl = document.getElementById('comp-detail-desc');

  if (!buttons.length || !headerEl || !descEl) return;

  function selectComponent(sym) {
    const data = INSTRUMENT_COMPONENTS[sym];
    if (!data) return;

    buttons.forEach(btn => {
      const isMatch = btn.getAttribute('data-sym') === sym;
      btn.classList.toggle('active', isMatch);
      btn.setAttribute('aria-selected', isMatch ? 'true' : 'false');
    });

    headerEl.textContent = data.name;
    descEl.textContent = data.desc;
  }

  buttons.forEach((btn, index) => {
    btn.addEventListener('click', () => {
      const sym = btn.getAttribute('data-sym');
      selectComponent(sym);
    });

    btn.addEventListener('keydown', (e) => {
      let targetIndex = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        targetIndex = (index + 1) % buttons.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        targetIndex = (index - 1 + buttons.length) % buttons.length;
      }

      if (targetIndex !== null) {
        e.preventDefault();
        buttons[targetIndex].focus();
        selectComponent(buttons[targetIndex].getAttribute('data-sym'));
      }
    });
  });

  // Default selection
  selectComponent('X');
}

/* ==========================================================================
   2. Slide Lightbox Modal
   ========================================================================== */
const SLIDES = [
  {
    src: "assets/slide1.png",
    alt: "Slide 1: The Criterion — A useful loop should improve by passing through itself",
    caption: "Slide 1: The Criterion — A useful reflective loop should become more precise, constrained, or testable by passing through itself."
  },
  {
    src: "assets/slide2.png",
    alt: "Slide 2: The Experiment — Separate recursion from real improvement",
    caption: "Slide 2: The Experiment — Compare self-application against baseline, generic revision, and decorative self-reference under blinded evaluation."
  }
];

let currentSlideIdx = 0;

function initSlideLightbox() {
  const modal = document.getElementById('lightbox-modal');
  const imgEl = document.getElementById('lightbox-img');
  const captionEl = document.getElementById('lightbox-caption');
  const closeBtn = document.getElementById('lightbox-close');
  const prevBtn = document.getElementById('lightbox-prev');
  const nextBtn = document.getElementById('lightbox-next');
  const slideTriggers = document.querySelectorAll('.slide-zoom-trigger');

  if (!modal || !imgEl || !captionEl) return;

  function updateLightboxView() {
    const slide = SLIDES[currentSlideIdx];
    imgEl.src = slide.src;
    imgEl.alt = slide.alt;
    captionEl.textContent = slide.caption;
  }

  function openLightbox(idx) {
    currentSlideIdx = (idx >= 0 && idx < SLIDES.length) ? idx : 0;
    updateLightboxView();
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (closeBtn) closeBtn.focus();
  }

  function closeLightbox() {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function prevSlide() {
    currentSlideIdx = (currentSlideIdx - 1 + SLIDES.length) % SLIDES.length;
    updateLightboxView();
  }

  function nextSlide() {
    currentSlideIdx = (currentSlideIdx + 1) % SLIDES.length;
    updateLightboxView();
  }

  slideTriggers.forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      const idx = parseInt(trigger.getAttribute('data-slide-idx') || '0', 10);
      openLightbox(idx);
    });

    trigger.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const idx = parseInt(trigger.getAttribute('data-slide-idx') || '0', 10);
        openLightbox(idx);
      }
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
  if (prevBtn) prevBtn.addEventListener('click', (e) => { e.stopPropagation(); prevSlide(); });
  if (nextBtn) nextBtn.addEventListener('click', (e) => { e.stopPropagation(); nextSlide(); });

  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.classList.contains('lightbox-content')) {
      closeLightbox();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (!modal.classList.contains('active')) return;
    if (e.key === 'Escape') {
      closeLightbox();
    } else if (e.key === 'ArrowLeft') {
      prevSlide();
    } else if (e.key === 'ArrowRight') {
      nextSlide();
    }
  });
}

/* ==========================================================================
   3. Citation Copying (Clipboard API with Fallback)
   ========================================================================== */
const CITATION_TEXT = `Lampley, Cameron G. "Productive Self-Application: An Operational Criterion for Reflective Reasoning Systems." Candidate arXiv v1.0, 15 August 2026.`;

function initCitationCopy() {
  const copyButtons = document.querySelectorAll('.copy-citation-btn');
  const toast = document.getElementById('toast-msg');

  if (!copyButtons.length) return;

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg || "Citation copied";
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2800);
  }

  function executeCopy() {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(CITATION_TEXT)
        .then(() => showToast("Citation copied"))
        .catch(() => fallbackCopy());
    } else {
      fallbackCopy();
    }
  }

  function fallbackCopy() {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = CITATION_TEXT;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      showToast("Citation copied");
    } catch (err) {
      showToast("Failed to copy citation");
    }
  }

  copyButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      executeCopy();
    });
  });
}

/* ==========================================================================
   4. Smooth Scrolling Controls
   ========================================================================== */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#' || !targetId) return;
      const targetEl = document.querySelector(targetId);
      if (targetEl) {
        e.preventDefault();
        targetEl.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
}

/* ==========================================================================
   5. Fully Functional Experimental Protocol Testbed
   ========================================================================== */
const TESTBED_SPECIMENS = {
  rubric: {
    name: "Specimen A: Diagnostic Evaluation Rubric",
    conditions: {
      baseline: {
        lane: "Baseline (No Revision)",
        instruction: "Inspect original reasoning policy without revision.",
        code: `PROCEDURE DiagnosticRubric(claim):
  1. Check if argument has premises.
  2. Rate clarity on a 1-5 scale.
  3. Suggest general improvements.
  RETURN score, notes`,
        scores: { P: 2.8, K: 2.2, F: 1.9, C_pen: 0.1, O_pen: 0.2 },
        delta: 0.0,
        verdict: "neutral",
        badge: "FROZEN UNMODIFIED BASELINE"
      },
      generic: {
        lane: "Generic Revision (Clarity Edit)",
        instruction: "Revise procedure for clarity, professional tone, and thoroughness.",
        code: `PROCEDURE DiagnosticRubric_Refined(claim):
  1. Clearly verify empirical premises and context.
  2. Assess logical clarity, coherence, and soundness.
  3. Provide comprehensive structured feedback.
  RETURN detailed_score, structured_critique`,
        scores: { P: 3.6, K: 2.9, F: 2.4, C_pen: 0.05, O_pen: 0.1 },
        delta: 0.0,
        verdict: "neutral",
        badge: "CONTROL BASELINE (Δgeneric = 0.00)"
      },
      self: {
        lane: "Self-Application (M^up(M) Target)",
        instruction: "Apply revision procedure to its own selector, evaluator, and failure rules.",
        code: `PROCEDURE DiagnosticRubric_SelfApplied(claim):
  1. Isolate commitments C ⊆ claim that are falsifiable.
  2. Verify that Evaluator E rejects circular justifications.
  3. Bound claim scope: reject if ungrounded across held-out tests.
  4. Output explicit counterexample conditions.
  RETURN {precision: P(C), constraint: K(C), testability: F(C)}`,
        scores: { P: 4.8, K: 4.6, F: 4.7, C_pen: 0.0, O_pen: 0.0 },
        delta: +1.77,
        verdict: "pass",
        badge: "CRITERION SATISFIED (Δself - Δgeneric = +1.77 > 0)"
      },
      decorative: {
        lane: "Decorative Loop (Surface Syntax)",
        instruction: "Add recursive rhetoric without altering executable constraints.",
        code: `PROCEDURE DiagnosticRubric_RecursiveLoop(claim):
  // Engaging in recursive metacognitive self-reflection:
  1. Reflect upon the self-referential essence of premises.
  2. Iteratively ponder internal coherence of the loop.
  3. Self-critique the reflection of the critique.
  RETURN enlightened_score, recursive_narrative`,
        scores: { P: 3.0, K: 2.3, F: 1.8, C_pen: 0.35, O_pen: 0.45 },
        delta: -0.85,
        verdict: "fail",
        badge: "FALSIFIED: DECORATIVE RECURSION (Δdecorative - Δgeneric = -0.85 ≤ 0)"
      }
    }
  },
  invariants: {
    name: "Specimen B: Invariant Extractor",
    conditions: {
      baseline: {
        lane: "Baseline (No Revision)",
        instruction: "Extract state invariants using simple rule list.",
        code: `EXTRACTOR Invariants(state):
  Find unchanged variables in state transitions.
  RETURN preserved_keys`,
        scores: { P: 3.0, K: 2.5, F: 2.1, C_pen: 0.1, O_pen: 0.1 },
        delta: 0.0,
        verdict: "neutral",
        badge: "FROZEN UNMODIFIED BASELINE"
      },
      generic: {
        lane: "Generic Revision",
        instruction: "Rewrite invariant extractor for better formatting and coverage.",
        code: `EXTRACTOR Invariants_Clear(state):
  Systematically check all state keys for temporal stability.
  Log any modified variables.
  RETURN structured_invariants_list`,
        scores: { P: 3.7, K: 3.1, F: 2.8, C_pen: 0.05, O_pen: 0.05 },
        delta: 0.0,
        verdict: "neutral",
        badge: "CONTROL BASELINE (Δgeneric = 0.00)"
      },
      self: {
        lane: "Self-Application (M^up(M))",
        instruction: "Apply extractor to its own extraction rules to guarantee algebraic closure.",
        code: `EXTRACTOR Invariants_Lifted(state):
  1. Prove invariance under transformation group O.
  2. Require state hash continuity across branching depths.
  3. Reject any invariant that admits invalid state transitions.
  RETURN ProvenInvariants { closure: TRUE, falsifier_suite }`,
        scores: { P: 4.9, K: 4.8, F: 4.9, C_pen: 0.0, O_pen: 0.0 },
        delta: +1.67,
        verdict: "pass",
        badge: "CRITERION SATISFIED (Δself - Δgeneric = +1.67 > 0)"
      },
      decorative: {
        lane: "Decorative Loop",
        instruction: "Insert self-referential statements into extractor.",
        code: `EXTRACTOR Invariants_StrangeLoop(state):
  // The extractor reflects upon its own existence:
  Observe that the extraction is itself an invariant of the loop.
  RETURN meta_philosophical_invariants`,
        scores: { P: 2.9, K: 2.4, F: 1.7, C_pen: 0.4, O_pen: 0.5 },
        delta: -0.92,
        verdict: "fail",
        badge: "FALSIFIED: DECORATIVE RECURSION (Δdecorative - Δgeneric = -0.92 ≤ 0)"
      }
    }
  }
};

let activeSpecimenKey = 'rubric';
let activeConditionKey = 'self';

function initExperimentalTestbed() {
  const specimenSelect = document.getElementById('testbed-specimen-select');
  const laneButtons = document.querySelectorAll('.lane-btn');
  const codeBox = document.getElementById('testbed-code-box');
  const instructionEl = document.getElementById('testbed-instruction');
  const gaugeP = document.getElementById('gauge-fill-p');
  const gaugeK = document.getElementById('gauge-fill-k');
  const gaugeF = document.getElementById('gauge-fill-f');
  const valP = document.getElementById('gauge-val-p');
  const valK = document.getElementById('gauge-val-k');
  const valF = document.getElementById('gauge-val-f');
  const verdictMath = document.getElementById('testbed-verdict-math');
  const verdictBadge = document.getElementById('testbed-verdict-badge');

  if (!specimenSelect || !laneButtons.length || !codeBox) return;

  function renderTestbed() {
    const specimen = TESTBED_SPECIMENS[activeSpecimenKey];
    const data = specimen.conditions[activeConditionKey];
    if (!data) return;

    // Update lane button active states
    laneButtons.forEach(btn => {
      const isMatch = btn.getAttribute('data-condition') === activeConditionKey;
      btn.classList.toggle('active', isMatch);
      btn.setAttribute('aria-selected', isMatch ? 'true' : 'false');
    });

    // Update code & instruction
    if (instructionEl) instructionEl.textContent = data.instruction;
    if (codeBox) codeBox.textContent = data.code;

    // Update gauges
    const pctP = Math.min(100, Math.max(0, (data.scores.P / 5.0) * 100));
    const pctK = Math.min(100, Math.max(0, (data.scores.K / 5.0) * 100));
    const pctF = Math.min(100, Math.max(0, (data.scores.F / 5.0) * 100));

    if (gaugeP) gaugeP.style.width = `${pctP}%`;
    if (gaugeK) gaugeK.style.width = `${pctK}%`;
    if (gaugeF) gaugeF.style.width = `${pctF}%`;

    if (valP) valP.textContent = `${data.scores.P.toFixed(1)} / 5.0`;
    if (valK) valK.textContent = `${data.scores.K.toFixed(1)} / 5.0`;
    if (valF) valF.textContent = `${data.scores.F.toFixed(1)} / 5.0`;

    // Update verdict
    if (verdictMath) {
      if (activeConditionKey === 'self') {
        verdictMath.textContent = `Δself - Δgeneric = +${data.delta.toFixed(2)} > 0`;
        verdictMath.style.color = 'var(--accent-teal)';
      } else if (activeConditionKey === 'decorative') {
        verdictMath.textContent = `Δdecorative - Δgeneric = ${data.delta.toFixed(2)} ≤ 0`;
        verdictMath.style.color = '#ef4444';
      } else if (activeConditionKey === 'generic') {
        verdictMath.textContent = `Δgeneric - Δgeneric = 0.00 (Benchmark)`;
        verdictMath.style.color = 'var(--text-main)';
      } else {
        verdictMath.textContent = `Baseline (Unmodified Benchmark)`;
        verdictMath.style.color = 'var(--text-dim)';
      }
    }

    if (verdictBadge) {
      verdictBadge.textContent = data.badge;
      verdictBadge.className = `verdict-badge ${data.verdict}`;
    }
  }

  // Specimen Change
  specimenSelect.addEventListener('change', (e) => {
    activeSpecimenKey = e.target.value;
    renderTestbed();
  });

  // Lane Buttons
  laneButtons.forEach((btn, idx) => {
    btn.addEventListener('click', () => {
      activeConditionKey = btn.getAttribute('data-condition');
      renderTestbed();
    });

    btn.addEventListener('keydown', (e) => {
      let targetIdx = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        targetIdx = (idx + 1) % laneButtons.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        targetIdx = (idx - 1 + laneButtons.length) % laneButtons.length;
      }

      if (targetIdx !== null) {
        e.preventDefault();
        laneButtons[targetIdx].focus();
        activeConditionKey = laneButtons[targetIdx].getAttribute('data-condition');
        renderTestbed();
      }
    });
  });

  // Initial render
  renderTestbed();
}
