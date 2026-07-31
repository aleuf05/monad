"""Documented field ranges/units and tunable constants for the Living Basin.

All thresholds here are provisional modeling choices, not measured physical
constants. The model is deliberately simple: it is meant to be *structurally
causal and inspectable*, not physically accurate. See ARCHITECTURE.md.
"""

from __future__ import annotations

GRID_SIZE = 64

# --- Field documentation ---------------------------------------------------
# Every cell carries these fields. Ranges are normalized [0, 1] unless noted.
#
#   elevation         meters, arbitrary baseline (basin-shaped terrain)
#   soil_moisture     [0, 1] fraction of local water-holding capacity filled
#   soil_cohesion     [0, 1] structural resistance to erosion
#   organic_content   [0, 1] built up slowly by vegetation, raises cohesion
#   root_density      [0, 1] fraction of max root coverage, lags biomass
#   vegetation_biomass[0, 1] fraction of local carrying capacity
#   surface_water     mm of standing/flowing water depth at the cell
#   flow_direction    (dr, dc) offset to the downhill neighbor, or None
#   erosion_depth     meters cumulatively removed (monotonic, >= 0)
#   trail_intensity   [0, 1] accumulated herbivore passage, decays slowly
#   grazing_pressure  [0, 1] recent grazing accumulator, decays

FIELD_NAMES = [
    "elevation",
    "soil_moisture",
    "soil_cohesion",
    "organic_content",
    "root_density",
    "vegetation_biomass",
    "surface_water",
    "erosion_depth",
    "trail_intensity",
    "grazing_pressure",
]

# --- Hydrology ---------------------------------------------------------
RAINFALL_DT_HOURS = 0.12          # simulated hours per tick, for converting a
                                   # scripted mm/hr rate into this tick's mm
                                   # deposit -- one tick is *not* one hour;
                                   # this keeps a "48mm/hr" event physically
                                   # labeled while giving fine-grained ticks
INFILTRATION_BASE = 0.06          # fraction of surface_water infiltrated/tick, baseline
INFILTRATION_ROOT_BONUS = 0.10    # extra infiltration fraction at root_density == 1
EVAPORATION_RATE = 0.03           # fraction of soil_moisture lost/tick (evaporation)
DEEP_DRAINAGE_RATE = 0.025        # additional fraction of soil_moisture lost/tick to
                                   # groundwater -- without this a closed basin has no
                                   # true outflow and sustained rain saturates every
                                   # cell given enough ticks, not just convergence zones
SURFACE_WATER_LOSS_RATE = 0.07    # fraction of surface_water lost/tick (evaporation +
                                   # seepage), faster than deep soil moisture loss
RUNOFF_FLOW_FRACTION = 0.45       # fraction of a cell's surface_water that flows downhill/tick
SATURATION_THRESHOLD = 0.85       # soil_moisture level considered "saturated" (edge-triggered event)
MOISTURE_CONVERSION = 0.010       # fractional soil_moisture gained per mm infiltrated;
                                   # deliberately small -- see hydrology.infiltrate_and_evaporate

# --- Vegetation ----------------------------------------------------------
VEG_GROWTH_RATE = 0.02            # biomass growth toward carrying capacity/tick
VEG_MOISTURE_OPTIMAL = 0.5        # soil_moisture at which growth is fastest
ROOT_APPROACH_RATE = 0.03         # root_density moves toward biomass by this fraction/tick
LOW_ROOT_THRESHOLD = 0.20         # root_density below this fires a root_loss event

# --- Herbivores / trails ---------------------------------------------------
HERBIVORE_COUNT = 6
GRAZE_RATE = 0.12                 # biomass fraction consumed per visit
GRAZING_PRESSURE_GAIN = 0.20
GRAZING_PRESSURE_DECAY = 0.01
GRAZED_PATCH_THRESHOLD = 0.6      # grazing_pressure level that registers a GrazedPatch feature
TRAIL_GAIN_PER_PASS = 0.08
TRAIL_DECAY = 0.002
TRAIL_MATURE_THRESHOLD = 0.25     # trail_intensity level that registers a HerbivoreTrail feature

# --- Soil cohesion / erosion ------------------------------------------------
COHESION_BASE = 0.50
COHESION_ROOT_WEIGHT = 0.35
COHESION_ORGANIC_WEIGHT = 0.15
COHESION_SATURATION_PENALTY = 0.35
COHESION_RELAX_RATE = 0.15        # fraction of the way from current to target cohesion/tick
COHESION_DEGRADED_THRESHOLD = 0.35  # soil_cohesion below this fires a cohesion_degraded event

EROSION_RUNOFF_THRESHOLD = 0.15   # runoff (mm-equivalent moved) above which erosion can occur
EROSION_SATURATION_THRESHOLD = 0.80
EROSION_COHESION_THRESHOLD = 0.40
EROSION_SLOPE_THRESHOLD = 0.02    # elevation drop to lowest neighbor, meters
EROSION_RATE = 0.6                # erosion_depth gained per tick when all thresholds are met,
                                   # scaled by how far runoff exceeds threshold
GULLY_DEPTH_THRESHOLD = 0.35      # erosion_depth at which a cell becomes an ErosiveGully feature

# --- Pools -------------------------------------------------------------
POOL_WATER_THRESHOLD = 3.0        # mm of standing surface_water
POOL_PERSIST_TICKS = 6            # consecutive ticks above threshold before a WaterPool registers

ORGANIC_GROWTH_RATE = 0.01        # organic_content growth per tick when biomass is high

# --- Weather -------------------------------------------------------------
EVENT_EPSILON = 1e-6              # below this a field change is not worth recording
