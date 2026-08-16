/**
 * Productive Self-Application — Interactive Engine
 * Clean-room implementation for instrument component inspection, slide lightbox, and citation copying.
 */

document.addEventListener('DOMContentLoaded', () => {
  initInstrumentInspector();
  initSlideLightbox();
  initCitationCopy();
  initSmoothScroll();
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
