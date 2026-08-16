/**
 * Monad CardMaker v0.1 - Public Web App Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const cardForm = document.getElementById('cardForm');
  const recipientInput = document.getElementById('recipient');
  const occasionSelect = document.getElementById('occasion');
  const relationshipInput = document.getElementById('relationship');
  const detailsInput = document.getElementById('details');
  const tonePicker = document.getElementById('tonePicker');
  const generateBtn = document.getElementById('generateBtn');
  const regenerateBtn = document.getElementById('regenerateBtn');
  const printBtn = document.getElementById('printBtn');
  const quickSampleBtn = document.getElementById('quickSampleBtn');
  const spinner = document.getElementById('spinner');

  // View Mode Buttons
  const viewSpreadBtn = document.getElementById('viewSpreadBtn');
  const viewCoverBtn = document.getElementById('viewCoverBtn');
  const viewFullBtn = document.getElementById('viewFullBtn');

  // Preview Sections
  const spreadView = document.getElementById('spreadView');
  const coverView = document.getElementById('coverView');
  const printView = document.getElementById('printView');
  const cardContainer = document.getElementById('cardContainer');

  // Card Content Elements
  const frontHeadlineText = document.getElementById('frontHeadlineText');
  const frontSubtitleText = document.getElementById('frontSubtitleText');
  const insideQuoteText = document.getElementById('insideQuoteText');
  const insideMessageText = document.getElementById('insideMessageText');
  const closingSignatureText = document.getElementById('closingSignatureText');

  // SVG Icons
  const svgIconLeft = document.getElementById('svgIconLeft');
  const svgIconCover = document.getElementById('svgIconCover');
  const svgIconPrint = document.getElementById('svgIconPrint');

  // Print Elements
  const printFrontHeadline = document.getElementById('printFrontHeadline');
  const printFrontSubtitle = document.getElementById('printFrontSubtitle');
  const printInsideQuote = document.getElementById('printInsideQuote');
  const printInsideMessage = document.getElementById('printInsideMessage');
  const printClosingSignature = document.getElementById('printClosingSignature');

  let activeTone = 'Warm';

  // SVG Icons Map
  const SVG_ICONS = {
    plane: '<svg viewBox="0 0 24 24"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" fill="currentColor"/></svg>',
    leaf: '<svg viewBox="0 0 24 24"><path d="M17 8C8 10 5.9 16.17 3.83 12l1.42-1.42c3.84 3.84 9.68 4.25 14.07 1.07l-3.32-3.32c-.39-.39-.39-1.02 0-1.41.39-.39 1.02-.39 1.41 0l3.32 3.32c3.18-4.39 2.77-10.23-1.07-14.07z" fill="currentColor"/></svg>',
    star: '<svg viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" fill="currentColor"/></svg>',
    sparkles: '<svg viewBox="0 0 24 24"><path d="M12 3l2.2 4.8L19 10l-4.8 2.2L12 17l-2.2-4.8L5 10l4.8-2.2zM5 3l1.1 2.4L8.5 6.5 6.1 7.6 5 10 3.9 7.6 1.5 6.5l2.4-1.1z" fill="currentColor"/></svg>',
    heart: '<svg viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/></svg>',
    alien: '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 3.69 2.47 6.86 6 8.25V22h8v-1.75c3.53-1.39 6-4.56 6-8.25 0-5.52-4.48-10-10-10zm-3 10c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm6 0c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z" fill="currentColor"/></svg>',
    crown: '<svg viewBox="0 0 24 24"><path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .55-.45 1-1 1H6c-.55 0-1-.45-1-1v-1h14v1z" fill="currentColor"/></svg>'
  };

  // Tone Selection Handler
  tonePicker.addEventListener('click', (e) => {
    if (e.target.classList.contains('tone-chip')) {
      document.querySelectorAll('.tone-chip').forEach(c => c.classList.remove('active'));
      e.target.classList.add('active');
      activeTone = e.target.dataset.tone;
    }
  });

  // View Mode Switcher
  function setViewMode(mode) {
    [viewSpreadBtn, viewCoverBtn, viewFullBtn].forEach(b => b.classList.remove('active'));
    spreadView.style.display = 'none';
    coverView.style.display = 'none';
    printView.style.display = 'none';

    if (mode === 'spread') {
      viewSpreadBtn.classList.add('active');
      spreadView.style.display = 'flex';
    } else if (mode === 'cover') {
      viewCoverBtn.classList.add('active');
      coverView.style.display = 'flex';
    } else if (mode === 'full') {
      viewFullBtn.classList.add('active');
      printView.style.display = 'block';
    }
  }

  viewSpreadBtn.addEventListener('click', () => setViewMode('spread'));
  viewCoverBtn.addEventListener('click', () => setViewMode('cover'));
  viewFullBtn.addEventListener('click', () => setViewMode('full'));

  // Quick Sample Loader
  quickSampleBtn.addEventListener('click', () => {
    recipientInput.value = 'Ken';
    occasionSelect.value = 'Birthday';
    relationshipInput.value = 'Family';
    detailsInput.value = 'aviation enthusiast, builds remote control planes, loves family barbecues';

    document.querySelectorAll('.tone-chip').forEach(c => {
      if (c.dataset.tone === 'Funny') {
        c.click();
      }
    });

    generateCard();
  });

  // Form Submit / Generate Action
  cardForm.addEventListener('submit', (e) => {
    e.preventDefault();
    generateCard();
  });

  regenerateBtn.addEventListener('click', () => {
    generateCard();
  });

  // Generate Card API Call with fallback routing
  async function generateCard() {
    const payload = {
      recipient: recipientInput.value.trim() || 'Ken',
      occasion: occasionSelect.value || 'Birthday',
      relationship: relationshipInput.value.trim() || 'Family',
      details: detailsInput.value.trim() || 'aviation',
      tone: activeTone
    };

    setLoading(true);

    const endpoints = ['/cardmaker-api/generate', '/api/generate'];
    let card = null;

    for (const endpoint of endpoints) {
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          card = await response.json();
          break;
        }
      } catch (err) {
        // Try next endpoint
      }
    }

    if (card) {
      renderCard(card);
    } else {
      alert('Error connecting to CardMaker server.');
    }
    setLoading(false);
  }

  // Render Card Data into UI
  function renderCard(card) {
    frontHeadlineText.innerText = card.front_headline;
    frontSubtitleText.innerText = card.front_subtitle;
    insideQuoteText.innerText = card.inside_quote;
    insideMessageText.innerText = card.inside_message;
    closingSignatureText.innerText = card.closing_signature;

    // Sync to Print View
    printFrontHeadline.innerText = card.front_headline;
    printFrontSubtitle.innerText = card.front_subtitle;
    printInsideQuote.innerText = card.inside_quote;
    printInsideMessage.innerText = card.inside_message;
    printClosingSignature.innerHTML = card.closing_signature.replace('\n', '<br>');

    // Apply Theme Colors & SVG Icon
    if (card.theme) {
      const t = card.theme;
      cardContainer.style.setProperty('--card-bg', t.color_bg);
      cardContainer.style.setProperty('--card-text', t.color_text);
      cardContainer.style.setProperty('--card-primary', t.color_primary);
      cardContainer.style.setProperty('--card-secondary', t.color_secondary);
      cardContainer.style.setProperty('--card-font', t.font_family);

      const iconSvg = SVG_ICONS[t.svg_icon] || SVG_ICONS['heart'];
      svgIconLeft.innerHTML = iconSvg;
      svgIconCover.innerHTML = iconSvg;
      svgIconPrint.innerHTML = iconSvg;
    }
  }

  function setLoading(isLoading) {
    generateBtn.disabled = isLoading;
    regenerateBtn.disabled = isLoading;
    if (isLoading) {
      spinner.style.display = 'inline-block';
      generateBtn.querySelector('.btn-text').innerText = 'Generating...';
    } else {
      spinner.style.display = 'none';
      generateBtn.querySelector('.btn-text').innerText = '✨ Generate Card';
    }
  }

  // Print / Export PDF Action
  printBtn.addEventListener('click', () => {
    window.print();
  });

  // Generate initial sample card on load
  generateCard();
});
