/**
 * Moonbase Architect v0.1
 * Lightweight Browser-Local Telemetry & Instrumentation (No External Infrastructure)
 * 
 * Stored locally in browser localStorage for developer review & test analysis.
 */

const STORAGE_KEY = 'monad_moonbase_telemetry_v01';

export class MoonbaseTelemetry {
  constructor() {
    this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    this.startTime = Date.now();
    this.events = [];
    this.initSession();
  }

  initSession() {
    this.recordEvent('session_started', {
      userAgent: navigator.userAgent,
      screen: `${window.innerWidth}x${window.innerHeight}`
    });
  }

  recordEvent(eventType, payload = {}) {
    const elapsedSeconds = ((Date.now() - this.startTime) / 1000).toFixed(1);
    const entry = {
      sessionId: this.sessionId,
      eventType,
      elapsedSeconds: parseFloat(elapsedSeconds),
      timestamp: new Date().toISOString(),
      ...payload
    };

    this.events.push(entry);
    this.persist();
    return entry;
  }

  recordDimensionAttempt(missionId, width, length, area, perimeter) {
    return this.recordEvent('dimensions_attempted', {
      missionId,
      width,
      length,
      area,
      perimeter
    });
  }

  recordSolution(missionId, width, length, isRecord = false) {
    return this.recordEvent('valid_solution_reached', {
      missionId,
      width,
      length,
      pair: `${Math.min(width, length)}x${Math.max(width, length)}`,
      isRecord
    });
  }

  recordHint() {
    return this.recordEvent('hint_requested');
  }

  recordReset(missionId) {
    return this.recordEvent('mission_reset', { missionId });
  }

  persist() {
    try {
      const summary = {
        sessionId: this.sessionId,
        startTime: this.startTime,
        eventCount: this.events.length,
        events: this.events
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(summary));
    } catch (e) {
      console.warn('Telemetry storage unavailable', e);
    }
  }

  getLogs() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : { events: this.events };
    } catch (e) {
      return { events: this.events };
    }
  }

  clearLogs() {
    this.events = [];
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {}
  }
}
