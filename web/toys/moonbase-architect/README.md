# Monad Education 001 — Moonbase Architect v0.1

An interactive, physics-grounded lunar habitat engineering and ECLSS simulator designed for Project Monad.

## Overview

Moonbase Architect models the real thermodynamic, diurnal, life support, and radiation constraints of establishing a permanent human settlement on the Moon.

## Key Capabilities

1. **Environmental Physics**:
   - 708.7-hour lunar diurnal cycle (14 Earth days day / 14 Earth days night).
   - Solar irradiance tracking with varying latitude, sun elevation, and polar illumination factors (e.g. Shackleton Crater Rim 88% solar availability).
   - Deep-space radiative heat rejection ($Q = \epsilon \sigma A T^4$).
   - Galactic Cosmic Ray (GCR) and Solar Particle Event (SPE) attenuation through sintered regolith arches ($I = I_0 e^{-\mu \rho x}$).

2. **Life Support & ECLSS Closed-Loop Mass Balance**:
   - Oxygen consumption (0.84 kg/day per crew member) vs. Electrolysis and Molten Regolith Extraction.
   - Water consumption (2.5 L/day per crew member) vs. Cryo-Regolith extraction and Vapor Compression Distillation recovery.
   - Food production via vertical aeroponic towers and spirulina photobioreactors.

3. **Power Grid & Thermal Management**:
   - Dual-axis tracking triple-junction GaAs photovoltaic arrays.
   - Regenerative fuel cell (RFC) cryo-storage banks for 354-hour lunar night survivability.
   - Fission Surface Power (Kilopower 40 kW Stirling reactor).
   - Two-phase ammonia thermal radiators.

4. **Interactive Architecture**:
   - 2.5D tactical lunar canvas with dynamic lighting, shadows, and resource conduit animation.
   - Visual inspection cutaway diagrams showing structural pressure hulls, Whipple micrometeorite bumpers, and regolith overburden.
   - Visual overlay layers (Radiation hazard heatmap, thermal flow, power network, hoop stress).
   - Pre-configured mission scenarios (Artemis Base Camp, Marius Hills Lava Tube, Shackleton ISRU Refinery, and Sandbox).
   - Real-time Web Audio synthesizer feedback.
