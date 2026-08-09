---
id: CAP-ARI-004
title: Laptop Live-Lab Sensor and Rich Interaction Node
creation_timestamp: 2026-08-05T14:36:00Z
authoring_role: Captain
authorizing_role: Admiral
research_question: Can the laptop become a low-friction live-lab node where speech, camera observations, rich hand gestures, interface state, and Captain response form one coherent, inspectable, correctable interaction loop?
permitted_autonomous_scope: Locate and inspect existing vision and hand-gesture artifacts; inventory present capabilities; characterize one non-command gesture; build a reversible Root Console response prototype; measure latency, stability, false activation, and correction effort; propose the next integration experiment.
prohibited_actions: Treat inferred gesture as automatically authorized intent; record or transmit camera or microphone data without visible activation; enable unattended operational commands; claim existing vision results without locating evidence; publish private sensor data; open a second indefinite autonomous campaign.
natural_stopping_conditions: Existing gesture apparatus cannot be located or run; one end-to-end non-command interaction is measured; permission or privacy design requires Admiral judgment; available hardware blocks the probe; integration requires broad architectural change; three-generation budget is exhausted.
expected_return_packet: Capability inventory, verified artifact paths, measured interaction trace, competing integration approaches, prototype result including failures, privacy and correction design, and one recommended next experiment.
status: NEEDS_FURTHER_ENGINEERING
record_origin: contemporaneous
provenance: Admiral directed the Live Captain to preserve the laptop live-lab idea and then ordered a packet logged for it on 2026-08-05.
later_links:
  - docs/research/LIVE_LAB_LAPTOP_SENSOR_NODE_SEED_2026-08-05.md
  - docs/doctrine/025-capability-retrieval-to-integration.md
---

# Captain Autonomous Research Packet 04

## Laptop Live-Lab Sensor and Rich Interaction Node

**Program:** Project Monad Live Research  
**Inquiry class:** Bounded multimodal interaction research  
**Execution state:** Needs further engineering. The existing vision capability
must pass Doctrine 025 retrieval and reproduction before live integration;
Captain Watch execution still requires an explicit Admiral approval.

## 1. Founding opportunity

The laptop is already more than a terminal. It combines camera, microphone,
display, speakers, browser execution, and the Root Console at the point where
the Admiral works. Monad also has commissioned speech interaction and, by the
Admiral's report, strong pre-existing vision-processing results including rich
hand-gesture processing.

The research opportunity is to make these capabilities one live laboratory
relationship without collapsing observation, interpretation, intent, and
authority into one unreliable inference.

## 2. Primary question

Can the laptop become a low-friction live-lab node where speech, camera
observations, rich hand gestures, interface state, and Captain response form
one coherent, inspectable, correctable interaction loop?

## 3. Competing hypotheses

- **H1 — Multimodal gain:** gesture and speech together express laboratory
  intent more naturally and accurately than either channel alone.
- **H2 — Useful parallel channels:** camera and microphone are valuable, but
  their interpretations should remain independent signals joined only by the
  Captain or explicit interface confirmation.
- **H3 — Gesture novelty trap:** rich gesture recognition is impressive but
  adds false activation and correction burden without improving real work.
- **H4 — Domain-specific value:** gesture helps only in spatial tasks such as
  pointing, model inspection, or document comparison, not as a general command
  language.

## 4. Evidence discipline

Keep four layers visibly distinct:

```text
raw observation → interpreted gesture/speech → inferred intent → authorized action
```

The Admiral's statement about strong existing gesture results is provenance for
the retrieval task, not proof that the current system is runnable. The first
generation must locate and inspect the actual artifacts.

## 5. First bounded arc

### Generation 1 — Capability retrieval

Locate vision-processing code, models, demonstrations, measurements, and input
requirements. Establish what ran, on which hardware, and whether it still runs.

### Generation 2 — One non-command gesture

Choose a gesture with visible but harmless meaning—for example, highlighting a
region or displaying a recognized pose. Connect camera observation to a Root
Console indication with raw and interpreted state both visible.

### Generation 3 — Interaction characterization

Measure end-to-end latency, recognition stability, false activations, recovery
after loss of pose, and the Admiral's correction effort. Compare gesture-only,
speech-only, and combined interaction where practical.

## 6. Mandatory controls

- visible camera and microphone activation state;
- an immediate stop control;
- no operational action from gesture alone in this arc;
- a no-gesture baseline;
- explicit indication of uncertainty or loss of tracking;
- no durable raw sensor recording unless separately authorized;
- preservation of failed and ambiguous trials.

## 7. Selection rule

Prefer the next experiment with the greatest expected discrimination between
multimodal gain, parallel-channel usefulness, novelty burden, and
domain-specific value—weighted by reversibility and correction effort.

## 8. Return condition

After at most three research generations, return one compact brief containing:

1. verified existing capabilities and their paths;
2. what was actually connected and observed;
3. quantitative latency and stability evidence;
4. false activations and correction behavior;
5. strongest surviving hypothesis;
6. privacy and authority implications;
7. exactly one recommended next experiment.

This packet does not displace the staged Semantic Document Viewer campaign.
Only one Captain Watch objective may be active; Command chooses when this
packet enters execution.
