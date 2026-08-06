/*
 * Semantic Text Metamorphosis -- reusable Live Captain capability.
 *
 * v0.2: a small physics-driven choreography engine. Text fragments lifted
 * out of the Captain's own rendered message become physical bodies (mass,
 * velocity, a critically-underdamped spring chasing a target) simulated
 * every animation frame -- not pre-baked WAAPI keyframes tracing a fixed
 * path. A message can chain any of a fixed vocabulary of primitives
 * (lift, orbit, scatter, converge, shed, morph, merge, pulse, crystallize,
 * trail, land) in whatever order and with whatever parameters it wants,
 * instead of always getting one hardcoded five-phase sequence. The
 * synthesis itself (what text a `morph`/`crystallize`/merge lands as) is
 * NOT computed by this component -- it is always caller-supplied. This
 * component performs the expressive transformation act; it does not
 * invent meaning.
 *
 * Why real physics instead of keyframes: a fixed keyframe path is the same
 * every time and reads as mechanical no matter how it's parameterized --
 * that was the actual complaint that caused this rewrite. A spring chasing
 * a (possibly moving) target produces continuous, non-repeating, organic
 * motion for free: natural ease in/out, overshoot-and-settle on arrival,
 * and -- because velocity is never reset between primitives -- real
 * follow-through when one move flows into the next.
 *
 * No dependencies. requestAnimationFrame drives the simulation;
 * TreeWalker-based phrase location wraps/unwraps text nodes so the source
 * DOM is restored exactly if a run is cancelled before landing.
 */

(function (global) {
  "use strict";

  var REDUCE_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

  function prefersReducedMotion() {
    return typeof matchMedia === "function" && matchMedia(REDUCE_MOTION_QUERY).matches;
  }

  // ---- phrase location -----------------------------------------------

  function findTextNodeContaining(container, phrase) {
    var needle = phrase.toLowerCase();
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      var idx = node.textContent.toLowerCase().indexOf(needle);
      if (idx !== -1) return { node: node, idx: idx };
    }
    return null;
  }

  function wrapPhrase(container, phrase) {
    var found = findTextNodeContaining(container, phrase);
    if (!found) return null;
    var node = found.node, idx = found.idx;
    var full = node.textContent;
    var matchText = full.slice(idx, idx + phrase.length);
    var before = full.slice(0, idx);
    var after = full.slice(idx + phrase.length);

    var mark = document.createElement("mark");
    mark.className = "metamorphosis-source-lifted";
    mark.textContent = matchText;

    var beforeNode = document.createTextNode(before);
    var afterNode = document.createTextNode(after);
    var parent = node.parentNode;
    parent.replaceChild(afterNode, node);
    parent.insertBefore(mark, afterNode);
    parent.insertBefore(beforeNode, mark);

    return {
      mark: mark,
      matchText: matchText,
      restore: function () {
        var restored = document.createTextNode(matchText);
        parent.replaceChild(restored, mark);
        parent.normalize();
      },
    };
  }

  // ---- physics ----------------------------------------------------------
  //
  // Each body is a critically-underdamped spring in x/y/rotation/scale,
  // integrated with semi-implicit Euler. Per-body mass/stiffness/damping
  // jitter (+-15-20%) so a group of bodies never moves in perfect lockstep
  // -- the actual "physical, not synchronized" feel comes from here, not
  // from any single primitive.

  var actorSeq = 0;

  function makeBody(opts) {
    var jitter = function (base, spread) { return base * (1 - spread + Math.random() * spread * 2); };
    return {
      x: 0, y: 0, vx: 0, vy: 0,
      rot: 0, vrot: 0,
      scale: 1, vscale: 0,
      brightness: 1, vbrightness: 0,
      opacity: 1, vopacity: 0,
      targetX: 0, targetY: 0, targetRot: 0, targetScale: 1, targetBrightness: 1, targetOpacity: 1,
      mass: jitter(opts.mass || 1, 0.2),
      k: jitter(opts.k || 210, 0.18),
      damping: jitter(opts.damping || 17, 0.15),
      updateTarget: null, // optional (body, tSec, dt) => void, for moving targets (e.g. orbit)
      onFrame: null, // optional (body, tSec, dt) => void, for DOM rendering / cleanup
    };
  }

  function springStep(cur, vel, target, mass, k, damping, dt) {
    var f = -k * (cur - target) - damping * vel;
    var v2 = vel + (f / mass) * dt;
    return [cur + v2 * dt, v2];
  }

  function stepBody(b, dt) {
    var r;
    r = springStep(b.x, b.vx, b.targetX, b.mass, b.k, b.damping, dt); b.x = r[0]; b.vx = r[1];
    r = springStep(b.y, b.vy, b.targetY, b.mass, b.k, b.damping, dt); b.y = r[0]; b.vy = r[1];
    r = springStep(b.rot, b.vrot, b.targetRot, b.mass, b.k * 0.5, b.damping * 0.7, dt); b.rot = r[0]; b.vrot = r[1];
    r = springStep(b.scale, b.vscale, b.targetScale, b.mass, b.k * 0.9, b.damping * 0.8, dt); b.scale = r[0]; b.vscale = r[1];
    r = springStep(b.brightness, b.vbrightness, b.targetBrightness, b.mass, b.k * 0.7, b.damping * 1.1, dt); b.brightness = r[0]; b.vbrightness = r[1];
    r = springStep(b.opacity, b.vopacity, b.targetOpacity, 1, 240, 26, dt); b.opacity = r[0]; b.vopacity = r[1];
  }

  function settled(b, posEps, velEps) {
    return Math.abs(b.x - b.targetX) < posEps && Math.abs(b.y - b.targetY) < posEps &&
      Math.hypot(b.vx, b.vy) < velEps;
  }

  function waitUntil(predicate, maxMs) {
    return new Promise(function (resolve) {
      var start = performance.now();
      function check() {
        if (predicate() || performance.now() - start > maxMs) { resolve(); return; }
        requestAnimationFrame(check);
      }
      check();
    });
  }

  function nextFrame() {
    return new Promise(function (resolve) { requestAnimationFrame(resolve); });
  }

  // A single shared rAF loop per run() call, stepping every live body
  // (actors, in-flight shed fragments, trail ghosts) together each frame.
  function Simulation() {
    this.bodies = [];
    this.running = false;
    this.lastT = 0;
    this._raf = null;
  }
  Simulation.prototype.add = function (b) { this.bodies.push(b); };
  Simulation.prototype.remove = function (b) {
    var i = this.bodies.indexOf(b);
    if (i !== -1) this.bodies.splice(i, 1);
  };
  Simulation.prototype.start = function () {
    if (this.running) return;
    this.running = true;
    var self = this;
    function frame(t) {
      if (!self.running) return;
      var dt = self.lastT ? Math.min((t - self.lastT) / 1000, 1 / 30) : 1 / 60;
      self.lastT = t;
      var tSec = t / 1000;
      self.bodies.slice().forEach(function (b) {
        if (b.updateTarget) b.updateTarget(b, tSec, dt);
        stepBody(b, dt);
        if (b.onFrame) b.onFrame(b, tSec, dt);
      });
      self._raf = requestAnimationFrame(frame);
    }
    this._raf = requestAnimationFrame(frame);
  };
  Simulation.prototype.stop = function () {
    this.running = false;
    if (this._raf != null) cancelAnimationFrame(this._raf);
  };

  // ---- actor construction / rendering -----------------------------------

  // Split by actual human-perceived characters, not raw UTF-16 code units.
  // Plain `.split("")` cuts emoji above the Basic Multilingual Plane
  // (almost all modern emoji) into two broken surrogate halves, and
  // shatters ZWJ compound emoji (family/profession sequences) into
  // meaningless fragments -- both fly apart as garbage instead of moving
  // as one glyph. Intl.Segmenter grapheme mode keeps every such sequence
  // as a single unit; Array.from (codepoint-aware, no ZWJ handling) is the
  // fallback for engines without it.
  function graphemeSplit(text) {
    if (typeof Intl !== "undefined" && Intl.Segmenter) {
      var segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
      var out = [];
      var iter = segmenter.segment(text)[Symbol.iterator]();
      var next;
      while (!(next = iter.next()).done) out.push(next.value.segment);
      return out;
    }
    return Array.from(text);
  }

  function buildCharSpans(el, text) {
    el.textContent = "";
    graphemeSplit(text).forEach(function (ch) {
      var span = document.createElement("span");
      span.className = "metamorphosis-char";
      span.textContent = ch === " " ? " " : ch;
      span.style.display = "inline-block";
      el.appendChild(span);
    });
  }

  function makeActor(sourceEl, text) {
    var rect = sourceEl.getBoundingClientRect();
    var style = getComputedStyle(sourceEl);
    var el = document.createElement("div");
    el.className = "metamorphosis-actor";
    el.id = "metamorphosis-actor-" + ++actorSeq;
    el.style.cssText =
      "position:fixed; left:" + rect.left + "px; top:" + rect.top + "px; " +
      "font-family:" + style.fontFamily + "; font-size:" + style.fontSize + "; " +
      "color:" + style.color + "; font-weight:" + style.fontWeight + "; " +
      "line-height:" + style.lineHeight + "; white-space:nowrap; pointer-events:none; " +
      "will-change:transform,opacity,filter; transform-origin:center center;";
    buildCharSpans(el, text);
    var body = makeBody({});
    return { el: el, body: body, rect: rect, text: text, trail: [] };
  }

  function renderActor(actor) {
    var b = actor.body;
    var speed = Math.hypot(b.vx, b.vy);
    // Squash & stretch along the direction of travel -- the single
    // biggest lever for "feels physical" vs "slides on rails": faster
    // motion visibly elongates the glyph along its heading and compresses
    // it perpendicular to that heading, exactly like classic animation.
    var stretch = Math.min(1 + speed * 0.0016, 1.5);
    var heading = speed > 4 ? Math.atan2(b.vy, b.vx) : 0;
    var headingDeg = (heading * 180) / Math.PI;
    actor.el.style.transform =
      "translate(" + b.x + "px," + b.y + "px) " +
      "rotate(" + b.rot + "deg) " +
      "rotate(" + headingDeg + "deg) scale(" + (b.scale * stretch) + "," + (b.scale / Math.sqrt(stretch)) + ") rotate(" + (-headingDeg) + "deg)";
    actor.el.style.opacity = String(Math.max(0, Math.min(1, b.opacity)));
    actor.el.style.filter = "brightness(" + Math.max(0, b.brightness) + ")";
  }

  function spawnTrailGhost(overlay, actor) {
    var ghost = actor.el.cloneNode(true);
    ghost.id = "";
    ghost.className = "metamorphosis-trail-ghost";
    ghost.style.opacity = String(0.32 * Math.max(0, Math.min(1, actor.body.opacity)));
    ghost.style.willChange = "opacity";
    overlay.appendChild(ghost);
    var anim = ghost.animate([{ opacity: ghost.style.opacity }, { opacity: 0 }], { duration: 260, easing: "ease-out" });
    anim.finished.catch(function () {}).then(function () { ghost.remove(); });
  }

  // ---- the component ----------------------------------------------------

  function SemanticMetamorphosis(root) {
    this._root = root || document.body;
    this._overlay = document.createElement("div");
    this._overlay.className = "metamorphosis-overlay";
    this._overlay.style.cssText = "position:fixed; inset:0; pointer-events:none; z-index:9999; overflow:visible;";
    this._root.appendChild(this._overlay);

    this._live = document.createElement("div");
    this._live.className = "metamorphosis-live-region";
    this._live.setAttribute("role", "status");
    this._live.setAttribute("aria-live", "polite");
    this._live.style.cssText = "position:fixed; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap;";
    this._root.appendChild(this._live);

    this._busy = false;
  }

  SemanticMetamorphosis.prototype._announce = function (text) {
    this._live.textContent = text;
  };

  // cancel() always RESOLVES the pending run().done promise with a
  // structured { cancelled: true, ... } result -- never rejects.
  SemanticMetamorphosis.prototype.cancel = function () {
    if (!this._busy || !this._ctx) return;
    this._ctx.cancelled = true;
    this._ctx.sim.stop();
    this._ctx.actors.forEach(function (a) { a.el.remove(); });
    this._ctx.restoreFns.forEach(function (fn) { try { fn(); } catch (e) {} });
    this._ctx.overlay = null;
    var p = this._pending;
    var result = {
      cancelled: true,
      sourcePhrases: p.foundPhrases,
      stepsRun: p.stepsRun,
      durationMs: Math.round(performance.now() - p.start),
      accessibleDescription: "Semantic metamorphosis cancelled before landing.",
      timestamp: new Date().toISOString(),
    };
    var resolveDone = p.resolveDone;
    this._pending = null;
    this._ctx = null;
    this._busy = false;
    resolveDone(result);
  };

  // ---- primitive step vocabulary ----------------------------------------
  //
  // Every primitive is (ctx, args) => Promise<void>, and only ever touches
  // ctx.actors (the live body/DOM set) and ctx.sim (the shared simulation).
  // Reduced-motion mode snaps bodies straight to target and resolves near-
  // instantly, but still runs the same steps in the same order with the
  // same accessible announcements -- structure preserved, motion skipped.

  function settleNow(bodies) {
    bodies.forEach(function (b) {
      b.x = b.targetX; b.y = b.targetY; b.vx = 0; b.vy = 0;
      b.scale = b.targetScale; b.vscale = 0;
      b.rot = b.targetRot; b.vrot = 0;
      b.brightness = b.targetBrightness; b.vbrightness = 0;
      b.opacity = b.targetOpacity; b.vopacity = 0;
    });
  }

  var PRIMITIVES = {
    lift: function (ctx, args) {
      var phrases = (args.phrases || []).slice(0, 6);
      var wrapped = phrases.map(function (p) { return wrapPhrase(ctx.sourceContainer, p); }).filter(Boolean);
      wrapped.forEach(function (w) { ctx.restoreFns.push(w.restore); });
      ctx.foundPhrases = wrapped.map(function (w) { return w.matchText; });
      ctx.announce("Lifting " + ctx.foundPhrases.join(", ") + " out of message text.");

      var anchorMark = document.createElement("div");
      anchorMark.className = "metamorphosis-anchor-glyph";
      anchorMark.textContent = ctx.anchorGlyph;
      anchorMark.style.cssText =
        "position:fixed; left:" + ctx.gatherX + "px; top:" + ctx.gatherY + "px; " +
        "transform:translate(-50%,-50%); font-size:1.4rem; opacity:0.85; pointer-events:none;";
      ctx.overlay.appendChild(anchorMark);
      ctx.anchorEl = anchorMark;
      ctx.restoreFns.push(function () { anchorMark.remove(); });

      ctx.actors = wrapped.map(function (w) {
        var a = makeActor(w.mark, w.matchText);
        w.mark.style.opacity = "0.25";
        a.body.vy = -70; // a small detach "pop"
        ctx.overlay.appendChild(a.el);
        ctx.sim.add(a.body);
        a.body.onFrame = function () {
          renderActor(a);
          if (ctx.trailEnabled && Math.random() < 0.12) spawnTrailGhost(ctx.overlay, a);
        };
        return a;
      });

      if (ctx.reduced) { settleNow(ctx.actors.map(function (a) { return a.body; })); return Promise.resolve(); }
      return waitUntil(function () { return ctx.actors.every(function (a) { return settled(a.body, 0.8, 6); }); }, 500);
    },

    orbit: function (ctx, args) {
      if (!ctx.actors.length) return Promise.resolve();
      var turns = args.turns != null ? Number(args.turns) : 1;
      var radius = args.radius != null ? Number(args.radius) : 54;
      ctx.announce("Orbiting " + ctx.foundPhrases.join(", ") + " around " + ctx.anchorGlyph + ".");
      var n = ctx.actors.length;
      var durationSec = Math.max(0.5, 0.85 * Math.max(1, Math.abs(turns)));
      var t0 = performance.now() / 1000;
      ctx.actors.forEach(function (a, i) {
        var phase0 = (i / n) * Math.PI * 2 + Math.random() * 0.3;
        var omegaJitter = 1 + (Math.random() * 0.16 - 0.08);
        var radiusJitter = 0.85 + Math.random() * 0.3;
        var wobblePhase = Math.random() * Math.PI * 2;
        a.body.updateTarget = function (b, tSec) {
          var t = tSec - t0;
          var progress = Math.min(t / durationSec, 1);
          var angle = phase0 + progress * turns * Math.PI * 2 * omegaJitter;
          var r = radius * radiusJitter * (1 + 0.07 * Math.sin(t * 2.6 + wobblePhase));
          b.targetX = ctx.gatherDX(a) + Math.cos(angle) * r;
          b.targetY = ctx.gatherDY(a) + Math.sin(angle) * r;
        };
      });
      if (ctx.reduced) {
        ctx.actors.forEach(function (a) { a.body.updateTarget = null; });
        settleNow(ctx.actors.map(function (a) { return a.body; }));
        return Promise.resolve();
      }
      return waitUntil(function () { return performance.now() / 1000 - t0 >= durationSec; }, durationSec * 1000 + 200)
        .then(function () { ctx.actors.forEach(function (a) { a.body.updateTarget = null; }); });
    },

    scatter: function (ctx, args) {
      if (!ctx.actors.length) return Promise.resolve();
      var radius = args.radius != null ? Number(args.radius) : 90;
      ctx.announce("Scattering " + ctx.foundPhrases.join(", ") + ".");
      ctx.actors.forEach(function (a) {
        var angle = Math.random() * Math.PI * 2;
        var r = radius * (0.6 + Math.random() * 0.4);
        a.body.targetX = ctx.gatherDX(a) + Math.cos(angle) * r;
        a.body.targetY = ctx.gatherDY(a) + Math.sin(angle) * r;
      });
      if (ctx.reduced) { settleNow(ctx.actors.map(function (a) { return a.body; })); return Promise.resolve(); }
      return waitUntil(function () { return ctx.actors.every(function (a) { return settled(a.body, 1.2, 8); }); }, 900);
    },

    converge: function (ctx) {
      if (!ctx.actors.length) return Promise.resolve();
      ctx.announce("Converging " + ctx.foundPhrases.join(", ") + ".");
      ctx.actors.forEach(function (a) {
        a.body.targetX = ctx.gatherDX(a);
        a.body.targetY = ctx.gatherDY(a);
      });
      if (ctx.reduced) { settleNow(ctx.actors.map(function (a) { return a.body; })); return Promise.resolve(); }
      return waitUntil(function () { return ctx.actors.every(function (a) { return settled(a.body, 0.8, 6); }); }, 700);
    },

    shed: function (ctx, args) {
      if (!ctx.actors.length) return Promise.resolve();
      var fraction = args.fraction != null ? Number(args.fraction) : 0.35;
      ctx.announce("Weakening and shedding irrelevant fragments.");
      var fragments = [];
      ctx.actors.forEach(function (a) {
        var chars = a.el.querySelectorAll(".metamorphosis-char");
        chars.forEach(function (ch) {
          if (Math.random() < fraction) {
            var fb = makeBody({ mass: 0.5, k: 90, damping: 9 });
            var angle = Math.random() * Math.PI * 2;
            fb.vx = Math.cos(angle) * 90;
            fb.vy = Math.sin(angle) * 90 - 30;
            fb.targetX = Math.cos(angle) * 60;
            fb.targetY = Math.sin(angle) * 60;
            fb.targetScale = 0;
            fb.targetOpacity = 0;
            fb.vrot = (Math.random() - 0.5) * 240;
            fb.targetRot = fb.vrot * 0.4;
            fb.onFrame = function () {
              ch.style.transform = "translate(" + fb.x + "px," + fb.y + "px) rotate(" + fb.rot + "deg) scale(" + fb.scale + ")";
              ch.style.opacity = String(Math.max(0, fb.opacity));
            };
            ctx.sim.add(fb);
            fragments.push(fb);
          } else {
            ch.animate(
              [{ transform: "scale(1)" }, { transform: "scale(1.18)" }, { transform: "scale(1)" }],
              { duration: 260, easing: "ease-in-out" }
            );
          }
        });
      });
      if (ctx.reduced) {
        fragments.forEach(function (fb) { ctx.sim.remove(fb); });
        ctx.actors.forEach(function (a) {
          a.el.querySelectorAll(".metamorphosis-char").forEach(function (ch) { ch.style.opacity = "1"; ch.style.transform = ""; });
        });
        return Promise.resolve();
      }
      return waitUntil(function () { return fragments.every(function (fb) { return fb.opacity < 0.05; }); }, 650)
        .then(function () { fragments.forEach(function (fb) { ctx.sim.remove(fb); }); });
    },

    morph: function (ctx, args) {
      if (!ctx.actors.length) return Promise.resolve();
      var to = args.to != null ? String(args.to) : ctx.resultText;
      ctx.announce("Transforming into: " + to + ".");
      var survivor = ctx.actors[0];
      // extra actors beyond the first fold into the survivor silently --
      // morph is a single-body operation.
      ctx.actors.slice(1).forEach(function (a) { ctx.sim.remove(a.body); a.el.remove(); });
      ctx.actors = [survivor];
      var b = survivor.body;
      b.targetScale = 0.72;
      var doMorphAt = performance.now() + (ctx.reduced ? 0 : 130);
      return (ctx.reduced ? Promise.resolve() : waitUntil(function () { return performance.now() >= doMorphAt; }, 400))
        .then(function () {
          buildCharSpans(survivor.el, to);
          survivor.text = to;
          b.targetScale = 1;
          if (ctx.reduced) { settleNow([b]); return; }
          return waitUntil(function () { return settled(b, 0.8, 6); }, 500);
        });
    },

    merge: function (ctx, args) {
      if (ctx.actors.length < 1) return Promise.resolve();
      var into = args.into != null ? String(args.into) : ctx.resultText;
      ctx.announce("Merging into: " + into + ".");
      ctx.actors.forEach(function (a) { a.body.targetX = ctx.gatherDX(a); a.body.targetY = ctx.gatherDY(a); });
      var settleP = ctx.reduced
        ? (settleNow(ctx.actors.map(function (a) { return a.body; })), Promise.resolve())
        : waitUntil(function () { return ctx.actors.every(function (a) { return settled(a.body, 1.2, 8); }); }, 700);
      return settleP.then(function () {
        var survivor = ctx.actors[0];
        var meanVx = ctx.actors.reduce(function (s, a) { return s + a.body.vx; }, 0) / ctx.actors.length;
        var meanVy = ctx.actors.reduce(function (s, a) { return s + a.body.vy; }, 0) / ctx.actors.length;
        ctx.actors.slice(1).forEach(function (a) { ctx.sim.remove(a.body); a.el.remove(); });
        buildCharSpans(survivor.el, into);
        survivor.text = into;
        survivor.body.vx = meanVx; survivor.body.vy = meanVy; // follow-through
        survivor.body.targetScale = 1.2;
        ctx.actors = [survivor];
        if (ctx.reduced) { settleNow([survivor.body]); return; }
        return waitUntil(function () { return settled(survivor.body, 0.8, 6); }, 500)
          .then(function () { survivor.body.targetScale = 1; return waitUntil(function () { return settled(survivor.body, 0.8, 6); }, 400); });
      });
    },

    pulse: function (ctx, args) {
      if (!ctx.actors.length) return Promise.resolve();
      var strength = args.strength != null ? Number(args.strength) : 0.25;
      var count = args.count != null ? Number(args.count) : 1;
      ctx.announce("Pulsing.");
      var i = 0;
      function beat() {
        ctx.actors.forEach(function (a) { a.body.vscale += strength; a.body.vbrightness += strength * 2.2; });
        i++;
        if (ctx.reduced) return Promise.resolve();
        return waitUntil(function () { return true; }, 0).then(function () {
          return new Promise(function (r) { setTimeout(r, 170); });
        }).then(function () { if (i < count) return beat(); });
      }
      return beat();
    },

    crystallize: function (ctx, args) {
      if (!ctx.actors.length) return Promise.resolve();
      var glyph = args.glyph != null ? String(args.glyph) : "◆";
      var survivor = ctx.actors[ctx.actors.length - 1];
      ctx.announce("Crystallizing as " + glyph + ".");
      buildCharSpans(survivor.el, survivor.text + " " + glyph);
      survivor.text = survivor.text + " " + glyph;
      survivor.body.vscale += 0.5;
      survivor.body.vbrightness += 1.4;
      if (ctx.reduced) { settleNow([survivor.body]); return Promise.resolve(); }
      return waitUntil(function () { return settled(survivor.body, 0.8, 6); }, 450);
    },

    trail: function (ctx, args) {
      ctx.trailEnabled = args.on !== false && args.on !== 0 && args.on !== "off";
      return Promise.resolve();
    },

    land: function (ctx) {
      if (!ctx.landTarget) return Promise.resolve();
      // Guarantee a single clean survivor lands even if the chain never
      // explicitly merged (protects the no-leftover-DOM contract). If no
      // step ever set a result text either, fall back to joining the
      // found phrases rather than landing a blank, anticlimactic marker.
      var mergeText = ctx.resultText || ctx.foundPhrases.join(" ");
      var landPromise = ctx.actors.length > 1 ? PRIMITIVES.merge(ctx, { into: mergeText }) : Promise.resolve();
      return landPromise.then(function () {
        if (!ctx.actors.length) return;
        var survivor = ctx.actors[0];
        var landRect = ctx.landTarget.getBoundingClientRect();
        var r = survivor.el.getBoundingClientRect();
        survivor.body.targetX = survivor.body.x + (landRect.left + landRect.width / 2 - r.left - r.width / 2);
        survivor.body.targetY = survivor.body.y + (landRect.top + landRect.height / 2 - r.top - r.height / 2);
        ctx.announce("Landing beside " + ctx.landGlyph + ".");
        var finish = function () {
          var resultNode = document.createElement("span");
          resultNode.className = "metamorphosis-result";
          resultNode.textContent = survivor.text;
          ctx.landTarget.appendChild(resultNode);
          ctx.sim.remove(survivor.body);
          survivor.el.remove();
          ctx.actors = [];
        };
        if (ctx.reduced) { settleNow([survivor.body]); finish(); return; }
        return waitUntil(function () { return settled(survivor.body, 0.8, 6); }, 700).then(finish);
      });
    },
  };

  /**
   * steps: Array<{ op: string, args?: object }>
   * opts: {
   *   sourceContainer: Element,
   *   phrases: string[],           // used by the implicit "lift" first step
   *   resultText: string,          // fallback text for morph/merge/land if a step omits its own
   *   anchorGlyph?: string ('⟰'),
   *   landTarget: Element,
   *   landGlyph?: string ('⚓'),
   *   reducedMotion?: 'auto'|'force'|'off'
   * }
   * returns { cancel(): void, done: Promise<ExecutionResult> }
   */
  SemanticMetamorphosis.prototype.run = function (steps, opts) {
    if (this._busy) {
      return { cancel: function () {}, done: Promise.reject(new Error("metamorphosis already in progress")) };
    }
    this._busy = true;
    var self = this;
    var start = performance.now();
    var reduced = opts.reducedMotion === "force" ? true : opts.reducedMotion === "off" ? false : prefersReducedMotion();

    var gatherRect = opts.sourceContainer.getBoundingClientRect();
    var gatherX = window.innerWidth / 2, gatherY = Math.max(80, gatherRect.top - 40);

    var ctx = {
      sourceContainer: opts.sourceContainer,
      resultText: opts.resultText || "",
      anchorGlyph: opts.anchorGlyph || "⟰",
      landGlyph: opts.landGlyph || "⚓",
      landTarget: opts.landTarget,
      overlay: self._overlay,
      sim: new Simulation(),
      actors: [],
      foundPhrases: [],
      restoreFns: [],
      trailEnabled: false,
      reduced: reduced,
      cancelled: false,
      gatherX: gatherX,
      gatherY: gatherY,
      announce: function (t) { self._announce(t); },
      gatherDX: function (a) { return gatherX - a.rect.left - a.rect.width / 2; },
      gatherDY: function (a) { return gatherY - a.rect.top - a.rect.height / 2; },
    };
    self._ctx = ctx;
    ctx.sim.start();

    var stepsRun = [];
    var donePromise = new Promise(function (resolve) {
      self._pending = { foundPhrases: [], stepsRun: stepsRun, start: start, resolveDone: resolve };

      var chain = Promise.resolve();
      var normalizedSteps = [{ op: "lift", args: { phrases: opts.phrases || [] } }].concat(steps || []);
      normalizedSteps.forEach(function (step) {
        chain = chain.then(function () {
          if (ctx.cancelled) return;
          var fn = PRIMITIVES[step.op];
          if (!fn) return;
          stepsRun.push(step.op);
          self._pending.foundPhrases = ctx.foundPhrases;
          return fn(ctx, step.args || {});
        });
      });

      chain.then(function () {
        if (ctx.cancelled) return; // cancel() already resolved .done
        ctx.sim.stop();
        ctx.actors.forEach(function (a) { a.el.remove(); });
        ctx.restoreFns.forEach(function (fn) { try { fn(); } catch (e) {} });
        var durationMs = Math.round(performance.now() - start);
        var accessibleDescription = "Metamorphosis of " + ctx.foundPhrases.join(", ") + " complete via " + stepsRun.join(" → ") + ".";
        self._announce(accessibleDescription);
        self._pending = null;
        self._ctx = null;
        self._busy = false;
        resolve({
          cancelled: false,
          sourcePhrases: ctx.foundPhrases,
          stepsRun: stepsRun,
          resultText: ctx.resultText,
          durationMs: durationMs,
          accessibleDescription: accessibleDescription,
          timestamp: new Date().toISOString(),
        });
      }).catch(function () {
        // cancel() already resolved .done with a cancelled result.
      });
    });

    return { cancel: this.cancel.bind(this), done: donePromise };
  };

  // Backward-compatible sugar: the original fixed five-phase sequence,
  // expressed as a step chain over the new engine. Existing callers using
  // `perform(spec)` (and the `⟦metamorphose: ...⟧` trigger tag) keep working
  // unchanged.
  SemanticMetamorphosis.prototype.perform = function (spec) {
    return this.run(
      [
        { op: "orbit", args: { turns: 1 } },
        { op: "shed", args: { fraction: 0.4 } },
        { op: "morph", args: { to: spec.resultText } },
        { op: "crystallize", args: { glyph: spec.resultGlyph || "◆" } },
        { op: "land", args: {} },
      ],
      {
        sourceContainer: spec.sourceContainer,
        phrases: spec.phrases,
        resultText: spec.resultText,
        anchorGlyph: spec.anchorGlyph,
        landTarget: spec.landTarget,
        landGlyph: spec.landGlyph,
        reducedMotion: spec.reducedMotion,
      }
    );
  };

  SemanticMetamorphosis.capabilityCard = {
    id: "semantic-text-metamorphosis",
    version: "0.2",
    kind: "expressive-ui-capability",
    summary:
      "Lift phrases out of the Captain's own rendered text and choreograph them through a physics-simulated (not keyframed) sequence of composable primitives -- orbit, scatter, converge, shed, morph, merge, pulse, crystallize, trail, land -- ending in a synthesized result landing permanently near an anchor.",
    whenToUse: [
      "Synthesizing 2-4 related concepts already visible in recent conversation into one crystallized insight.",
      "Expressive emphasis moments, not routine responses -- this is a deliberate rhetorical/visual act, not default UI behavior.",
      "When the result text for morph/merge/crystallize/land is already decided -- this capability does not generate or infer the synthesis itself.",
    ],
    whenNotToUse: [
      "Do not use for content the Captain hasn't already decided on -- result text is always a required input, never computed here.",
      "Do not use more than once in quick succession -- it is a deliberate emphasis device; overuse dilutes it.",
    ],
    invocation: {
      method: "SemanticMetamorphosis#run(steps, opts)",
      primitives: {
        lift: "implicit first step; args: { phrases: string[] }",
        orbit: "args: { turns?: number=1, radius?: number=54 } -- bodies spring-chase a continuously-advancing point on a circle, per-body phase/speed/radius jitter",
        scatter: "args: { radius?: number=90 } -- each body springs to an independent random point",
        converge: "args: {} -- all bodies spring toward the shared anchor point",
        shed: "args: { fraction?: number=0.35 } -- that fraction of characters fly off as independent impulse-driven fragments and fade",
        morph: "args: { to: string } -- the (single) actor's text is swapped mid-transition, body continuity preserved",
        merge: "args: { into: string } -- all actors converge and combine into one new actor carrying the group's mean velocity",
        pulse: "args: { strength?: number=0.25, count?: number=1 } -- scale/brightness impulse, springs back",
        crystallize: "args: { glyph?: string='◆' } -- appends the glyph with a stronger pulse",
        trail: "args: { on?: boolean=true } -- toggles fading motion-trail ghosts on subsequent steps",
        land: "args: {} -- (auto-merges if >1 actor remains) settles onto landTarget and becomes a permanent plain DOM node",
      },
      opts: {
        sourceContainer: "Element -- contains the rendered text the source phrases will be located within",
        phrases: "string[] -- 1-6 phrases to locate (case-insensitive, first match each) and lift out",
        resultText: "string -- fallback synthesized text for steps that don't specify their own",
        anchorGlyph: "string, default '⟰'",
        landTarget: "Element -- where the final result is permanently inserted",
        landGlyph: "string, default '⚓'",
        reducedMotion: "'auto'|'force'|'off', default 'auto'",
      },
      returns: "{ cancel(): void, done: Promise<ExecutionResult> }",
      legacyMethod: "SemanticMetamorphosis#perform(spec) -- sugar for orbit→shed→morph→crystallize→land, unchanged signature",
    },
    executionResult: {
      cancelled: "boolean",
      sourcePhrases: "string[]",
      stepsRun: "string[]",
      resultText: "string",
      durationMs: "number",
      accessibleDescription: "string",
      timestamp: "ISO 8601 string",
    },
    example: {
      phrases: ["confusion", "recursion", "evidence"],
      steps: [
        { op: "orbit", args: { turns: 1.5 } },
        { op: "shed", args: { fraction: 0.4 } },
        { op: "morph", args: { to: "testable recursive hypothesis" } },
        { op: "crystallize", args: { glyph: "◆" } },
        { op: "land", args: {} },
      ],
    },
  };

  global.SemanticMetamorphosis = SemanticMetamorphosis;
})(window);
