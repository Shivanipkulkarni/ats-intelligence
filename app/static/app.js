const resumeInput = document.getElementById('resumeText');
const jobInput = document.getElementById('jobDescription');
const resumePDFInput = document.getElementById('resumePDF');
const jdPDFInput = document.getElementById('jdPDF');
const semanticResult = document.getElementById('semanticResult');
const careerResult = document.getElementById('careerResult');
const companyResult = document.getElementById('companyResult');
const coreResult = document.getElementById('coreResult');

const buildResultHtml = (title, payload) => {
  if (!payload) {
    return '<div class="result-body">No result yet.</div>';
  }

  const rows = Object.entries(payload).map(([key, value]) => {
    if (Array.isArray(value)) {
      value = value.map((item) => `<li>${item}</li>`).join('');
      return `<div class="result-row"><strong>${key}</strong><ul>${value}</ul></div>`;
    }
    if (typeof value === 'object' && value !== null) {
      value = Object.entries(value)
        .map(([subKey, subValue]) => `<li><strong>${subKey}</strong>: ${subValue}</li>`)
        .join('');
      return `<div class="result-row"><strong>${key}</strong><ul>${value}</ul></div>`;
    }
    return `<div class="result-row"><strong>${key}</strong>: ${value}</div>`;
  });

  return `<div class="result-body">${rows.join('')}</div>`;
};

const showError = (card, message) => {
  card.innerHTML = `<div class="result-body"><strong>Error:</strong> ${message}</div>`;
};

const apiPost = async (url, body) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || response.statusText);
  }

  return response.json();
};

const getPayload = () => ({
  resume_text: resumeInput.value.trim(),
  job_description: jobInput.value.trim(),
});

const runSemantic = async () => {
  try {
    semanticResult.innerHTML = '<div class="result-body">Computing semantic fit…</div>';
    const payload = getPayload();
    const result = await apiPost('/api/v1/semantic/fit', payload);
    semanticResult.innerHTML = buildResultHtml('Semantic Fit', result);
  } catch (error) {
    showError(semanticResult, error.message);
  }
};

const runCareer = async () => {
  try {
    careerResult.innerHTML = '<div class="result-body">Analyzing career trajectory…</div>';
    const payload = { resume_text: resumeInput.value.trim(), roles: [] };
    const result = await apiPost('/api/v1/career/trajectory', payload);
    careerResult.innerHTML = buildResultHtml('Career Trajectory', result);
  } catch (error) {
    showError(careerResult, error.message);
  }
};

const runCompany = async () => {
  try {
    companyResult.innerHTML = '<div class="result-body">Evaluating company context…</div>';
    const payload = { resume_text: resumeInput.value.trim(), companies: [] };
    const result = await apiPost('/api/v1/company/context', payload);
    companyResult.innerHTML = buildResultHtml('Company Context', result);
  } catch (error) {
    showError(companyResult, error.message);
  }
};

const runCore = async () => {
  try {
    coreResult.innerHTML = '<div class="result-body">Computing overall candidate score…</div>';
    const payload = { resume_text: resumeInput.value.trim(), job_description: jobInput.value.trim(), roles: [], companies: [], weights: null };
    const result = await apiPost('/api/v1/candidate/score', payload);
    coreResult.innerHTML = buildResultHtml('Core Candidate Score', result);
  } catch (error) {
    showError(coreResult, error.message);
  }
};

const handleResumePDFUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/pdf/extract-resume', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.detail || 'Failed to extract resume PDF');
    }
    
    const data = await response.json();
    resumeInput.value = data.resume_text;
  } catch (error) {
    alert('Error extracting resume PDF: ' + error.message);
  }
};

const handleJDPDFUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/pdf/extract-jd', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.detail || 'Failed to extract job description PDF');
    }
    
    const data = await response.json();
    jobInput.value = data.job_description;
  } catch (error) {
    alert('Error extracting job description PDF: ' + error.message);
  }
};

const scorePDFs = async () => {
  try {
    if (!resumePDFInput.files[0] || !jdPDFInput.files[0]) {
      alert('Please upload both resume and job description PDFs');
      return;
    }
    
    semanticResult.innerHTML = '<div class="result-body">Processing PDFs and computing scores…</div>';
    careerResult.innerHTML = '<div class="result-body">Processing…</div>';
    companyResult.innerHTML = '<div class="result-body">Processing…</div>';
    coreResult.innerHTML = '<div class="result-body">Processing…</div>';
    
    const formData = new FormData();
    formData.append('resume_pdf', resumePDFInput.files[0]);
    formData.append('jd_pdf', jdPDFInput.files[0]);
    
    const response = await fetch('/api/v1/pdf/score', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.detail || 'Failed to score PDFs');
    }
    
    const result = await response.json();
    
    semanticResult.innerHTML = buildResultHtml('Semantic Fit', result.semantic_fit);
    careerResult.innerHTML = buildResultHtml('Career Trajectory', result.career_trajectory);
    companyResult.innerHTML = buildResultHtml('Company Context', result.company_context);
    coreResult.innerHTML = buildResultHtml('Overall Score', result.overall_score);
  } catch (error) {
    showError(semanticResult, error.message);
    showError(careerResult, error.message);
    showError(companyResult, error.message);
    showError(coreResult, error.message);
  }
};

const bind = () => {
  document.getElementById('runSemantic').addEventListener('click', runSemantic);
  document.getElementById('runCareer').addEventListener('click', runCareer);
  document.getElementById('runCompany').addEventListener('click', runCompany);
  document.getElementById('runCore').addEventListener('click', runCore);
  document.getElementById('scorePDFs').addEventListener('click', scorePDFs);
  
  // PDF upload handlers
  resumePDFInput.addEventListener('change', handleResumePDFUpload);
  jdPDFInput.addEventListener('change', handleJDPDFUpload);
};

bind();
