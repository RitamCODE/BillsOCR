// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, initializing app...');
  
  const form = document.getElementById('upload-form');
  const input = document.getElementById('file-input');
  const statusEl = document.getElementById('status');
  const resultsSection = document.getElementById('results');
  const resultsTableBody = document.querySelector('#results-table tbody');
  const downloadBtn = document.getElementById('download-btn');
  const clearBtn = document.getElementById('clear-btn');
  const emptyState = document.getElementById('empty-state');
  const modal = document.getElementById('detail-modal');
  const modalBody = document.getElementById('modal-body');
  const modalClose = document.querySelector('.modal-close');
  const fileLabelText = document.getElementById('file-label-text');
  const selectedFilesDiv = document.getElementById('selected-files');

  // Check if all elements exist
  if (!form || !input || !statusEl) {
    console.error('Required elements not found!', { form, input, statusEl });
    alert('Error: Page elements not found. Please refresh the page.');
    return;
  }
  
  console.log('All elements found, setting up event listeners...');

  // Store all results in memory
  let allResults = [];

  function setStatus(text, type = 'info') {
    statusEl.textContent = text;
    statusEl.className = `status ${type}`;
  }

  function formatCurrency(amount) {
    if (!amount) return '-';
    const num = parseFloat(amount);
    if (isNaN(num)) return amount;
    return `$${num.toFixed(2)}`;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      // Handle YYYY-MM-DD format
      if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
        const [year, month, day] = dateStr.split('-');
        const date = new Date(year, month - 1, day);
        if (!isNaN(date.getTime())) {
          return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        }
      }
      // Try parsing as-is
      const date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
      }
      return dateStr;
    } catch {
      return dateStr;
    }
  }

  function showResults(newResults) {
    // Add new results to the collection
    allResults = [...allResults, ...newResults];
    
    // Re-render table
    renderTable();
    
    updateEmptyState();
  }

  function renderTable() {
    resultsTableBody.innerHTML = '';
    
    allResults.forEach((r, index) => {
      const tr = document.createElement('tr');
      const hasError = r.error;
      const rowClass = hasError ? 'error-row' : '';
      
      tr.innerHTML = `
        <td>${index + 1}</td>
        <td class="filename-cell">${r.filename || 'Unknown'}</td>
        <td>${hasError ? `<span class="error-text">Error: ${r.error}</span>` : (r.vendor || '<em>Not detected</em>')}</td>
        <td>${hasError ? '-' : formatDate(r.date)}</td>
        <td class="total-cell">${hasError ? '-' : formatCurrency(r.total)}</td>
        <td>
          ${hasError ? '' : `<button class="btn-small view-detail" data-index="${index}">View</button>`}
          <button class="btn-small btn-danger delete-row" data-index="${index}">Delete</button>
        </td>
      `;
      if (rowClass) tr.classList.add(rowClass);
      resultsTableBody.appendChild(tr);
    });
    
    // Attach event listeners
    document.querySelectorAll('.view-detail').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.index);
        showDetailModal(allResults[index]);
      });
    });
    
    document.querySelectorAll('.delete-row').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.index);
        allResults.splice(index, 1);
        renderTable();
        updateEmptyState();
        setStatus('Bill removed from list.', 'info');
      });
    });
  }

  function updateEmptyState() {
    const table = resultsTableBody.closest('table');
    if (allResults.length === 0) {
      if (table) table.classList.add('hidden');
      emptyState.classList.remove('hidden');
    } else {
      if (table) table.classList.remove('hidden');
      emptyState.classList.add('hidden');
    }
  }

  function showDetailModal(result) {
    if (!modal || !modalBody) return;
    modalBody.innerHTML = `
      <div class="detail-section">
        <h4>Filename</h4>
        <p>${result.filename || 'Unknown'}</p>
      </div>
      <div class="detail-section">
        <h4>Vendor</h4>
        <p>${result.vendor || 'Not detected'}</p>
      </div>
      <div class="detail-section">
        <h4>Date</h4>
        <p>${formatDate(result.date) || 'Not detected'}</p>
      </div>
      <div class="detail-section">
        <h4>Total</h4>
        <p class="total-large">${formatCurrency(result.total)}</p>
      </div>
      <div class="detail-section">
        <h4>Processed At</h4>
        <p>${new Date(result.processed_at).toLocaleString()}</p>
      </div>
      <div class="detail-section">
        <h4>Raw OCR Text</h4>
        <pre class="raw-text">${result.raw_text || 'No text extracted'}</pre>
      </div>
    `;
    modal.classList.remove('hidden');
    console.log('Modal shown');
  }

  function hideDetailModal() {
    if (!modal) return;
    modal.classList.add('hidden');
    console.log('Modal hidden');
  }

  // Add click handler to file input for debugging
  input.addEventListener('change', (e) => {
    console.log('File selected:', e.target.files.length, 'file(s)');
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      if (fileLabelText) {
        fileLabelText.textContent = `${files.length} file(s) selected`;
      }
      if (selectedFilesDiv) {
        selectedFilesDiv.innerHTML = '<strong>Selected files:</strong><br>' + 
          files.map(f => `• ${f.name}`).join('<br>');
        selectedFilesDiv.style.display = 'block';
      }
      setStatus(`Selected ${files.length} file(s). Click "Upload & Extract" to process.`, 'info');
    } else {
      if (fileLabelText) {
        fileLabelText.textContent = 'Choose Files';
      }
      if (selectedFilesDiv) {
        selectedFilesDiv.style.display = 'none';
      }
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    console.log('Form submitted');
    
    if (!input.files || input.files.length === 0) {
      setStatus('Please select one or more images.', 'warn');
      console.warn('No files selected');
      return;
    }
    
    console.log('Processing', input.files.length, 'file(s)...');

    const data = new FormData();
    for (const f of input.files) data.append('files', f);

    setStatus('Uploading and extracting...', 'info');
    try {
      const res = await fetch('/api/extract', { method: 'POST', body: data });
      if (!res.ok) {
        let errorDetail = `Request failed with status ${res.status}`;
        try {
          const error = await res.json();
          errorDetail = error.detail || errorDetail;
          console.error('Server error response:', error);
        } catch {
          const text = await res.text().catch(() => '');
          console.error('Server error text:', text);
          errorDetail = text || errorDetail;
        }
        throw new Error(errorDetail);
      }
      const json = await res.json();
      const results = json.results || [];
      showResults(results);
      
      const successCount = results.filter(r => !r.error).length;
      const errorCount = results.filter(r => r.error).length;
      
      if (errorCount > 0) {
        setStatus(`Processed ${successCount} bill(s) successfully, ${errorCount} error(s).`, 'warn');
      } else {
        setStatus(`Successfully processed ${successCount} bill(s)!`, 'success');
      }
      input.value = ''; // Clear file input
      if (fileLabelText) fileLabelText.textContent = 'Choose Files';
      if (selectedFilesDiv) selectedFilesDiv.style.display = 'none';
    } catch (err) {
      console.error('Upload error:', err);
      let errorMsg = err.message || 'Unknown error occurred';
      
      // Try to get more details from the error
      if (err.response) {
        try {
          const errorData = await err.response.json();
          errorMsg = errorData.detail || errorMsg;
        } catch {
          errorMsg = `HTTP ${err.response.status}: ${errorMsg}`;
        }
      }
      
      setStatus(`Error: ${errorMsg}`, 'error');
      
      // Show error in results table if we got partial results
      if (err.partialResults) {
        showResults(err.partialResults);
      }
    }
  });

  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      window.location.href = '/api/download';
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to clear all results?')) {
        allResults = [];
        renderTable();
        updateEmptyState();
        setStatus('All results cleared.', 'info');
      }
    });
  }

  if (modalClose) {
    modalClose.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideDetailModal();
    });
  }

  if (modal) {
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        hideDetailModal();
      }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        hideDetailModal();
      }
    });
    
    // Ensure modal is hidden on load
    modal.classList.add('hidden');
  }

  // Initialize
  updateEmptyState();
  console.log('App initialized successfully!');
});
