/**
 * Moonbase Architect v0.1
 * Core Mathematical Simulation & Mission Engine (Deterministic)
 * 
 * Common Core 4th Grade Focus:
 * - Area (A = W × L)
 * - Perimeter (P = 2W + 2L)
 * - Multiplication & Factor Pairs (e.g. factors of 48)
 * - Optimization (Minimizing perimeter for fixed area, maximizing area for fixed perimeter)
 */

export const SHIELDING_COST_PER_METER = 10000; // $10,000 per meter of exterior wall

export const MISSIONS = [
  {
    id: 1,
    title: 'Mission 1: Build It',
    targetArea: 48,
    type: 'target_area',
    prompt: 'The crew needs exactly 48 floor tiles. Build a habitat that fits!',
    subtext: 'Find any rectangle with an area of 48. There are multiple solutions!',
    expectedPairs: [[6, 8], [8, 6], [4, 12], [12, 4], [3, 16], [16, 3], [2, 24], [24, 2], [1, 48], [48, 1]]
  },
  {
    id: 2,
    title: 'Mission 2: Make It Cheaper',
    targetArea: 48,
    type: 'optimize_perimeter',
    prompt: 'Keep exactly 48 floor tiles, but use less outside wall. Meteor shielding is expensive!',
    subtext: 'Can you find the shape with 48 tiles that has the lowest perimeter?',
    optimalPerimeter: 28, // 6×8 or 8×6 has P = 2(6+8) = 28
    optimalDimensions: [[6, 8], [8, 6]]
  },
  {
    id: 3,
    title: 'Mission 3: Beat the Engineers',
    fixedPerimeter: 24,
    type: 'maximize_area',
    prompt: 'You have a wall budget of 24 meters. Build the largest habitat you can without exceeding it!',
    subtext: 'What shape gives you the most floor space for a 24-meter perimeter?',
    maxPerimeter: 24,
    optimalArea: 36, // 6×6 square has P=24, Area=36
    optimalDimensions: [[6, 6]]
  },
  {
    id: 4,
    title: 'Sandbox: Free Build',
    type: 'free_build',
    prompt: 'Design any habitat shape you like. Watch how Area and Perimeter interact!',
    subtext: 'Test any dimensions up to 24 × 24.'
  }
];

export class MoonbaseMathEngine {
  constructor() {
    this.minDimension = 1;
    this.maxDimension = 24;

    this.width = 6;
    this.length = 8;

    this.currentMissionIndex = 0;
    this.discoveredPairsByMission = {
      1: new Set(),
      2: new Set(),
      3: new Set()
    };

    this.bestPerimeterFor48 = Infinity;
    this.bestAreaFor24 = 0;
  }

  getCurrentMission() {
    return MISSIONS[this.currentMissionIndex];
  }

  setDimensions(w, l) {
    const prevW = this.width;
    const prevL = this.length;

    this.width = Math.max(this.minDimension, Math.min(this.maxDimension, Math.round(w)));
    this.length = Math.max(this.minDimension, Math.min(this.maxDimension, Math.round(l)));

    const changed = (prevW !== this.width || prevL !== this.length);
    return {
      changed,
      state: this.getCalculations(),
      maraReaction: this.evaluateMaraReaction(prevW, prevL)
    };
  }

  setWidth(w) {
    return this.setDimensions(w, this.length);
  }

  setLength(l) {
    return this.setDimensions(this.width, l);
  }

  getCalculations() {
    const width = this.width;
    const length = this.length;
    const area = width * length;
    const perimeter = 2 * (width + length);
    const shieldingCost = perimeter * SHIELDING_COST_PER_METER;
    const isSquare = (width === length);

    const mission = this.getCurrentMission();
    let missionPassed = false;
    let isOptimalRecord = false;
    let missionMessage = '';

    const pairKey = `${Math.min(width, length)}×${Math.max(width, length)}`;

    if (mission.type === 'target_area') {
      if (area === mission.targetArea) {
        missionPassed = true;
        this.discoveredPairsByMission[1].add(pairKey);
        const totalFound = this.discoveredPairsByMission[1].size;
        missionMessage = `Great build! ${width} × ${length} = ${area} tiles. Discovered ${totalFound} shape${totalFound > 1 ? 's' : ''}!`;
      } else {
        const diff = area - mission.targetArea;
        missionMessage = diff > 0 
          ? `Too big by ${diff} tile${diff > 1 ? 's' : ''} (Current: ${area}).` 
          : `Need ${Math.abs(diff)} more tile${Math.abs(diff) > 1 ? 's' : ''} (Current: ${area}).`;
      }
    } else if (mission.type === 'optimize_perimeter') {
      if (area === mission.targetArea) {
        this.discoveredPairsByMission[2].add(pairKey);
        if (perimeter < this.bestPerimeterFor48) {
          this.bestPerimeterFor48 = perimeter;
        }
        if (perimeter === mission.optimalPerimeter) {
          missionPassed = true;
          isOptimalRecord = true;
          missionMessage = `ENGINEERING RECORD! 48 tiles with only ${perimeter}m of wall ($${shieldingCost.toLocaleString()})!`;
        } else {
          const savings = perimeter - mission.optimalPerimeter;
          missionMessage = `48 tiles with ${perimeter}m of wall. Can you save ${savings} more meters of shielding?`;
        }
      } else {
        missionMessage = `Area must be exactly 48 tiles (Current: ${area}). Adjust width and length.`;
      }
    } else if (mission.type === 'maximize_area') {
      if (perimeter <= mission.maxPerimeter) {
        if (area > this.bestAreaFor24) {
          this.bestAreaFor24 = area;
        }
        if (area === mission.optimalArea && perimeter === mission.maxPerimeter) {
          missionPassed = true;
          isOptimalRecord = true;
          missionMessage = `MAXIMUM EFFICIENCY RECORD! ${area} tiles enclosed with ${perimeter}m of wall!`;
        } else {
          missionMessage = `Perimeter ${perimeter}m ≤ ${mission.maxPerimeter}m. Enclosing ${area} tiles. Can you get even more floor space?`;
        }
      } else {
        const over = perimeter - mission.maxPerimeter;
        missionMessage = `Exceeded wall budget by ${over} meter${over > 1 ? 's' : ''}! Wall is ${perimeter}m (Budget: ${mission.maxPerimeter}m).`;
      }
    } else {
      missionMessage = `${width} m × ${length} m = ${area} tiles (${perimeter} m wall).`;
    }

    return {
      width,
      length,
      area,
      perimeter,
      shieldingCost,
      isSquare,
      mission,
      missionPassed,
      isOptimalRecord,
      missionMessage,
      discoveredCount: (this.discoveredPairsByMission[mission.id] || new Set()).size,
      discoveredPairs: Array.from(this.discoveredPairsByMission[mission.id] || [])
    };
  }

  evaluateMaraReaction(prevW, prevL) {
    const prevArea = prevW * prevL;
    const prevPerimeter = 2 * (prevW + prevL);

    const cur = this.getCalculations();
    const curArea = cur.area;
    const curPerimeter = cur.perimeter;

    // MARA state-aware prompts based on child actions:
    if (cur.mission.id === 1) {
      if (curArea === 48) {
        const found = cur.discoveredCount;
        if (found === 1) {
          return `“Nice! ${cur.width} × ${cur.length} gives exactly 48 tiles. Can you make a different shape with the same 48 tiles?”`;
        } else if (found < 4) {
          return `“Another solution! That’s ${found} different shapes with 48 tiles. Keep exploring factor pairs!”`;
        } else {
          return `“Incredible factor mastery! You’ve found ${found} different ways to arrange 48 floor tiles!”`;
        }
      } else if (curArea > 48) {
        return `“That’s ${curArea} tiles (${cur.width} × ${cur.length}). A bit too spacious! Try reducing one dimension.”`;
      } else {
        return `“We have ${curArea} tiles so far. The crew needs 48. Increase width or length to expand.”`;
      }
    }

    if (cur.mission.id === 2) {
      if (curArea === 48) {
        if (cur.isOptimalRecord) {
          return `“ENGINEERING RECORD! 6 × 8 creates a square-like shape that uses only 28 meters of wall! Same floor, less wall!”`;
        } else if (prevArea === 48 && curPerimeter < prevPerimeter) {
          const saved = prevPerimeter - curPerimeter;
          return `“You kept 48 tiles but saved ${saved} meters of shielding! What changed about the shape?”`;
        } else if (prevArea === 48 && curPerimeter > prevPerimeter) {
          return `“Your room got longer and skinnier. Notice what happened to the wall cost?”`;
        } else {
          return `“48 tiles! Wall perimeter is ${curPerimeter}m. Can you bring the sides closer together to make it even cheaper?”`;
        }
      } else {
        return `“Remember to keep the floor area at exactly 48 tiles while hunting for lower perimeter!”`;
      }
    }

    if (cur.mission.id === 3) {
      if (cur.isOptimalRecord) {
        return `“BEAT THE ENGINEERS! A 6 × 6 square encloses 36 tiles with exactly 24m of wall. Squares maximize area for a given perimeter!”`;
      } else if (curPerimeter <= 24) {
        if (curArea > prevArea) {
          return `“Area went up to ${curArea} tiles without exceeding the 24m wall budget! Can we go even higher?”`;
        } else {
          return `“Wall is ${curPerimeter}m (under budget). Floor space is ${curArea} tiles. What happens if width and length get closer?”`;
        }
      } else {
        return `“Warning: Wall perimeter is ${curPerimeter}m. That exceeds our 24m wall budget! Reduce one side.”`;
      }
    }

    // Sandbox
    if (cur.isSquare) {
      return `“A perfect square (${cur.width} × ${cur.length})! Notice how compact the perimeter is for ${curArea} tiles.”`;
    }
    return `“Width: ${cur.width}m, Length: ${cur.length}m. Area = ${curArea} tiles. Perimeter = ${curPerimeter}m.”`;
  }
}
