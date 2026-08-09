# Live Lab Laptop Sensor Node — Research Seed

**Recorded:** 2026-08-05  
**Source:** Admiral Cameron Lampley, direct Live Captain conversation  
**Status:** Preserved idea; not yet an implemented or verified system claim

## Seed

Integrate the laptop into the live Monad laboratory as an embodied interaction
node. Its microphone, camera, display, speakers, and local browser/runtime can
form one rich interaction surface through which the Admiral and Live Captain
share the laboratory rather than communicating only through typed chat.

The immediate opportunity is to combine interaction channels Monad already
has or has begun commissioning:

- microphone input and Captain speech;
- laptop camera input;
- existing vision-processing results, including rich hand-gesture work;
- the Root Console as the visible command and evidence surface;
- expressive Captain responses through voice, text, imagery, and research
  instruments.

The Admiral specifically reports strong pre-existing vision-processing results
for rich hand gestures. That is preserved here as source testimony and should
be located and inspected before integration claims are made.

## Research question

Can the laptop become a low-friction live-lab sensor and interaction node where
speech, visible gesture, interface state, and Captain response combine into a
coherent exchange while every interpretation remains inspectable and
correctable?

## Candidate interaction loop

```text
camera + microphone + interface state
                ↓
       timestamped raw observations
                ↓
  speech / pose / gesture interpretations
                ↓
     fused interaction hypothesis
                ↓
 Captain response or proposed lab action
                ↓
 visible confirmation, correction, and trace
```

Raw observation, model interpretation, inferred intent, and authorized action
must remain distinct. A recognized hand shape is not automatically a command;
gesture meaning should be contextual, visible, and easy for the Admiral to
correct.

## First discriminating probe

Locate the existing vision and hand-gesture artifacts, establish what was
actually demonstrated, and connect one non-command gesture to a visible Root
Console response. Measure camera-to-interface latency, recognition stability,
false activations, and correction effort. Do not begin with autonomous physical
or operational commands.

## Relationship to current research

This is a sibling opportunity to the staged Semantic Document Viewer
sub-session, not a replacement for it. The viewer can eventually become one
domain where gaze, pointing, hand pose, and speech help navigate or compare
documents, but the laptop sensor node should first prove a small general
interaction loop independently.

## Open retrieval task

Find and inventory the pre-existing vision-processing and rich hand-gesture
results named by the Admiral. Record their code paths, models, input devices,
measured behavior, and present runnability before selecting an integration
architecture.
