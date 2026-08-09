#!/usr/bin/env python3
"""
Project Monad: Canonical Public Command & Control Viewer
Live execution engine with human verification gate and real-time telemetry.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import math
import sys

app = FastAPI(title="Project Monad: Captain-Level Execution Engine", version="1.0.0")

# CORS for loopback-only; Caddy handles public-domain proxying
app.add_middleware(
    CORSMiddleware,
    allow_origins=["127.0.0.1", "localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PipelineState(BaseModel):
    examine_val: float
    select_val: float
    operate_intensity: float
    human_override: bool

class ExecutionResult(BaseModel):
    status: str
    phase_space_distance: float
    codomain_phi: float
    gate_integrity: str

@app.post("/api/execute", response_model=ExecutionResult)
def execute_monad_pipeline(state: PipelineState):
    """
    Core Formalism Evaluation: E: X × Σ → Φ
    Non-linear phase space mapping with strict human verification gate.
    """
    x_sigma = state.examine_val * state.select_val
    eval_transform = math.sin(x_sigma) * state.operate_intensity

    if not state.human_override:
        return ExecutionResult(
            status="HALTED_BY_POLICY",
            phase_space_distance=round(eval_transform, 4),
            codomain_phi=0.0,
            gate_integrity="FAILED: Strict Human Verification Gate Intercept Required"
        )

    phi_output = eval_transform * math.e ** (-abs(x_sigma) / 10.0)

    return ExecutionResult(
        status="VERIFIED_SUCCESS",
        phase_space_distance=round(eval_transform, 4),
        codomain_phi=round(phi_output, 4),
        gate_integrity="PASSED: Human-in-the-Loop Override Confirmed"
    )

@app.get("/", response_class=HTMLResponse)
def canonical_public_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Monad | Public Command & Control Viewer</title>
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-secondary: #111827;
            --bg-tertiary: #030712;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --text-tertiary: #d1d5db;
            --border-primary: #1f2937;
            --border-secondary: #374151;
            --accent-primary: #38bdf8;
            --accent-secondary: #0284c7;
            --accent-hover: #0369a1;
            --success: #34d399;
            --error: #f43f5e;
        }

        * {
            box-sizing: border-box;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
        }

        h1 {
            color: var(--accent-primary);
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            margin-top: 0;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 1rem;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            width: 100%;
            max-width: 1200px;
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-primary);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .card h2 {
            margin-top: 0;
            font-size: 1.25rem;
            color: var(--text-tertiary);
            border-bottom: 1px solid var(--border-secondary);
            padding-bottom: 0.5rem;
        }

        .form-group {
            margin-bottom: 1rem;
        }

        label {
            display: block;
            font-size: 0.875rem;
            color: var(--text-tertiary);
            margin-bottom: 0.25rem;
        }

        input, select {
            width: 100%;
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-secondary);
            border-radius: 6px;
            color: var(--text-primary);
            font-family: inherit;
        }

        input:focus, select:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.1);
        }

        button {
            background: var(--accent-secondary);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            transition: background 0.2s;
        }

        button:hover {
            background: var(--accent-hover);
        }

        button:active {
            transform: scale(0.98);
        }

        pre {
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            color: var(--success);
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            border: 1px solid var(--border-primary);
        }

        .formula {
            text-align: center;
            font-size: 1.5rem;
            color: var(--error);
            margin: 1rem 0;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin: 0;
        }

        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }
            h1 {
                font-size: 1.8rem;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>Project Monad: Command & Control</h1>
        <div class="subtitle">Captain-Level Canonical Public View Interface</div>
    </header>

    <div class="container">
        <div class="card">
            <h2>Pipeline Parameters</h2>
            <div class="formula">E: X × Σ → Φ</div>
            <div class="form-group">
                <label for="examine">Examine Factor (X)</label>
                <input type="number" id="examine" value="4.5" step="0.1" min="-10" max="10">
            </div>
            <div class="form-group">
                <label for="select">Select Weight (Σ)</label>
                <input type="number" id="select" value="2.0" step="0.1" min="-10" max="10">
            </div>
            <div class="form-group">
                <label for="operate">Operate Intensity</label>
                <input type="number" id="operate" value="1.0" step="0.1" min="0" max="5">
            </div>
            <div class="form-group">
                <label class="checkbox-group">
                    <input type="checkbox" id="override" checked>
                    <span>Strict Human Verification Gate Override (Active Authorization)</span>
                </label>
            </div>
            <button onclick="runPipeline()">Execute Pipeline Pass</button>
        </div>

        <div class="card">
            <h2>Live Telemetry Viewer</h2>
            <p>Execution state output and mapping logs:</p>
            <pre id="output">System initialized. Awaiting pipeline execution trigger...</pre>
        </div>
    </div>

    <script>
        async function runPipeline() {
            const data = {
                examine_val: parseFloat(document.getElementById('examine').value),
                select_val: parseFloat(document.getElementById('select').value),
                operate_intensity: parseFloat(document.getElementById('operate').value),
                human_override: document.getElementById('override').checked
            };

            try {
                const response = await fetch('/api/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const result = await response.json();
                document.getElementById('output').innerText = JSON.stringify(result, null, 2);
            } catch (err) {
                document.getElementById('output').innerText = "Execution Error: " + err.message;
                console.error(err);
            }
        }
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    import uvicorn

    # Bind to loopback only; Caddy handles public proxying
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4775

    uvicorn.run(app, host=host, port=port, log_level="info")
