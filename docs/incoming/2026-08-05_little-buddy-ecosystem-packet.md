# CAPTURE — Master Strategic Directive: The Little Buddy Ecosystem Packet

**Captured:** 2026-08-05
**Source:** Admiral, direct paste.
**Status:** **Staged, not filed.** Captured verbatim on arrival per the
standing rule. No evaluation applied to the content below.

**Admiral's live amendment, same session:** *"hardware stuff low prio."*
Section 2A and Milestone 1 are therefore deprioritised by direct
instruction — recorded here so the packet and the amendment stay together.

---

## Verbatim content as received

```
======================================================================
  [ MASTER STRATEGIC DIRECTIVE: THE LITTLE BUDDY ECOSYSTEM PACKET ]
======================================================================

  * CLASSIFICATION: EXECUTIVE STRATEGIC SPECIFICATION
  * TARGET SUBSYSTEM: EDGE VOICE & HARDWARE EMULATION ("LITTLE BUDDY")
  * SCOPE: FULL ARCHITECTURAL BLUEPRINT (TECH LEAD EXECUTION TIER)
  * AUTHORIZATION: CHIEF COMMAND (ACTIVE)

======================================================================
```

### 1. Executive Summary & Core Objective

The objective of this packet is to transition the "Little Buddy" vocal subsystem from theoretical architecture to an engineered, modular reality. The strategy avoids premature micro-coding, instead providing explicit architectural boundaries, interface contracts, and functional requirements. This leaves the technical lead full autonomy to design the underlying implementation while guaranteeing strict interoperability across hardware, edge software, and control dashboards.

---

### 2. System Architecture & Component Boundaries

The Little Buddy ecosystem is divided into three distinct operational tiers. Each tier must maintain decoupled interfaces via defined inter-process communication (IPC) and hardware protocols.

#### A. The Hardware & Audio Layer (Edge Interface)

* **Design Mandate**: Secure, low-latency analog/digital conversion and clean signal routing on local microcontrollers.
* **Tech Lead Requirements**:
* **Microcontroller Selection**: Standardize around an ESP32 or Raspberry Pi Pico W architecture capable of handling I2S/PWM audio protocols.
* **DAC & Amplification**: Integrate an external I2S DAC (such as the PCM5102A series) to bypass noisy onboard PWM generation and ensure a clean signal-to-noise ratio.
* **Power & Isolation**: Enforce separate analog and digital ground planes where feasible, utilizing appropriate decoupling capacitors to eliminate ground loops and digital switching noise on the audio output stage.

#### B. The Software Pipeline & Synthesis Engine

* **Design Mandate**: Bridge system telemetry, agent dialogue, and text inputs into a continuous, low-latency audio stream without buffer starvation.
* **Tech Lead Requirements**:
* **Ingestion Bus**: Establish a lightweight messaging or IPC socket architecture (e.g., local WebSockets, Unix domain sockets, or MQTT) to ingest strings from the active command rig.
* **Synthesis Abstraction**: Design a modular TTS wrapper that can toggle between cloud-backed high-fidelity neural voices and local edge-quantized fallback models (INT8/INT4 footprints).
* **Buffering & Flow Control**: Implement a ring-buffer mechanism on the client audio handler to gracefully manage network jitter or processing spikes, preventing audio stuttering or buffer underruns.

#### C. The Live Integration & Telemetry Bus

* **Design Mandate**: Bind the vocal output engine directly to the operational dashboard and system event logs.
* **Tech Lead Requirements**:
* **Event Prioritization & Ducking**: Create a priority queue for audio triggers. Critical system faults or emergency overrides must instantly interrupt or "duck" routine telemetry readouts.
* **Bi-Directional Command Loop**: Define the protocol for future voice input (microphone parsing to intent classification), ensuring the audio layer can feed structured commands back into the command buffer safely.

---

### 3. Interface Contracts & Specifications

To ensure the tech lead can execute without ambiguity, the following structural boundaries and data contracts are established:

* **Payload Structure**: All incoming text packets destined for vocalization must conform to a standardized JSON schema containing:
* `timestamp`: Epoch integer for sequence ordering.
* `priority_level`: Integer scale (e.g., 0 for ambient status, 10 for critical alerts).
* `text_payload`: UTF-8 string to be synthesized.

* **Audio Handshake**: The audio routing subsystem must acknowledge receipt of a payload with a status code (`READY`, `BUFFERING`, `DROPPED_QUEUE_FULL`) before execution.
* **Fallback Protocol**: If the primary synthesis endpoint fails to respond within a defined timeout threshold (e.g., 800ms), the system must automatically failover to the local edge synthesizer without requiring manual intervention or crashing the event bus.

---

### 4. Code Example (Reference Clarity Only)

*The following pseudo-code structure illustrates the expected event loop pattern for the IPC ingestion and buffer handler. Tech lead may adapt language and framework implementation as needed.*

```python
# Reference Pattern: Event Loop & Buffer Management
class AudioPipelineRouter:
    def __init__(self, dac_driver, tts_client):
        self.dac = dac_driver
        self.tts = tts_client
        self.priority_queue = PriorityQueue()

    def handle_incoming_event(self, event_payload):
        # Enforce priority and ducking rules
        self.priority_queue.put((event_payload['priority'], event_payload['text']))
        self.process_queue()

    def process_queue(self):
        while not self.priority_queue.empty():
            priority, text = self.priority_queue.get()
            audio_stream = self.tts.synthesize(text)
            self.dac.stream_buffer(audio_stream)
```

---

### 5. Execution Roadmap for Tech Lead

1. **Milestone 1 (Bench PoC)**: Breadboard the microcontroller and I2S DAC. Validate manual 1kHz tone generation and clean waveform output.
2. **Milestone 2 (Pipeline Wrapper)**: Deploy the local IPC socket wrapper and connect a basic text-to-speech engine to the hardware output.
3. **Milestone 3 (Dashboard Hook)**: Integrate the priority queue with the system log event bus, verifying that routine alerts voice cleanly without buffer clipping.

```
======================================================================
  [ PACKET STATUS: FULLY SPECIFIED & LOCKED FOR EXECUTION ]
======================================================================
```

---

## Capture notes — not part of the packet

Recorded at capture time so the organising pass does not re-derive them.
These are observations about *fit against the repository*, not judgements
about the design, which is competent.

### A voice engine already exists and the packet does not know about it

`tools/voice-engine/` is the **Monad Rich Voice Engine** — "backend-only,
cache-first Gemini TTS tier behind Character Voice Studio", with
`rich_voice.py`, `server.py`, `evaluation.py` and three test files. Its unit
is `scripts/rich-voice.service`, currently **inactive**.

It already implements a substantial part of §2B's "Synthesis Abstraction",
and it carries something the packet does not mention at all: **a cost
boundary.** From its README —

- `GET /status`, `GET /budget`, `POST /estimate` never call Gemini
- `POST /render` checks an immutable artifact cache before reserving budget
- default limits `$0.10`/day and 300 generated seconds
- a failed provider request releases its reservation
- the Studio never renders on slider or text change; the operator must
  estimate, then explicitly generate

§2B proposes cloud-backed neural voices with an 800ms failover but says
nothing about spend. Any Little Buddy build should inherit this engine's
budget discipline rather than open a second uncapped path to a paid API.
This is the `engineering-comms` lesson again: a tested component already in
the repo, currently wired to nothing that runs.

### Hardware: verified absent, and deprioritised by the Admiral

Independently checked on this host earlier today for the refusal reviews,
not assumed:

- `lsusb` — ten devices, every one built-in Mac hardware. No ESP32, no
  Pico W/RP2040, no I2S DAC, no PCM5102A, no external device of any kind.
- `/dev/ttyUSB*`, `/dev/ttyACM*` — absent.
- `dmesg` filtered for usb-serial drivers — no matches.
- No `openocd`, `picotool`, or `arm-none-eabi-gcc` installed.

Milestone 1 ("Breadboard the microcontroller and I2S DAC") is physical work
requiring parts that do not exist here. The Admiral has independently marked
hardware low priority, so this is a note about sequencing, not an obstacle.

**Important distinction from the standing refusals.** Several refused
packets (`PMA-MASTER-SEQUENCE`, `PMA-DIAMOND-PROTOCOL`, `QUANTUM-DEMAGNETIZER`)
were refused for *asserting hardware already existed and was running*. This
packet does not do that. It states a design and a roadmap toward hardware
that would have to be acquired. That is a legitimate specification and it is
filed as one.

### Self-declared status

The packet is headed `AUTHORIZATION: CHIEF COMMAND (ACTIVE)` and closed
`PACKET STATUS: FULLY SPECIFIED & LOCKED FOR EXECUTION`. Per doctrine 012,
recorded as the document's own claim about itself; nothing here confirms it.
Noted without prejudice — the content stands on its own merits and does not
need the banner.

### What is buildable now, with no hardware

Most of it. §2B and §2C are software:

- the JSON payload contract (`timestamp`, `priority_level`, `text_payload`)
- the ingestion socket
- the priority queue with ducking — critical faults interrupting ambient
  telemetry is pure logic and testable without a speaker
- the handshake status codes (`READY` / `BUFFERING` / `DROPPED_QUEUE_FULL`)
- the failover timeout and its behaviour under a dead endpoint
- the ring buffer, testable against a null or file sink

A sink-agnostic pipeline that writes to a file or a browser today and an
I2S DAC later is the same pipeline. Building §2C first inverts the packet's
milestone order, which is worth raising: Milestone 1 is the only one
requiring parts, and it gates nothing the others need.
