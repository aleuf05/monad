(function () {
  "use strict";

  var STORAGE_KEY = "monad.geometricIntentLexicon.v0.1";
  var mode = "reference";
  var selected = new Set();
  var sacred = new Set();
  var gesture = null;
  var drawing = false;
  var currentEpisode = null;
  var guideActive = false;
  var guideSaved = false;

  var stage = document.getElementById("geometryStage");
  var path = document.getElementById("gesturePath");
  var readout = document.getElementById("selectionReadout");
  var utterance = document.getElementById("utterance");
  var privatePhrase = document.getElementById("privatePhrase");
  var operationalMeaning = document.getElementById("operationalMeaning");
  var preview = document.getElementById("intentPreview");
  var compileState = document.getElementById("compileState");
  var reviewed = document.getElementById("humanReviewed");
  var saveButton = document.getElementById("saveEntry");
  var signal = document.getElementById("signal");
  var cards = document.getElementById("lexiconCards");
  var guideProgress = document.getElementById("guideProgress");
  var guideNext = document.getElementById("guideNext");
  var reflection = document.getElementById("reflectionSummary");

  var GUIDE_REFS = ["Fan.Face:A", "Panel.Hole:1", "Panel.Hole:2"];

  function updateGuide() {
    if (!guideActive) return;
    var referencesDone = GUIDE_REFS.every(function (ref) { return selected.has(ref); });
    var sacredDone = referencesDone && GUIDE_REFS.every(function (ref) { return sacred.has(ref); });
    var gestureDone = sacredDone && gesture && gesture.type === "keep-out" && gesture.points.length > 1;
    var compileDone = Boolean(gestureDone && currentEpisode && operationalMeaning.value.trim());
    var states = [referencesDone, sacredDone, gestureDone, compileDone, guideSaved];
    var count = states.filter(Boolean).length;
    document.querySelectorAll("[data-guide-step]").forEach(function (element, index) {
      element.classList.toggle("done", states[index]);
    });
    guideProgress.textContent = count + " / 5";
    if (!referencesDone) {
      guideNext.textContent = "Tap these three named chips below the diagram: Fan.Face:A, Panel.Hole:1, and Panel.Hole:2.";
    } else if (!sacredDone) {
      guideNext.textContent = "Good. Press “Mark selected sacred” so those exact interfaces cannot silently move.";
    } else if (!gestureDone) {
      guideNext.textContent = "Choose “Trace keep-out,” then draw a line across the diagram where the cable needs room.";
    } else if (!compileDone) {
      guideNext.textContent = "Describe what “usual forgiving fit” means for you, then press “Compile teaching episode.”";
    } else if (!guideSaved) {
      guideNext.textContent = "Read the plain-language reflection, check the human-review box, then save the lexicon version.";
    } else {
      guideNext.textContent = "Complete. You saved one provisional private meaning. A real printed fit must still test it.";
    }
  }

  function loadLexicon() {
    try {
      var parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function writeLexicon(entries) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }

  function setSignal(message, isError) {
    signal.textContent = message;
    signal.style.color = isError ? "var(--red)" : "var(--cyan)";
  }

  function updateReadout() {
    var refs = Array.from(selected);
    var protectedRefs = Array.from(sacred);
    var parts = refs.length ? "References: " + refs.join(", ") : "No explicit references selected.";
    if (protectedRefs.length) parts += " · Sacred: " + protectedRefs.join(", ");
    if (gesture) parts += " · Gesture: " + gesture.type + " (" + gesture.points.length + " samples)";
    readout.textContent = parts;
  }

  function updateGeometryClasses() {
    document.querySelectorAll(".reference").forEach(function (element) {
      var ref = element.dataset.ref;
      element.classList.toggle("selected", selected.has(ref));
      element.classList.toggle("sacred", sacred.has(ref));
    });
    document.querySelectorAll("[data-select-ref]").forEach(function (element) {
      var ref = element.dataset.selectRef;
      element.classList.toggle("selected", selected.has(ref));
      element.classList.toggle("sacred", sacred.has(ref));
    });
  }

  function toggleReference(ref) {
    if (selected.has(ref)) {
      selected.delete(ref);
      sacred.delete(ref);
    } else {
      selected.add(ref);
    }
    updateGeometryClasses();
    updateReadout();
    updateGuide();
  }

  function setMode(next) {
    mode = next;
    document.querySelectorAll("[data-mode]").forEach(function (button) {
      button.classList.toggle("active", button.dataset.mode === next);
    });
    stage.style.cursor = next === "reference" ? "default" : "crosshair";
  }

  function svgPoint(event) {
    var point = stage.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(stage.getScreenCTM().inverse());
  }

  function renderGesture() {
    if (!gesture || gesture.points.length < 2) {
      path.setAttribute("d", "");
      return;
    }
    var d = gesture.points.map(function (point, index) {
      return (index ? "L" : "M") + point.x.toFixed(1) + " " + point.y.toFixed(1);
    }).join(" ");
    path.setAttribute("d", d);
  }

  document.querySelectorAll("[data-mode]").forEach(function (button) {
    button.addEventListener("click", function () { setMode(button.dataset.mode); });
  });

  document.querySelectorAll(".reference").forEach(function (element) {
    element.addEventListener("click", function (event) {
      if (mode !== "reference") return;
      event.stopPropagation();
      toggleReference(element.dataset.ref);
    });
  });

  document.querySelectorAll("[data-select-ref]").forEach(function (element) {
    element.addEventListener("click", function () {
      setMode("reference");
      toggleReference(element.dataset.selectRef);
    });
  });

  stage.addEventListener("pointerdown", function (event) {
    if (mode === "reference") return;
    event.preventDefault();
    drawing = true;
    stage.setPointerCapture(event.pointerId);
    gesture = { type: mode, points: [svgPoint(event)] };
    renderGesture();
    updateReadout();
  });

  stage.addEventListener("pointermove", function (event) {
    if (!drawing || !gesture) return;
    var point = svgPoint(event);
    var previous = gesture.points[gesture.points.length - 1];
    if (Math.hypot(point.x - previous.x, point.y - previous.y) < 5) return;
    gesture.points.push(point);
    renderGesture();
    updateReadout();
  });

  function finishGesture(event) {
    if (!drawing) return;
    drawing = false;
    if (stage.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
    updateReadout();
    updateGuide();
  }
  stage.addEventListener("pointerup", finishGesture);
  stage.addEventListener("pointercancel", finishGesture);

  document.getElementById("markSacred").addEventListener("click", function () {
    if (!selected.size) {
      setSignal("Select one or more explicit references before marking them sacred.", true);
      return;
    }
    selected.forEach(function (ref) { sacred.add(ref); });
    updateGeometryClasses();
    updateReadout();
    setSignal("Selected references marked sacred in this teaching episode.");
    updateGuide();
  });

  document.getElementById("clearStage").addEventListener("click", function () {
    selected.clear();
    sacred.clear();
    gesture = null;
    currentEpisode = null;
    guideSaved = false;
    reviewed.checked = false;
    saveButton.disabled = true;
    path.setAttribute("d", "");
    preview.textContent = "Words, references, and gesture evidence will appear here.";
    reflection.textContent = "";
    reflection.className = "reflection";
    compileState.textContent = "not compiled";
    compileState.className = "state";
    updateGeometryClasses();
    updateReadout();
    setSignal("Teaching stage reset.");
    updateGuide();
  });

  function unresolvedTerms(text, meaning) {
    var candidateTerms = ["usual", "forgiving", "stout", "natural", "enough", "strong", "light", "clean"];
    return candidateTerms.filter(function (term) {
      return new RegExp("\\b" + term + "\\b", "i").test(text) && !meaning.trim();
    });
  }

  function inferRelations(text) {
    var relations = [];
    if (/\bmount|connect|attach\b/i.test(text)) relations.push({ operation: "CONNECT", status: "proposed" });
    if (/\bavoid|keep[- ]?out|clear of\b/i.test(text)) relations.push({ operation: "CLEAR", status: "proposed" });
    if (/\bpreserve|sacred|must not change\b/i.test(text) || sacred.size) {
      relations.push({ operation: "PRESERVE", references: Array.from(sacred), status: "explicit-or-proposed" });
    }
    if (/\bairflow|open\b/i.test(text)) relations.push({ operation: "PRESERVE_REGION", status: "proposed" });
    return relations;
  }

  function compile() {
    var words = utterance.value.trim();
    var phrase = privatePhrase.value.trim();
    var meaning = operationalMeaning.value.trim();
    var unresolved = unresolvedTerms(words, meaning);

    currentEpisode = {
      schema_version: "monad.geometricTeachingEpisode.v0.1",
      id: "episode-" + Date.now(),
      recorded_at: new Date().toISOString(),
      epistemic_status: "human-review-required",
      expression: {
        words: words,
        private_phrase_candidate: phrase
      },
      explicit_references: Array.from(selected).map(function (ref) {
        return { ref: ref, sacred: sacred.has(ref) };
      }),
      gesture: gesture ? {
        type: gesture.type,
        coordinate_space: "demo-stage-640x400",
        samples: gesture.points.map(function (point) {
          return [Number(point.x.toFixed(1)), Number(point.y.toFixed(1))];
        })
      } : null,
      proposed_interpretation: {
        relations: inferRelations(words),
        operational_meaning: meaning || null,
        unresolved_terms: unresolved
      },
      evidence: {
        demonstrations: 1,
        physical_results: 0,
        independent_confirmations: 0
      },
      human_review: {
        reviewed: false,
        universal_claim: false
      }
    };

    preview.textContent = JSON.stringify(currentEpisode, null, 2);
    var referenceNames = currentEpisode.explicit_references.map(function (item) {
      return item.ref + (item.sacred ? " (sacred)" : "");
    });
    reflection.innerHTML =
      "<strong>I understood:</strong><br>" +
      (referenceNames.length
        ? "Use " + escapeHtml(referenceNames.join(", ")) + ".<br>"
        : "No exact geometry references were supplied.<br>") +
      (gesture
        ? "Treat your drawn path as an explicit <strong>" + escapeHtml(gesture.type) + "</strong> gesture.<br>"
        : "No gesture was supplied.<br>") +
      (meaning
        ? "For now, “" + escapeHtml(phrase) + "” means: " + escapeHtml(meaning) + "<br>"
        : "The private phrase still lacks an operational meaning.<br>") +
      "<em>This interpretation is proposed, not physically validated.</em>";
    reflection.className = "reflection visible";
    compileState.textContent = unresolved.length ? "unresolved language" : "ready for review";
    compileState.className = "state " + (unresolved.length ? "unresolved" : "ready");
    reviewed.checked = false;
    saveButton.disabled = true;
    setSignal(unresolved.length
      ? "Compiled with unresolved terms: " + unresolved.join(", ") + ". Define the operational meaning or preserve the uncertainty."
      : "Teaching episode compiled. Inspect it before review.");
    updateGuide();
  }

  document.getElementById("compileIntent").addEventListener("click", compile);
  reviewed.addEventListener("change", function () {
    saveButton.disabled = !(reviewed.checked && currentEpisode);
  });

  saveButton.addEventListener("click", function () {
    if (!currentEpisode || !reviewed.checked) return;
    var phrase = privatePhrase.value.trim();
    var meaning = operationalMeaning.value.trim();
    if (!phrase || !meaning) {
      setSignal("A reusable entry requires both a private phrase and your explicit operational meaning.", true);
      return;
    }
    var entries = loadLexicon();
    var priorVersions = entries.filter(function (entry) { return entry.phrase.toLowerCase() === phrase.toLowerCase(); });
    currentEpisode.human_review.reviewed = true;
    currentEpisode.epistemic_status = "reviewed-provisional";
    var entry = {
      schema_version: "monad.intentLexiconEntry.v0.1",
      phrase: phrase,
      version: priorVersions.length + 1,
      operational_meaning: meaning,
      contexts: Array.from(selected),
      gesture_type: gesture ? gesture.type : null,
      evidence: currentEpisode.evidence,
      confidence: "provisional",
      exceptions: [],
      source_episode_id: currentEpisode.id,
      source_episode: structuredClone(currentEpisode),
      reviewed_at: new Date().toISOString(),
      revision_history: priorVersions.map(function (prior) {
        return { version: prior.version, reviewed_at: prior.reviewed_at };
      })
    };
    entries.push(entry);
    writeLexicon(entries);
    preview.textContent = JSON.stringify(currentEpisode, null, 2);
    renderLexicon();
    guideSaved = true;
    updateGuide();
    saveButton.disabled = true;
    setSignal("Saved “" + phrase + "” version " + entry.version + " as provisional.");
  });

  function renderLexicon() {
    var entries = loadLexicon();
    if (!entries.length) {
      cards.innerHTML = '<div class="empty">No reviewed private meanings saved yet.</div>';
      return;
    }
    cards.innerHTML = entries.slice().reverse().map(function (entry) {
      var lineage = entry.revision_history.length
        ? "Evolved from v" + entry.revision_history[entry.revision_history.length - 1].version +
          " · " + entry.revision_history.length + " prior version" +
          (entry.revision_history.length === 1 ? "" : "s")
        : "First recorded version";
      var episode = entry.source_episode && typeof entry.source_episode === "object"
        ? entry.source_episode
        : null;
      var sampleCount = episode?.gesture?.samples?.length || 0;
      var trace = episode
        ? "Trace preserved · " + episode.explicit_references.length + " references · " +
          sampleCount + " gesture samples"
        : "Legacy trace · source ID only";
      return '<article class="card">' +
        "<h3>“" + escapeHtml(entry.phrase) + "” <span class=\"meta\">v" + entry.version + "</span></h3>" +
        '<div class="meaning">' + escapeHtml(entry.operational_meaning) + "</div>" +
        '<div class="meta">Context: ' + escapeHtml(entry.contexts.join(", ") || "not yet bounded") + "</div>" +
        '<div class="meta">' + escapeHtml(lineage) + "</div>" +
        '<div class="meta">' + escapeHtml(trace) + "</div>" +
        '<div class="warning">Provisional · ' + entry.evidence.physical_results + " physical results · not universal</div>" +
        "</article>";
    }).join("");
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
    });
  }

  document.getElementById("exportLexicon").addEventListener("click", function () {
    var payload = {
      schema_version: "monad.intentLexiconExport.v0.1",
      exported_at: new Date().toISOString(),
      portability_note: "Private meanings remain inspectable and are not universal claims.",
      entries: loadLexicon()
    };
    var url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    var link = document.createElement("a");
    link.href = url;
    link.download = "geometric-intent-lexicon.json";
    link.click();
    URL.revokeObjectURL(url);
    setSignal("Lexicon exported as inspectable JSON.");
  });

  document.getElementById("clearLexicon").addEventListener("click", function () {
    if (!confirm("Clear this browser's private geometric lexicon? Export first if you need a recoverable copy.")) return;
    localStorage.removeItem(STORAGE_KEY);
    renderLexicon();
    setSignal("Local lexicon cleared.");
  });

  document.getElementById("startGuide").addEventListener("click", function () {
    guideActive = true;
    guideSaved = false;
    selected.clear();
    sacred.clear();
    gesture = null;
    currentEpisode = null;
    path.setAttribute("d", "");
    utterance.value = "Mount this fan to these two holes, keep the airflow open, avoid the cable, and use my usual forgiving fit.";
    privatePhrase.value = "usual forgiving fit";
    operationalMeaning.value = "";
    operationalMeaning.placeholder = "Example: 0.25–0.35 mm clearance per side for removable PETG fits on my FDM printer.";
    reviewed.checked = false;
    saveButton.disabled = true;
    preview.textContent = "The complete machine record will appear after compilation.";
    reflection.textContent = "";
    reflection.className = "reflection";
    compileState.textContent = "guided experiment";
    compileState.className = "state";
    updateGeometryClasses();
    updateReadout();
    updateGuide();
    document.getElementById("stageWrap").scrollIntoView({ behavior: "smooth", block: "center" });
    setSignal("Guided experiment started.");
  });

  updateReadout();
  renderLexicon();
}());
