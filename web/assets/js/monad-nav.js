/**
 * Shared orientation strip for the Monad site: fixed top-left breadcrumb +
 * a one-click switcher between the five top-level sections. Purely additive
 * (fixed-position overlay) so it can be dropped into any existing page
 * without touching that page's own layout or CSS.
 *
 * Usage: one script tag near the end of <body>, e.g. from a toy two levels
 * under web/:
 *   <script src="../../assets/js/monad-nav.js"
 *           data-root="../../" data-section="observe" data-page="Periscope Station"></script>
 *
 * data-root: relative path back to web/ (the directory containing index.html).
 * data-section: one of command | observe | build | story | crew, or omitted
 *   on the landing page itself.
 * data-page: current page's human label. Omit on a section's own landing page.
 */
(function () {
  var thisScript = document.currentScript;
  var root = thisScript.getAttribute("data-root") || "";
  var section = thisScript.getAttribute("data-section") || "";
  var page = thisScript.getAttribute("data-page") || "";

  var SECTIONS = {
    command: { label: "Command", href: "command.html" },
    observe: { label: "Observe", href: "observe.html" },
    build: { label: "Build & Research", href: "build.html" },
    story: { label: "Story & Records", href: "story.html" },
    crew: { label: "Crew", href: "staff.html" },
  };
  var ORDER = ["command", "observe", "build", "story", "crew"];

  var style = document.createElement("style");
  style.textContent =
    ".monad-nav{position:fixed;top:8px;left:8px;z-index:99999;display:flex;" +
    "align-items:center;gap:5px;padding:5px 10px;background:rgba(11,18,32,.94);" +
    "border:1px solid #1E2C42;border-radius:6px;font:11px/1.4 'JetBrains Mono',monospace;" +
    "color:#6B7C93;backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);}" +
    ".monad-nav a{color:#4FD1C5;text-decoration:none;}" +
    ".monad-nav a:hover{color:#E8A33D;}" +
    ".monad-nav .mn-sep{opacity:.5;}" +
    ".monad-nav .mn-current{color:#DCE6F2;}" +
    ".monad-nav .mn-switch{position:relative;}" +
    ".monad-nav .mn-switch-btn{background:none;border:none;color:#4FD1C5;font:inherit;" +
    "cursor:pointer;padding:0;}" +
    ".monad-nav .mn-switch-btn:hover{color:#E8A33D;}" +
    ".monad-nav .mn-menu{display:none;position:absolute;top:100%;left:0;margin-top:6px;" +
    "background:#111A2B;border:1px solid #1E2C42;border-radius:6px;padding:4px;min-width:150px;" +
    "flex-direction:column;}" +
    ".monad-nav .mn-menu.open{display:flex;}" +
    ".monad-nav .mn-menu a{padding:5px 8px;border-radius:4px;white-space:nowrap;}" +
    ".monad-nav .mn-menu a:hover{background:#0D1626;}" +
    ".monad-nav .mn-menu a.mn-active{color:#E8A33D;}" +
    "@media (max-width:520px){.monad-nav{font-size:10px;padding:4px 8px;}}";
  document.head.appendChild(style);

  var bar = document.createElement("nav");
  bar.className = "monad-nav";
  bar.setAttribute("aria-label", "Monad site navigation");

  var crumbs = [];
  crumbs.push('<a href="' + root + 'index.html">⚓ Monad</a>');

  if (section && SECTIONS[section]) {
    crumbs.push('<span class="mn-sep">›</span>');
    var menuLinks = ORDER.map(function (key) {
      var s = SECTIONS[key];
      var active = key === section ? " mn-active" : "";
      return '<a class="' + active.trim() + '" href="' + root + s.href + '">' + s.label + "</a>";
    }).join("");
    var switcherHtml =
      '<span class="mn-switch">' +
      '<button type="button" class="mn-switch-btn" data-mn-toggle>' +
      SECTIONS[section].label +
      " ▾</button>" +
      '<span class="mn-menu" data-mn-menu>' +
      menuLinks +
      "</span></span>";
    crumbs.push(switcherHtml);
  }

  if (page) {
    crumbs.push('<span class="mn-sep">›</span>');
    crumbs.push('<span class="mn-current">' + page + "</span>");
  }

  bar.innerHTML = crumbs.join(" ");
  document.body.appendChild(bar);

  var toggle = bar.querySelector("[data-mn-toggle]");
  var menu = bar.querySelector("[data-mn-menu]");
  if (toggle && menu) {
    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      menu.classList.toggle("open");
    });
    document.addEventListener("click", function () {
      menu.classList.remove("open");
    });
  }
})();
