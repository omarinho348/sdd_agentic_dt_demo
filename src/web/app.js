const form = document.querySelector('#generator-form');
const description = document.querySelector('#description');
const missingSection = document.querySelector('#missing-section');
const missingFields = document.querySelector('#missing-fields');
const status = document.querySelector('#status');
const generateButton = document.querySelector('#generate-button');
const emptyState = document.querySelector('#empty-state');
const resultContent = document.querySelector('#result-content');
const interfaceList = document.querySelector('#interface-list');
const contractBadge = document.querySelector('#contract-badge');
const downloadButton = document.querySelector('#download-button');
const sampleButton = document.querySelector('#sample-button');
const telemetryStatus = document.querySelector('#telemetry-status');
const telemetryStation1 = document.querySelector('#telemetry-station1');
const telemetryStation2 = document.querySelector('#telemetry-station2');
const telemetryQueue = document.querySelector('#telemetry-queue');
const telemetryTime = document.querySelector('#telemetry-time');

let parameters = {};
let latestDocument = null;

connectTelemetry();

const labels = {
  station1_name: ['Assembly station name', 'text', 'e.g. Assembly Station'],
  station1_cycle_time: ['Assembly cycle time (seconds)', 'number', 'e.g. 5'],
  station2_name: ['Packaging station name', 'text', 'e.g. Packaging Station'],
  station2_cycle_time: ['Packaging cycle time (seconds)', 'number', 'e.g. 8'],
  queue_capacity: ['Queue capacity (items)', 'number', 'e.g. 3'],
};

sampleButton.addEventListener('click', () => {
  description.value = 'Create a line with assembly and packaging stations.';
  description.dispatchEvent(new Event('input'));
  description.focus();
});

description.addEventListener('input', () => {
  parameters = {};
  latestDocument = null;
  missingSection.hidden = true;
  missingFields.replaceChildren();
  emptyState.hidden = false;
  resultContent.hidden = true;
  contractBadge.textContent = 'Waiting';
  contractBadge.classList.remove('is-valid');
  setStatus('Ready when you are.');
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  setBusy(true);
  clearStatus();

  try {
    if (Object.keys(parameters).length === 0) {
      const extracted = await request('/api/extract', { description: description.value });
      parameters = extracted.parameters;
      renderMissing(extracted.missing_fields);
      if (extracted.missing_fields.length > 0) {
        setStatus('Add the highlighted values to continue.', 'needs-input');
        setBusy(false);
        return;
      }
    } else {
      readMissingFields();
    }

    const generated = await request('/api/generate', { parameters });
    latestDocument = generated.document;
    renderContract(latestDocument);
    setStatus('Contract generated and saved to assembly_line.json.', 'success');
    missingSection.hidden = true;
  } catch (error) {
    showErrors(error.errors || [{ field: 'request', message: error.message }]);
    setStatus('Check the highlighted fields and try again.', 'error');
  } finally {
    setBusy(false);
  }
});

function renderMissing(fields) {
  missingFields.replaceChildren();
  fields.forEach((field) => {
    const [label, type, placeholder] = labels[field];
    const wrapper = document.createElement('label');
    wrapper.className = 'missing-field';
    wrapper.dataset.field = field;
    wrapper.innerHTML = `<span>${label}</span><input name="${field}" type="${type}" placeholder="${placeholder}" step="any" required><small></small>`;
    missingFields.append(wrapper);
  });
  missingSection.hidden = fields.length === 0;
}

function readMissingFields() {
  missingFields.querySelectorAll('input').forEach((input) => {
    parameters[input.name] = input.value;
  });
}

function renderContract(contractDocument) {
  emptyState.hidden = true;
  resultContent.hidden = false;
  contractBadge.textContent = 'Validated';
  contractBadge.classList.add('is-valid');
  interfaceList.replaceChildren();

  contractDocument.forEach((interfaceModel, index) => {
    const article = document.createElement('article');
    article.className = 'interface-card';
    const type = index === 0 ? 'Queue' : `Station 0${index}`;
    article.innerHTML = `<div class="interface-top"><div><span class="interface-kind">${type}</span><h3></h3></div><span class="interface-id"></span></div><div class="content-list"></div>`;
    article.querySelector('h3').textContent = interfaceModel.displayName;
    article.querySelector('.interface-id').textContent = interfaceModel['@id'];
    const contentList = article.querySelector('.content-list');
    interfaceModel.contents.forEach((content) => {
      const row = document.createElement('div');
      row.className = 'content-row';
      row.innerHTML = `<span class="content-type">${content['@type']}</span><strong></strong><span class="content-schema"></span>`;
      row.querySelector('strong').textContent = content.name;
      row.querySelector('.content-schema').textContent = content.schema;
      contentList.append(row);
    });
    interfaceList.append(article);
  });
}

function showErrors(errors) {
  errors.forEach((error) => {
    const field = missingFields.querySelector(`[name="${error.field}"]`);
    if (field) {
      field.classList.add('has-error');
      field.nextElementSibling.textContent = error.message;
    }
  });
}

async function request(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw payload;
  return payload;
}

function setBusy(isBusy) {
  generateButton.disabled = isBusy;
  generateButton.querySelector('span').textContent = isBusy ? 'Working…' : 'Generate model';
}

function setStatus(message, kind) {
  status.textContent = message;
  status.className = `status ${kind || ''}`;
}

function clearStatus() {
  missingFields.querySelectorAll('input').forEach((input) => input.classList.remove('has-error'));
  missingFields.querySelectorAll('small').forEach((item) => { item.textContent = ''; });
}

downloadButton.addEventListener('click', () => {
  if (!latestDocument) return;
  const blob = new Blob([JSON.stringify(latestDocument, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'assembly_line.json';
  link.click();
  URL.revokeObjectURL(link.href);
});

function connectTelemetry() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/telemetry`);
  socket.addEventListener('open', () => {
    telemetryStatus.textContent = 'Waiting for model';
    telemetryStatus.classList.remove('is-valid');
  });
  socket.addEventListener('message', (event) => {
    const frame = JSON.parse(event.data);
    telemetryStation1.textContent = frame.station1_state;
    telemetryStation2.textContent = frame.station2_state;
    telemetryQueue.textContent = frame.queue_occupancy;
    telemetryTime.textContent = `${frame.timestamp}s`;
    telemetryStatus.textContent = 'Running';
    telemetryStatus.classList.add('is-valid');
  });
  socket.addEventListener('close', () => {
    telemetryStatus.textContent = 'Offline';
    telemetryStatus.classList.remove('is-valid');
  });
}
