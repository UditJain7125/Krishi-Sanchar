// Each service now deploys as its own Render Web Service (see render.yaml),
// so there's no shared API_BASE or /api/* prefix anymore — every feature
// talks directly to its own service's root.
//
// After your first Render deploy, replace these with the actual URLs Render
// assigns (Dashboard → each service → the URL shown at the top, usually
// https://<service-name>.onrender.com if that name was free).
const API = {
  crop: 'https://krishisanchar-crop-c3wq.onrender.com',
  fertilizer: 'https://krishisanchar-fertilizer-c3wq.onrender.com',
  yieldPrediction: 'https://krishisanchar-yield-c3wq.onrender.com',
  market: 'https://krishisanchar-market-c3wq.onrender.com',
  weather: 'https://krishisanchar-weather-c3wq.onrender.com',
  assistant: 'https://krishisanchar-assistant-c3wq.onrender.com',
  disease: 'https://krishisanchar-disease-c3wq.onrender.com',
};

// Local fallback icons — the crop API doesn't return an image, so we map
// the crop name it returns to an icon on our side.
const CROP_ICONS = {
  rice: 'https://cdn-icons-png.flaticon.com/512/862/862856.png',
  maize: 'https://cdn-icons-png.flaticon.com/512/820/820559.png',
  wheat: 'https://cdn-icons-png.flaticon.com/512/862/862847.png',
  sugarcane: 'https://cdn-icons-png.flaticon.com/512/2921/2921980.png',
  potato: 'https://cdn-icons-png.flaticon.com/512/1041/1041355.png',
};
const DEFAULT_CROP_ICON = 'https://cdn-icons-png.flaticon.com/512/628/628283.png';

// Map OpenWeatherMap "weather" descriptions to the icon set already used in
// the Weather Forecast panel mockup.
const WEATHER_ICONS = {
  clear: 'https://cdn-icons-png.flaticon.com/512/1163/1163736.png',
  clouds: 'https://cdn-icons-png.flaticon.com/512/1163/1163763.png',
  rain: 'https://cdn-icons-png.flaticon.com/512/1163/1163728.png',
  drizzle: 'https://cdn-icons-png.flaticon.com/512/1163/1163728.png',
  thunderstorm: 'https://cdn-icons-png.flaticon.com/512/1163/1163731.png',
  snow: 'https://cdn-icons-png.flaticon.com/512/1163/1163736.png',
  mist: 'https://cdn-icons-png.flaticon.com/512/1163/1163763.png',
  haze: 'https://cdn-icons-png.flaticon.com/512/1163/1163763.png',
  fog: 'https://cdn-icons-png.flaticon.com/512/1163/1163763.png',
};
const DEFAULT_WEATHER_ICON = 'https://cdn-icons-png.flaticon.com/512/1163/1163763.png';

function weatherIconFor(description) {
  const desc = (description || '').toLowerCase();
  for (const key in WEATHER_ICONS) {
    if (desc.includes(key)) return WEATHER_ICONS[key];
  }
  return DEFAULT_WEATHER_ICON;
}

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initSidebar();
  initDiseaseDetection();
  initCropRecommendation();
  initFertilizerRecommendation();
  initMarketAnalysis();
  initAiAssistant();
  initYieldPrediction();
  initWeatherForecast();
});

// ==========================================================================
// 1. NAVIGATION & PAGE VIEW SWITCHING
// ==========================================================================
function initNavigation() {
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  const panels = document.querySelectorAll('.dashboard-panel');
  const pageTitle = document.getElementById('current-page-title');

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      // Ignore logout click since it has inline handler
      if (item.classList.contains('logout-item')) return;
      
      e.preventDefault();
      const targetId = item.getAttribute('data-target');
      
      // Update sidebar active class
      navItems.forEach(nav => nav.classList.remove('active'));
      item.classList.add('active');

      // Update active panel with transition
      panels.forEach(panel => {
        panel.classList.remove('active');
        if (panel.id === targetId) {
          panel.classList.add('active');
          // Update header title
          pageTitle.textContent = item.querySelector('span').textContent;
        }
      });

      // Close sidebar on mobile after clicking
      const sidebar = document.querySelector('.sidebar');
      if (sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
      }
    });
  });
}

// Enter Dashboard View
function enterDashboard() {
  const landingPage = document.getElementById('landing-page');
  const dashboardPage = document.getElementById('dashboard-page');
  
  landingPage.classList.remove('active');
  dashboardPage.classList.add('active');
  
  // Set default tab (Overview)
  switchDashboardTab('dashboard-overview');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Exit Dashboard View (Logout)
function exitDashboard() {
  const landingPage = document.getElementById('landing-page');
  const dashboardPage = document.getElementById('dashboard-page');
  
  dashboardPage.classList.remove('active');
  landingPage.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Switch tabs dynamically from links inside cards
function switchDashboardTab(targetTabId) {
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  const panels = document.querySelectorAll('.dashboard-panel');
  const pageTitle = document.getElementById('current-page-title');

  // Find corresponding nav item
  navItems.forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('data-target') === targetTabId) {
      item.classList.add('active');
      pageTitle.textContent = item.querySelector('span').textContent;
    }
  });

  // Switch panels
  panels.forEach(panel => {
    panel.classList.remove('active');
    if (panel.id === targetTabId) {
      panel.classList.add('active');
    }
  });
}

// Shortcut to open dashboard to specific tab
function navigateToDashboard(targetTabId) {
  enterDashboard();
  switchDashboardTab(targetTabId);
}


// ==========================================================================
// 2. SIDEBAR TOGGLE & NOTIFICATIONS
// ==========================================================================
function initSidebar() {
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('active');
    });
  }

  // Close sidebar clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 1024) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target) && sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
      }
    }
  });
}

// Toggle notification bell dropdown
function toggleNotifications() {
  const dropdown = document.getElementById('notifications-dropdown');
  dropdown.classList.toggle('active');

  // Close dropdown on click outside
  document.addEventListener('click', function closeDropdown(e) {
    const bell = document.querySelector('.notification-bell');
    if (!bell.contains(e.target) && dropdown.classList.contains('active')) {
      dropdown.classList.remove('active');
      document.removeEventListener('click', closeDropdown);
    }
  });
}


// ==========================================================================
// 3. SCHEME APPLICATION MODAL & TOASTS
// ==========================================================================
let activeScheme = '';

function openSchemeModal(schemeName) {
  event.preventDefault();
  activeScheme = schemeName;
  const modal = document.getElementById('scheme-modal');
  const title = document.getElementById('modal-title');
  title.textContent = `Apply for ${schemeName} Scheme`;
  modal.classList.add('active');
}

function closeSchemeModal() {
  const modal = document.getElementById('scheme-modal');
  modal.classList.remove('active');
}

function submitSchemeApplication(e) {
  e.preventDefault();
  closeSchemeModal();
  
  // Show toast message
  showToast(`Application for ${activeScheme} submitted successfully!`);
  
  // Log into History Table
  addHistoryLog(
    new Date().toLocaleString(),
    'Scheme Registration',
    `${activeScheme} Scheme`,
    'Pending Verification'
  );
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  
  setTimeout(() => {
    toast.classList.remove('show');
  }, 4000);
}

// Add history row
function addHistoryLog(date, type, params, result) {
  const tableBody = document.getElementById('history-table-body');
  const typeClass = type.toLowerCase().includes('disease') ? 'disease' : 
                    type.toLowerCase().includes('crop') ? 'crop' : 
                    type.toLowerCase().includes('fertilizer') ? 'fertilizer' : 'crop';
  
  const icon = typeClass === 'disease' ? 'fa-virus-slash' :
               typeClass === 'fertilizer' ? 'fa-flask' : 'fa-seedling';

  const newRow = document.createElement('tr');
  newRow.innerHTML = `
    <td>${date}</td>
    <td><span class="activity-type ${typeClass}"><i class="fas ${icon}"></i> ${type}</span></td>
    <td>${params}</td>
    <td>${result}</td>
  `;
  
  // Insert at the top of history table
  tableBody.insertBefore(newRow, tableBody.firstChild);
}


// ==========================================================================
// 4. DISEASE DETECTION (AI DIAGNOSIS MOCK)
// ==========================================================================
function initDiseaseDetection() {
  const dropZone = document.getElementById('leaf-drop-zone');
  const fileInput = document.getElementById('leaf-file-input');
  const previewContainer = document.getElementById('upload-preview-container');
  const previewImg = document.getElementById('upload-preview');
  const removeBtn = document.getElementById('remove-upload-btn');
  const analyzeBtn = document.getElementById('analyze-leaf-btn');

  const emptyState = document.getElementById('empty-results-state');
  const resultsContainer = document.getElementById('detection-results');
  const saveBtn = document.getElementById('save-diagnosis-btn');

  // Result fields populated from plant_disease_detection.py's /predict-disease response
  const resultTag = document.getElementById('result-tag');
  const resultDiseaseName = document.getElementById('result-disease-name');
  const resultSciName = document.getElementById('result-sci-name');
  const resultConfidenceBar = document.getElementById('result-confidence-bar');
  const resultConfidenceVal = document.getElementById('result-confidence-val');
  const resultAbout = document.getElementById('result-about');
  const resultTreatmentList = document.getElementById('result-treatment-list');
  const resultPreventionList = document.getElementById('result-prevention-list');

  // Keep a reference to the currently selected file so the analyze
  // handler can upload it.
  let selectedFile = null;
  let lastDiagnosis = null;

  // Trigger file select click
  dropZone.addEventListener('click', () => fileInput.click());

  // Drag and drop events
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length) {
      handleLeafFile(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (fileInput.files.length) {
      handleLeafFile(fileInput.files[0]);
    }
  });

  // Handle uploaded leaf
  function handleLeafFile(file) {
    if (!file.type.startsWith('image/')) {
      showToast('Please upload an image file (JPG, PNG, JPEG)');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      showToast('Image is larger than the 5MB limit.');
      return;
    }

    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      dropZone.style.display = 'none';
      previewContainer.style.display = 'block';
      analyzeBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  // Remove upload handler
  removeBtn.addEventListener('click', () => {
    fileInput.value = '';
    selectedFile = null;
    lastDiagnosis = null;
    previewImg.removeAttribute('src');
    previewContainer.style.display = 'none';
    dropZone.style.display = 'block';
    analyzeBtn.disabled = true;

    // Reset results side
    emptyState.style.display = 'block';
    resultsContainer.style.display = 'none';
  });

  // Render a /predict-disease response into the results card
  function renderDiagnosis(data) {
    const healthy = !!data.healthy;

    resultTag.textContent = healthy ? 'Healthy' : 'Disease Detected';
    resultTag.className = healthy ? 'tag-success' : 'tag-danger';

    resultDiseaseName.textContent = healthy
      ? `${data.crop} — Healthy`
      : `${data.disease}`;
    resultSciName.textContent = data.scientific_name || 'N/A';

    const confidence = Number(data.confidence) || 0;
    resultConfidenceBar.style.width = `${confidence}%`;
    resultConfidenceVal.textContent = `${confidence.toFixed(2)}%`;

    resultAbout.textContent = data.about || 'No additional information available.';

    resultTreatmentList.innerHTML = '';
    (data.treatment && data.treatment.length ? data.treatment : ['No treatment needed.'])
      .forEach((item) => {
        const li = document.createElement('li');
        li.textContent = item;
        resultTreatmentList.appendChild(li);
      });

    resultPreventionList.innerHTML = '';
    (data.prevention && data.prevention.length ? data.prevention : ['Keep monitoring the plant regularly.'])
      .forEach((item) => {
        const li = document.createElement('li');
        li.textContent = item;
        resultPreventionList.appendChild(li);
      });
  }

  // Analyze leaf handler — sends the uploaded image to
  // plant_disease_detection.py's /predict-disease endpoint.
  analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) {
      showToast('Please upload a leaf image first.');
      return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = 'Scanning leaf... <i class="fas fa-spinner fa-spin"></i>';

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const res = await fetch(`${API.disease}/predict-disease`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        const detail = data && data.detail;
        const msg = (detail && (detail.error || detail.message || detail)) || 'Diagnosis failed.';
        throw new Error(msg);
      }

      lastDiagnosis = data;
      renderDiagnosis(data);

      emptyState.style.display = 'none';
      resultsContainer.style.display = 'block';
      showToast('Diagnosis completed successfully!');
    } catch (err) {
      console.error('Disease detection failed:', err);
      showToast(err.message || 'Could not reach the disease detection service.');
    } finally {
      analyzeBtn.innerHTML = 'Scan Leaf for Diseases <i class="fas fa-qrcode"></i>';
      analyzeBtn.disabled = false;
    }
  });

  // Save prediction handler
  saveBtn.addEventListener('click', () => {
    if (!lastDiagnosis) {
      showToast('Run a diagnosis first.');
      return;
    }

    const label = lastDiagnosis.healthy
      ? `${lastDiagnosis.crop} Healthy`
      : `${lastDiagnosis.disease} (${Number(lastDiagnosis.confidence).toFixed(2)}% Confidence)`;

    addHistoryLog(
      new Date().toLocaleString(),
      'Disease Detection',
      `${lastDiagnosis.crop} Leaf Image Upload`,
      label
    );
    showToast('Diagnosis saved to history log.');
  });
}


// ==========================================================================
// 5. CROP RECOMMENDATION
// ==========================================================================
function initCropRecommendation() {
  const form = document.getElementById('crop-rec-form');
  const emptyState = document.getElementById('crop-empty-state');
  const resultCard = document.getElementById('crop-result-card');
  
  const recCropName = document.getElementById('recommended-crop-name');
  const recSuitBar = document.getElementById('crop-suit-bar');
  const recSuitVal = document.getElementById('crop-suit-val');
  const recProfitVal = document.getElementById('crop-profit-val');
  const recTipsList = document.getElementById('crop-tips-list');
  const recResultImg = document.getElementById('crop-result-img');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const n = parseInt(document.getElementById('nitrogen').value);
    const p = parseInt(document.getElementById('phosphorus').value);
    const k = parseInt(document.getElementById('potassium').value);
    const temp = parseFloat(document.getElementById('temperature').value);
    const humidity = parseFloat(document.getElementById('humidity').value);
    const ph = parseFloat(document.getElementById('ph').value);
    const rain = parseFloat(document.getElementById('rainfall').value);

    // Set Loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Computing Suitability... <i class="fas fa-spinner fa-spin"></i>';

    try {
      const res = await fetch(`${API.crop}/crop_recommendation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          N: n,
          P: p,
          K: k,
          temperature: temp,
          humidity: humidity,
          ph: ph,
          rainfall: rain
        })
      });

      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`API error ${res.status}: ${errBody}`);
      }

      const data = await res.json();
      // Shape returned by app.py: { crop: "Rice", advice: { reason, fertilizer,
      // irrigation, diseases, yield, season, additional_tips: [...] } }
      const crop = data.crop || 'Unknown';
      const advice = data.advice || {};

      // The model doesn't return a numeric suitability score or profit figure,
      // so we show it as a confident single recommendation and surface the
      // expected yield text the LLM generated instead of a rupee profit figure.
      recCropName.textContent = crop;
      recSuitBar.style.width = '100%';
      recSuitVal.textContent = 'Recommended';
      recProfitVal.textContent = advice.yield || '—';
      recResultImg.src = CROP_ICONS[crop.toLowerCase()] || DEFAULT_CROP_ICON;

      // Build tips list from the advice fields returned by the LLM
      recTipsList.innerHTML = '';
      const tipLines = [
        advice.reason,
        advice.fertilizer && `Fertilizer: ${advice.fertilizer}`,
        advice.irrigation && `Irrigation: ${advice.irrigation}`,
        advice.diseases && `Watch for: ${advice.diseases}`,
        advice.season && `Season: ${advice.season}`,
        ...(Array.isArray(advice.additional_tips) ? advice.additional_tips : [])
      ].filter(Boolean);

      tipLines.forEach(tip => {
        const li = document.createElement('li');
        li.textContent = tip;
        recTipsList.appendChild(li);
      });

      emptyState.style.display = 'none';
      resultCard.style.display = 'block';

      // Add to history
      addHistoryLog(
        new Date().toLocaleString(),
        'Crop Recommendation',
        `N:${n}, P:${p}, K:${k}, pH:${ph}, Rain:${rain}mm`,
        `Recommended: ${crop}`
      );

      showToast('New crop recommendation calculated!');
    } catch (err) {
      console.error('Crop recommendation failed:', err);
      showToast('Could not reach the crop recommendation service.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Get Recommendation <i class="fas fa-circle-check"></i>';
    }
  });
}


// ==========================================================================
// 6. FERTILIZER RECOMMENDATION
// ==========================================================================
function initFertilizerRecommendation() {
  const form = document.getElementById('fertilizer-form');
  const emptyState = document.getElementById('fert-empty-state');
  const resultCard = document.getElementById('fert-result-card');
  
  const fertRecName = document.getElementById('fert-rec-name');
  const fertReasonVal = document.getElementById('fert-reason-val');
  const fertApplicationVal = document.getElementById('fert-application-val');
  const fertTimeVal = document.getElementById('fert-time-val');
  const fertPrecautionsVal = document.getElementById('fert-precautions-val');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const crop = document.getElementById('fert-crop').value;
    const soil = document.getElementById('fert-soil').value;
    const n = parseFloat(document.getElementById('fert-n').value);
    const p = parseFloat(document.getElementById('fert-p').value);
    const k = parseFloat(document.getElementById('fert-k').value);
    const temperature = parseFloat(document.getElementById('fert-temperature').value);
    const humidity = parseFloat(document.getElementById('fert-humidity').value);
    const moisture = parseFloat(document.getElementById('fert-moisture').value);

    // Set Loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Calculating Nutrients... <i class="fas fa-spinner fa-spin"></i>';

    try {
      const res = await fetch(`${API.fertilizer}/Fertilizer_recommendation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temperature,
          humidity,
          moisture,
          // IMPORTANT: these strings must exactly match the category values
          // (case included) that fertilizer_model.pkl was trained on.
          Soil_type: soil,
          Crop_type: crop,
          nitrogen: n,
          phosphorus: p,
          potassium: k
        })
      });

      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`API error ${res.status}: ${errBody}`);
      }

      const data = await res.json();
      // Shape returned by Fertilizer.py:
      // { recommended_fertilizer: "Urea", explanation: { reason,
      //   application_method, precautions, best_time } }
      const fertilizerName = data.recommended_fertilizer || 'Recommended Fertilizer';
      const explanation = data.explanation || {};

      fertRecName.textContent = fertilizerName;
      if (explanation.raw_response) {
        // The backend's LLM call didn't return valid JSON — show whatever
        // text it did return instead of leaving the card looking broken.
        fertReasonVal.textContent = explanation.raw_response;
        fertApplicationVal.textContent = '—';
        fertTimeVal.textContent = '—';
        fertPrecautionsVal.textContent = '—';
      } else {
        fertReasonVal.textContent = explanation.reason || 'No additional explanation was returned for this recommendation.';
        fertApplicationVal.textContent = explanation.application_method || '—';
        fertTimeVal.textContent = explanation.best_time || '—';
        fertPrecautionsVal.textContent = explanation.precautions || '—';
      }

      emptyState.style.display = 'none';
      resultCard.style.display = 'block';

      // Add to history
      addHistoryLog(
        new Date().toLocaleString(),
        'Fertilizer Rec.',
        `Crop:${crop}, N:${n}, P:${p}, K:${k}`,
        `Recommended: ${fertilizerName}`
      );

      showToast('Fertilizer recommendations calculated!');
    } catch (err) {
      console.error('Fertilizer recommendation failed:', err);
      showToast('Could not reach the fertilizer recommendation service.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Calculate Fertilizer Needs <i class="fas fa-flask"></i>';
    }
  });
}


// ==========================================================================
// 7. AI FARMING ASSISTANT
// ==========================================================================
function initAiAssistant() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const messagesContainer = document.getElementById('chat-messages');

  sendBtn.addEventListener('click', () => {
    sendMessage();
  });

  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const text = input.value.trim();
  if (!text) return;

  // Add user bubble
  appendChatBubble(text, 'user');
  input.value = '';

  // Show a "typing" indicator bubble while we wait for the AI response
  const typingBubble = appendChatBubble('Typing…', 'bot', true);
  sendBtn.disabled = true;

  try {
    const res = await fetch(`${API.assistant}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text })
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      const msg = errBody?.detail?.error || errBody?.detail || 'The AI assistant could not process that question.';
      throw new Error(msg);
    }

    const data = await res.json();
    // Shape returned by ai_assistant.py: { question, answer }
    setBubbleText(typingBubble, data.answer, true);
    typingBubble.classList.remove('typing');

    addHistoryLog(
      new Date().toLocaleString(),
      'AI Assistant',
      text.length > 60 ? text.slice(0, 60) + '…' : text,
      'Answered'
    );
  } catch (err) {
    console.error('AI assistant failed:', err);
    setBubbleText(
      typingBubble,
      "Sorry, I couldn't reach the AI assistant service right now. Please try again in a moment.",
      false
    );
    typingBubble.classList.remove('typing');
    showToast('Could not reach the AI assistant service.');
  } finally {
    sendBtn.disabled = false;
  }
}

function appendChatBubble(text, sender, isTyping = false) {
  const messagesContainer = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}${isTyping ? ' typing' : ''}`;
  bubble.innerHTML = `<div class="bubble-content"></div>`;
  setBubbleText(bubble, text, false);
  messagesContainer.appendChild(bubble);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  return bubble;
}

// Sets a bubble's content, escaping raw text and — for AI responses that
// may contain **bold**, bullet lists, etc. — rendering that light markdown
// as real HTML instead of leaving the literal * / ** characters visible.
function setBubbleText(bubble, text, renderMarkdown) {
  const content = bubble.querySelector('.bubble-content');
  content.innerHTML = renderMarkdown ? markdownToHtml(text) : `<p>${escapeHtml(text)}</p>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Minimal markdown renderer: handles **bold**, bullet lists (* / -),
// numbered lists, and paragraph breaks. Escapes HTML first so raw model
// output can never inject markup.
function markdownToHtml(rawText) {
  const escaped = escapeHtml(rawText);
  const lines = escaped.split(/\r?\n/);

  let html = '';
  let listItems = [];
  let listType = null; // 'ul' | 'ol'

  const flushList = () => {
    if (listItems.length) {
      html += `<${listType}>${listItems.map(li => `<li>${li}</li>`).join('')}</${listType}>`;
      listItems = [];
      listType = null;
    }
  };

  const inlineFormat = (line) => line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  lines.forEach(line => {
    const trimmed = line.trim();
    const bulletMatch = trimmed.match(/^[*-]\s+(.*)/);
    const numberedMatch = trimmed.match(/^\d+[.)]\s+(.*)/);

    if (bulletMatch) {
      if (listType !== 'ul') { flushList(); listType = 'ul'; }
      listItems.push(inlineFormat(bulletMatch[1]));
    } else if (numberedMatch) {
      if (listType !== 'ol') { flushList(); listType = 'ol'; }
      listItems.push(inlineFormat(numberedMatch[1]));
    } else {
      flushList();
      if (trimmed) {
        html += `<p>${inlineFormat(trimmed)}</p>`;
      }
    }
  });
  flushList();

  return html || `<p>${inlineFormat(escaped)}</p>`;
}

// Preset chips trigger
function sendQuickPrompt(promptText) {
  const input = document.getElementById('chat-input');
  input.value = promptText;
  sendMessage();
}


// ==========================================================================
// 8. YIELD PREDICTION
// ==========================================================================
function initYieldPrediction() {
  const form = document.getElementById('yield-form');
  const yieldResultVal = document.getElementById('predicted-yield-val');
  const yieldTotalVal = document.getElementById('predicted-total-val');
  const resultCard = document.getElementById('yield-result-card');
  const errorState = document.getElementById('yield-error-state');
  const errorMessage = document.getElementById('yield-error-message');
  const cropSelect = document.getElementById('yield-crop');
  const soilSelect = document.getElementById('yield-soil');

  // Pull the exact crop / soil-quality labels the model's encoders were
  // trained on, so the dropdowns can never send a value the backend
  // rejects. Falls back to the hardcoded <option> markup if this fails
  // (e.g. the yield service isn't running yet).
  loadYieldOptions(cropSelect, soilSelect);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const crop = document.getElementById('yield-crop').value;
    const area = parseFloat(document.getElementById('yield-area').value);
    const fertilizer = parseFloat(document.getElementById('yield-fertilizer').value);
    const soil = document.getElementById('yield-soil').value;
    const rain = parseFloat(document.getElementById('yield-rainfall').value);

    // Set Loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Predicting Yield... <i class="fas fa-spinner fa-spin"></i>';

    try {
      const res = await fetch(`${API.yieldPrediction}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          // IMPORTANT: Crop and Soil_Quality must exactly match the string
          // classes crop_encoder.pkl / soil_encoder.pkl were fit on
          // (Yield_prediction.py returns a 400 listing valid options if not).
          Crop: crop,
          Area: area,
          Fertilizer: fertilizer,
          Rainfall: rain,
          Soil_Quality: soil
        })
      });

      if (!res.ok) {
        // FastAPI returns { detail: "..." } for HTTPException, so surface
        // that instead of a generic message — it names the exact crop/soil
        // values the encoder was trained on when the value doesn't match.
        const errBody = await res.json().catch(() => ({}));
        const detail = typeof errBody.detail === 'string'
          ? errBody.detail
          : JSON.stringify(errBody.detail) || `API error ${res.status}`;
        throw new Error(detail);
      }

      const data = await res.json();
      // Shape returned by Yield_prediction.py:
      // { predicted_yield_per_acre, total_estimated_yield, model_accuracy,
      //   historical_trend: [...] }
      const yieldPerAcre = data.predicted_yield_per_acre;
      const totalYield = data.total_estimated_yield;

      yieldResultVal.textContent = `${yieldPerAcre.toFixed(1)} Quintals / acre`;
      yieldTotalVal.textContent = `${totalYield.toFixed(0)} Quintals`;

      errorState.style.display = 'none';
      resultCard.style.display = 'block';

      // Log to history
      addHistoryLog(
        new Date().toLocaleString(),
        'Yield Prediction',
        `Crop:${crop}, Area:${area} acres, Soil:${soil}`,
        `Predicted: ${yieldPerAcre.toFixed(1)} Q/ac (Total:${totalYield.toFixed(0)} Q)`
      );

      showToast('Yield prediction updated!');
    } catch (err) {
      console.error('Yield prediction failed:', err);
      errorMessage.textContent = err.message || 'Could not reach the yield prediction service.';
      resultCard.style.display = 'none';
      errorState.style.display = 'block';
      showToast('Yield prediction failed — see details on the right.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Predict Yield <i class="fas fa-chart-line"></i>';
    }
  });
}

// Populates the crop / soil <select> elements from GET /options so the
// values sent to /predict always match what the encoders were trained on.
async function loadYieldOptions(cropSelect, soilSelect) {
  try {
    const res = await fetch(`${API.yieldPrediction}/options`);
    if (!res.ok) return; // keep the static fallback options already in the HTML

    const data = await res.json();
    if (Array.isArray(data.crops) && data.crops.length) {
      cropSelect.innerHTML = data.crops
        .map(c => `<option value="${c}">${c}</option>`)
        .join('');
    }
    if (Array.isArray(data.soil_qualities) && data.soil_qualities.length) {
      soilSelect.innerHTML = data.soil_qualities
        .map(s => `<option value="${s}">${s}</option>`)
        .join('');
    }
  } catch (err) {
    console.error('Could not load yield prediction options, using static defaults:', err);
  }
}


// ==========================================================================
// 9. MARKET ANALYSIS
// ==========================================================================
// This panel does not exist in the current HTML yet. Add a form + result
// markup with these IDs to your dashboard (mirroring the crop/fertilizer
// panels' structure):
//
// <form id="market-form">
//   <input id="market-crop-input" type="text" placeholder="e.g. Wheat" required>
//   <button type="submit">Check Market Prices</button>
// </form>
// <div id="market-empty-state">No analysis yet.</div>
// <div id="market-result-card" style="display:none;">
//   <p id="market-price-range"></p>
//   <p id="market-best-market"></p>
//   <p id="market-worst-market"></p>
//   <p id="market-advice"></p>
//   <table><tbody id="market-prices-table-body"></tbody></table>
// </div>
function initMarketAnalysis() {
  const form = document.getElementById('market-form');
  if (!form) return; // panel not added to this page yet — skip silently

  const cropInput = document.getElementById('market-crop-input');
  const emptyState = document.getElementById('market-empty-state');
  const resultCard = document.getElementById('market-result-card');

  const priceRangeEl = document.getElementById('market-price-range');
  const bestMarketEl = document.getElementById('market-best-market');
  const worstMarketEl = document.getElementById('market-worst-market');
  const adviceEl = document.getElementById('market-advice');
  const tableBody = document.getElementById('market-prices-table-body');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const crop = cropInput.value.trim();
    if (!crop) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Checking Mandi Prices... <i class="fas fa-spinner fa-spin"></i>';

    try {
      const res = await fetch(`${API.market}/market-analysis/${encodeURIComponent(crop)}`);

      if (!res.ok) {
        // market_analysis.py returns 404 with a helpful message when no
        // records are found for the crop spelling given.
        const errBody = await res.json().catch(() => ({}));
        const msg = errBody?.detail?.message || `No market data found for "${crop}".`;
        showToast(msg);
        emptyState.style.display = 'block';
        resultCard.style.display = 'none';
        return;
      }

      const data = await res.json();
      // Shape returned by market_analysis.py:
      // { crop, market_prices: [{state,district,market,min_price,max_price,
      //   modal_price}], analysis: {price_range,best_market,worst_market,
      //   advice}, cached }
      const analysis = data.analysis || {};

      priceRangeEl.textContent = analysis.price_range || 'N/A';
      bestMarketEl.textContent = analysis.best_market ? `Best: ${analysis.best_market}` : '';
      worstMarketEl.textContent = analysis.worst_market ? `Worst: ${analysis.worst_market}` : '';
      adviceEl.textContent = analysis.advice || '';

      tableBody.innerHTML = '';
      (data.market_prices || []).forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${row.market || ''}</td>
          <td>${row.state || ''}</td>
          <td>${row.min_price || ''}</td>
          <td>${row.max_price || ''}</td>
          <td>${row.modal_price || ''}</td>
        `;
        tableBody.appendChild(tr);
      });

      emptyState.style.display = 'none';
      resultCard.style.display = 'block';

      addHistoryLog(
        new Date().toLocaleString(),
        'Market Analysis',
        `Crop: ${data.crop}`,
        analysis.price_range || 'Checked'
      );

      showToast(data.cached ? 'Loaded cached market data.' : 'Market analysis updated!');
    } catch (err) {
      console.error('Market analysis failed:', err);
      showToast('Could not reach the market analysis service.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Check Market Prices <i class="fas fa-chart-simple"></i>';
    }
  });
}


// ==========================================================================
// 10. WEATHER FORECAST
// ==========================================================================
function initWeatherForecast() {
  const form = document.getElementById('weather-form');
  if (!form) return; // panel not present — skip silently

  const cityInput = document.getElementById('weather-city-input');
  const loadingState = document.getElementById('weather-loading-state');
  const errorState = document.getElementById('weather-error-state');
  const errorMessageEl = document.getElementById('weather-error-message');
  const resultsWrap = document.getElementById('weather-results');
  const resultCityEl = document.getElementById('weather-result-city');
  const dayGrid = document.getElementById('five-day-grid');
  const adviceGrid = document.getElementById('advice-forecast-grid');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const city = cityInput.value.trim();
    if (!city) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Fetching... <i class="fas fa-spinner fa-spin"></i>';

    resultsWrap.style.display = 'none';
    errorState.style.display = 'none';
    loadingState.style.display = 'block';

    try {
      const res = await fetch(`${API.weather}/weather/${encodeURIComponent(city)}`);
      const data = await res.json();

      if (!res.ok || data.error) {
        // weather_service.py returns either an HTTPException (via !res.ok)
        // for a bad city, or a 200 body with an "error" key if the AI advice
        // step itself throws.
        const detail = data.detail || data.error;
        const msg = (detail && (detail.message || detail)) || `Could not find weather data for "${city}".`;
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }

      renderWeatherResults(data, { resultCityEl, dayGrid, adviceGrid });
      updateNavWeatherWidget(data.forecast);

      resultsWrap.style.display = 'block';

      addHistoryLog(
        new Date().toLocaleString(),
        'Weather Forecast',
        `City: ${data.city || city}`,
        'Forecast & AI advice retrieved'
      );

      showToast('Weather forecast updated!');
    } catch (err) {
      console.error('Weather forecast failed:', err);
      errorMessageEl.textContent = err.message || 'Could not reach the weather service.';
      errorState.style.display = 'block';
      showToast('Could not reach the weather forecast service.');
    } finally {
      loadingState.style.display = 'none';
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-magnifying-glass-location"></i> Get Forecast';
    }
  });
}

// Group the raw 3-hour interval forecast list from weather_service.py into
// one card per calendar day, and render the AI advice grid.
function renderWeatherResults(data, { resultCityEl, dayGrid, adviceGrid }) {
  resultCityEl.textContent = data.city ? `— ${data.city}` : '';

  const days = groupForecastByDay(data.forecast || []);

  dayGrid.innerHTML = '';
  days.slice(0, 5).forEach((day, index) => {
    const card = document.createElement('div');
    card.className = 'forecast-day-card';
    card.innerHTML = `
      <span class="day-name">${index === 0 ? 'Today' : day.label}</span>
      <img src="${weatherIconFor(day.description)}" alt="${day.description}" class="day-weather-icon">
      <strong class="day-temp">${Math.round(day.maxTemp)}°C</strong>
      <span class="day-pop"><i class="fas fa-droplet ${day.rainChance >= 40 ? 'text-primary' : ''}"></i> ${day.rainChance}% Rain</span>
    `;
    dayGrid.appendChild(card);
  });

  const advice = data.ai_advice || {};
  const adviceItems = [
    { key: 'irrigation', title: 'Irrigation', icon: 'fa-droplet', color: 'text-primary' },
    { key: 'fertilizer', title: 'Fertilizer', icon: 'fa-flask', color: 'text-success' },
    { key: 'pesticide', title: 'Pesticide', icon: 'fa-bug', color: 'text-danger' },
    { key: 'crop_care', title: 'Crop Care', icon: 'fa-seedling', color: 'text-success' },
  ];

  adviceGrid.innerHTML = '';
  adviceItems
    .filter(item => advice[item.key])
    .forEach(item => {
      const el = document.createElement('div');
      el.className = 'advice-item';
      el.innerHTML = `
        <i class="fas ${item.icon} ${item.color}"></i>
        <div>
          <h4>${item.title}</h4>
          <p>${advice[item.key]}</p>
        </div>
      `;
      adviceGrid.appendChild(el);
    });

  if (!adviceGrid.children.length) {
    adviceGrid.innerHTML = '<p class="text-muted">No AI advice available for this forecast.</p>';
  }
}

function groupForecastByDay(forecastList) {
  const byDate = {};

  forecastList.forEach(item => {
    // item.date looks like "2026-08-12 15:00:00"
    const [datePart, timePart] = item.date.split(' ');
    if (!byDate[datePart]) byDate[datePart] = [];
    byDate[datePart].push({ ...item, timePart });
  });

  return Object.keys(byDate).sort().map(datePart => {
    const entries = byDate[datePart];
    const maxTemp = Math.max(...entries.map(e => e.temperature));
    const rainyEntries = entries.filter(e => e.rain > 0 || /rain|drizzle|thunderstorm/i.test(e.weather));
    const rainChance = Math.round((rainyEntries.length / entries.length) * 100);

    // Prefer the entry closest to midday for the representative description/icon
    const midday = entries.reduce((closest, e) => {
      const hour = parseInt(e.timePart.split(':')[0], 10);
      const closestHour = parseInt(closest.timePart.split(':')[0], 10);
      return Math.abs(hour - 12) < Math.abs(closestHour - 12) ? e : closest;
    }, entries[0]);

    const dateObj = new Date(datePart + 'T00:00:00');
    const label = dateObj.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });

    return {
      date: datePart,
      label,
      maxTemp,
      rainChance,
      description: midday.weather,
    };
  });
}

// Keep the small weather widget in the top navbar in sync with the latest search
function updateNavWeatherWidget(forecastList) {
  if (!forecastList || !forecastList.length) return;
  const widget = document.querySelector('.nav-weather-widget');
  if (!widget) return;

  const tempEl = widget.querySelector('.weather-temp-mini');
  const iconEl = widget.querySelector('.weather-icon-mini');

  if (tempEl) tempEl.textContent = `${Math.round(forecastList[0].temperature)}°C`;
  if (iconEl) iconEl.src = weatherIconFor(forecastList[0].weather);
}