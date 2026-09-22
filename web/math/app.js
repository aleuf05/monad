import { MoonbaseMathEngine, MISSIONS, EM_STAGES } from './engine.js';
import { MoonbaseCanvasRenderer } from './renderer.js';
import { MoonbaseAudio } from './sound.js';
import { MoonbaseTelemetry } from './telemetry.js';

class MoonbaseApp {
  constructor() {
    this.engine = new MoonbaseMathEngine(); this.audio = new MoonbaseAudio(); this.telemetry = new MoonbaseTelemetry();
    this.canvas = document.getElementById('lunarCanvas'); this.renderer = new MoonbaseCanvasRenderer(this.canvas, this.engine); this.lastCelebrated = false;
    this.renderTabs(); this.bind(); this.refresh(); this.loop();
  }
  renderTabs() { document.getElementById('missionRibbon').innerHTML = MISSIONS.map((m, i) => `<button class="mission-tab ${i === this.engine.currentMissionIndex ? 'active' : ''}" data-i="${i}">${m.title}</button>`).join(''); }
  refresh(message = null) {
    const c = this.engine.getCalculations(); const m = c.mission;
    const isEM = m.type === 'electromagnetism';
    document.getElementById('lunarCanvas').closest('.canvas-wrap').hidden = isEM;
    document.getElementById('plotLabel').textContent = isEM ? 'Prediction → experiment → explanation' : 'Live mathematical object';
    document.getElementById('emLesson').hidden = !isEM;
    document.getElementById('promptTitle').textContent = m.prompt; document.getElementById('promptSub').textContent = m.subtext;
    document.getElementById('valWidth').textContent = c.width.toFixed(1); document.getElementById('valLength').textContent = c.length.toFixed(1);
    document.getElementById('sliderWidth').value = c.width; document.getElementById('sliderLength').value = c.length;
    const labels = [['ipStateLabel', c.stateLabel], ['ipFunctionLabel', c.functionLabel], ['ipDerivativeLabel', c.derivativeLabel], ['ipCheckLabel', 'CHECK']]; labels.forEach(([id, text]) => document.getElementById(id).textContent = text);
    [['ipStateFormula', c.stateFormula], ['ipState', c.stateFormula], ['ipFunctionFormula', c.functionFormula], ['ipFunction', c.functionValue], ['ipFunctionSub', c.functionSub], ['ipDerivativeFormula', c.derivativeFormula], ['ipDerivative', c.derivativeValue], ['ipDerivativeSub', c.derivativeSub], ['ipCheck', c.check], ['ipCheckSub', c.checkSub]].forEach(([id, text]) => document.getElementById(id).textContent = text);
    document.getElementById('maraSpeech').textContent = message || this.engine.evaluateMaraReaction(c);
    const actions = document.getElementById('assessmentActions');
    actions.innerHTML = c.assessment ? c.probe.options.map(option => `<button class="btn assessment-choice" data-answer="${option}">${option}</button>`).join('') : '';
    const badge = document.getElementById('promptBadge'); badge.hidden = !c.missionPassed; if (c.missionPassed) badge.textContent = '✓ INSIGHT LOCKED';
    document.getElementById('stampsList').innerHTML = c.insights.length ? c.insights.map(i => `<span class="factor-stamp">${i}</span>`).join('') : '<span style="color:#6B7C93;font-size:10px">Make a prediction, then earn a durable insight.</span>';
    if (isEM) this.refreshEM(c);
    this.renderer.notifyDimensionChange(); this.telemetry.recordDimensionAttempt(m.id, c.width, c.length, c.functionValue, c.derivativeValue);
    if (c.missionPassed && !this.lastCelebrated) { this.audio.playSuccess(); this.renderer.triggerCelebration(); this.lastCelebrated = true; } if (!c.missionPassed) this.lastCelebrated = false;
  }
  refreshEM(c) {
    const stage = c.emStage;
    document.getElementById('emStageCount').textContent = `STAGE ${c.emStageNumber + 1} / ${EM_STAGES.length}`;
    document.getElementById('emStageTitle').textContent = stage.title;
    document.getElementById('emStageBody').textContent = stage.body;
    document.getElementById('emStageFormula').textContent = stage.formula;
    document.getElementById('emStageNote').textContent = stage.note;
    document.getElementById('emRevealText').textContent = stage.explanation;
    document.getElementById('emRevealText').hidden = !this.emRevealed;
    document.getElementById('emReveal').textContent = this.emRevealed ? 'Explanation revealed' : 'Reveal explanation';
    document.getElementById('emPrev').disabled = c.emStageNumber === 0;
    document.getElementById('emNext').disabled = c.emStageNumber === EM_STAGES.length - 1;
    document.getElementById('emBench').hidden = !['flyback', 'drive', 'switch'].includes(stage.id);
  }
  change(fn) { const r = fn(); if (r.changed) { this.audio.playStep(); this.refresh(r.maraReaction); } }
  bind() {
    document.getElementById('missionRibbon').addEventListener('click', e => { const tab = e.target.closest('.mission-tab'); if (!tab) return; this.engine.currentMissionIndex = Number(tab.dataset.i); this.lastCelebrated = false; this.emRevealed = false; if (this.engine.getCurrentMission().type === 'electromagnetism') this.engine.width = 0; this.renderTabs(); this.refresh(); this.audio.playClick(); });
    document.getElementById('btnResetMission').addEventListener('click', () => { this.engine.width = 1; this.engine.length = 1; this.engine.insights.clear(); this.lastCelebrated = false; this.refresh('“Reset. Start by making a prediction you can defend.”'); });
    document.getElementById('btnWidthDec').addEventListener('click', () => this.change(() => this.engine.setWidth(this.engine.width - 0.1)));
    document.getElementById('btnWidthInc').addEventListener('click', () => this.change(() => this.engine.setWidth(this.engine.width + 0.1)));
    document.getElementById('btnLengthDec').addEventListener('click', () => this.change(() => this.engine.setLength(this.engine.length - 0.1)));
    document.getElementById('btnLengthInc').addEventListener('click', () => this.change(() => this.engine.setLength(this.engine.length + 0.1)));
    document.getElementById('sliderWidth').addEventListener('input', e => this.change(() => this.engine.setWidth(e.target.value)));
    document.getElementById('sliderLength').addEventListener('input', e => this.change(() => this.engine.setLength(e.target.value)));
    document.getElementById('btnMute').addEventListener('click', e => { this.audio.isMuted = !this.audio.isMuted; e.currentTarget.textContent = this.audio.isMuted ? '🔇 Sound Off' : '🔊 Sound On'; });
    document.getElementById('btnTelemetry').addEventListener('click', () => alert(JSON.stringify(this.telemetry.getLogs(), null, 2)));
    document.getElementById('assessmentActions').addEventListener('click', e => { const button = e.target.closest('.assessment-choice'); if (!button) return; const c = this.engine.getCalculations(); const right = button.dataset.answer === c.probe.answer; this.refresh(right ? `“Correct. ${c.probe.explanation} Now move the toy and make the idea quantitative.”` : `“Not quite. ${c.probe.explanation} That mismatch is exactly what we are here to repair.”`); });
    document.getElementById('emReveal').addEventListener('click', () => { this.emRevealed = true; this.refresh(); });
    document.getElementById('emPrev').addEventListener('click', () => { this.emRevealed = false; const stage = this.engine.getCalculations().emStageNumber; this.change(() => this.engine.setWidth(stage - 1)); });
    document.getElementById('emNext').addEventListener('click', () => { this.emRevealed = false; const stage = this.engine.getCalculations().emStageNumber; this.change(() => this.engine.setWidth(stage + 1)); });
  }
  loop(t = performance.now()) { this.renderer.render(t); requestAnimationFrame(x => this.loop(x)); }
}
document.addEventListener('DOMContentLoaded', () => { window.moonbaseApp = new MoonbaseApp(); });
