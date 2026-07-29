(function () {
  "use strict";

  var HANDOFF_KEY = "intentforge.pendingLexicon.v0.1";
  var REQUIRED_REFS = ["Fan.Face:A", "Panel.Hole:1", "Panel.Hole:2"];
  var REQUIREMENTS = [
    "Physical units",
    "Envelope width, height, and thickness",
    "Panel.Hole:1 physical position and diameter",
    "Panel.Hole:2 physical position and diameter",
    "Fan.Face:A physical center, bolt spacing, bolt diameter, and airflow diameter",
    "Keep-out physical representation and dimensions",
    "Minimum wall thickness and manufacturing assumptions",
    "Private phrase disposition for the current generator",
    "Translation review decision and scope"
  ];
  var FALSE_STATES = [
    "Geometry generated", "Simulation completed", "Prototype manufactured",
    "Prototype tested", "Externally reviewed", "Validated for use"
  ];

  var signal = document.getElementById("signal");
  var empty = document.getElementById("empty");
  var proposal = document.getElementById("proposal");

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[character];
    });
  }

  function refuse(message) {
    proposal.classList.remove("visible");
    empty.style.display = "block";
    empty.textContent = "Translation refused: " + message;
    signal.textContent = "Source evidence did not cross the truth boundary.";
    signal.className = "signal error";
  }

  function validate(payload) {
    if (!payload || payload.schema_version !== "monad.intentLexiconExport.v0.1") throw new Error("unsupported lexicon export schema");
    if (!Array.isArray(payload.entries) || payload.entries.length !== 1) throw new Error("v0.1 requires exactly one lexicon entry");
    var entry = payload.entries[0];
    if (entry.schema_version !== "monad.intentLexiconEntry.v0.1") throw new Error("unsupported lexicon entry schema");
    var episode = entry.source_episode;
    if (!episode || episode.schema_version !== "monad.geometricTeachingEpisode.v0.1") throw new Error("complete source teaching episode is absent");
    if (episode.id !== entry.source_episode_id) throw new Error("source episode identifier mismatch");
    if (episode.epistemic_status !== "reviewed-provisional" || episode.human_review?.reviewed !== true) throw new Error("teaching episode lacks explicit human review");
    if (episode.human_review?.universal_claim !== false) throw new Error("private meaning cannot be marked universal");
    var references = Array.isArray(episode.explicit_references) ? episode.explicit_references : [];
    REQUIRED_REFS.forEach(function (ref) {
      var found = references.find(function (item) { return item.ref === ref; });
      if (!found) throw new Error("required reference absent: " + ref);
      if (found.sacred !== true) throw new Error("required reference is not sacred: " + ref);
    });
    if (!episode.gesture || episode.gesture.type !== "keep-out" || !Array.isArray(episode.gesture.samples) || episode.gesture.samples.length < 2) {
      throw new Error("typed keep-out gesture with at least two samples is required");
    }
    return { entry:entry, episode:episode };
  }

  function render(payload) {
    var source;
    try { source = validate(payload); } catch (error) { refuse(error.message); return; }
    var entry = source.entry;
    var episode = source.episode;
    document.getElementById("words").textContent = episode.expression?.words || "No natural-language statement recorded.";
    document.getElementById("phrase").textContent = "“" + entry.phrase + "” · v" + entry.version;
    document.getElementById("meaning").textContent = entry.operational_meaning;
    document.getElementById("provenance").textContent =
      "Episode " + episode.id + " · " + episode.explicit_references.length + " references · " +
      episode.gesture.samples.length + " gesture samples in " + episode.gesture.coordinate_space + ".";

    var maps = [
      [["Panel.Hole:1", "Panel.Hole:2"], "existing panel-hole interfaces"],
      [["Fan.Face:A"], "fan center, bolt pattern, and airflow interface"],
      [["gesture:keep-out"], "physical keep-out representation"],
      [["lexicon:" + entry.phrase + "@v" + entry.version], "preserved; generator disposition required"]
    ];
    document.getElementById("mappings").innerHTML = maps.map(function (map) {
      return '<div class="map"><span class="source">' + escapeHtml(map[0].join(" + ")) +
        '</span><span class="arrow">→</span><span class="target">' + escapeHtml(map[1]) + "</span></div>";
    }).join("");
    document.getElementById("requirements").innerHTML = REQUIREMENTS.map(function (item) {
      return "<li>" + escapeHtml(item) + "</li>";
    }).join("");
    document.getElementById("truth").innerHTML = FALSE_STATES.map(function (item) {
      return "<div>Not earned · " + escapeHtml(item) + "</div>";
    }).join("");
    empty.style.display = "none";
    proposal.classList.add("visible");
    signal.textContent = "Reviewed language accepted. Nine physical and review requirements remain unresolved.";
    signal.className = "signal";
  }

  function example() {
    return {
      schema_version:"monad.intentLexiconExport.v0.1", exported_at:new Date().toISOString(),
      entries:[{
        schema_version:"monad.intentLexiconEntry.v0.1", phrase:"usual forgiving fit", version:1,
        operational_meaning:"0.25–0.35 mm clearance per side for removable PETG fits on my FDM printer.",
        source_episode_id:"episode-reviewed-demonstration",
        source_episode:{
          schema_version:"monad.geometricTeachingEpisode.v0.1", id:"episode-reviewed-demonstration",
          epistemic_status:"reviewed-provisional",
          expression:{words:"Mount this fan to these two holes, keep airflow open, avoid the cable, and use my usual forgiving fit."},
          explicit_references:[
            {ref:"Fan.Face:A",sacred:true},{ref:"Panel.Hole:1",sacred:true},{ref:"Panel.Hole:2",sacred:true}
          ],
          gesture:{type:"keep-out",coordinate_space:"demo-stage-640x400",samples:[[320,300],[410,250],[500,190]]},
          human_review:{reviewed:true,universal_claim:false}
        }
      }]
    };
  }

  document.getElementById("loadExample").addEventListener("click", function () { render(example()); });
  document.getElementById("fileInput").addEventListener("change", function (event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      try { render(JSON.parse(reader.result)); } catch (_) { refuse("file is not valid JSON"); }
    };
    reader.readAsText(file);
  });

  var handoff = localStorage.getItem(HANDOFF_KEY);
  if (handoff) {
    localStorage.removeItem(HANDOFF_KEY);
    try { render(JSON.parse(handoff)); } catch (_) { refuse("same-origin handoff was not valid JSON"); }
  }
}());
