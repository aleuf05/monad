Monad Mission Packet
Harbor Pilot Scenario v1.0
To: Commander Claude, Chief Engineer (Integration Watch)
From: Captain T
Priority: High
Objective: Produce Monad's first scenario that requires genuine interaction between every major bridge subsystem.
Mission Intent
We have proven that FleetCore can serve as the authoritative world model.
We now wish to demonstrate that the bridge is not merely a dashboard—it is an operational environment.
The Harbor Pilot scenario should feel like a real maritime procedure, not a scripted cutscene.
Design Philosophy
Every bridge instrument should have a meaningful role.
No decorative UI.
Every subsystem should participate in accomplishing the mission.
Scenario Overview
Title
Harbor Pilot Boarding
Flagship Monad is inbound to a major harbor.
A harbor pilot has been requested.
The pilot boat departs the harbor and intercepts Monad.
The bridge crew must successfully communicate with the pilot before navigation into restricted waters may begin.
Desired Flow
Phase 1 — Inbound Transit
Scenario initializes.
FleetCore creates:
Monad
Harbor
Harbor pilot boat
Harbor traffic
Environmental conditions
Bridge reports:
Harbor Pilot ETA 12 minutes.
Phase 2 — Detection
Pilot boat becomes visible.
Fleet Motion displays approach.
Periscope can visually identify pilot craft.
Radio remains quiet.
Phase 3 — Radio Contact
Pilot initiates communication.
Example:
"Monad, Pilot Boat Three."
"Request permission to come alongside."
The Captain must respond using the Radio.
Scenario should not automatically advance.
Communication is the trigger.
Phase 4 — Boarding
After radio acknowledgement:
Pilot boat approaches.
Boarding animation/event.
Bridge receives:
"Harbor Pilot aboard."
Phase 5 — Transfer of the Conn
Radio:
"Captain, request the conn."
Captain responds:
"The conn is yours."
Bridge status updates.
Pilot now issues helm commands.
Example:
Port five
Dead slow ahead
Midships
Ease to starboard
Captain retains command of the vessel while temporarily transferring ship handling authority.
Phase 6 — Harbor Transit
Pilot navigates the vessel.
Bridge follows orders.
Fleet Motion displays movement.
Periscope observes nearby traffic.
Radio continues normal procedural communications.
Phase 7 — Completion
Pilot safely delivers Monad to berth.
Pilot departs.
Scenario concludes.
Mission success recorded.
Acceptance Criteria
✓ FleetCore drives all world state.
✓ Fleet Motion displays every movement.
✓ Periscope observes the pilot boat.
✓ Radio communication is mandatory.
✓ Bridge state changes after "Pilot aboard."
✓ Conn transfer visibly occurs.
✓ Entire interaction can be replayed.
Stretch Goals (Optional)
Variable weather
Night operations
Multiple harbor layouts
Busy commercial traffic
Tug assistance
Harbor Control voice traffic
Optional radio mistakes requiring clarification
Architectural Principle
The Harbor Pilot is not a scripted cinematic.
He is another actor inhabiting FleetCore.
Every event should arise from authoritative world state and state transitions rather than isolated UI logic.
Captain's Intent
This scenario is recommended as Monad's first flagship demonstration.
A successful run should make the operator briefly forget they are testing software and instead feel like they are standing a bridge watch aboard a ship entering harbor.
Proceed boldly. Build for demonstration. Build for realism.
— Captain T ⚓
