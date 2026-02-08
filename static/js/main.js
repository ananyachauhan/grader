// Global state
let rubrics = [];
let documents = [];
let selectedDocs = new Set();
let gradingResults = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRubrics();
    setupEventListeners();
});

// Load rubrics
async function loadRubrics() {
    try {
        const response = await fetch('/api/grading/rubrics');
        const data = await response.json();
        rubrics = data.rubrics;
        
        const select = document.getElementById('rubric-select');
        select.innerHTML = '<option value="">Select a rubric...</option>';
        rubrics.forEach(rubric => {
            const option = document.createElement('option');
            option.value = rubric.filename;
            option.textContent = `${rubric.name} (${rubric.total_points} pts)`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading rubrics:', error);
        alert('Error loading rubrics: ' + error.message);
    }
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('load-docs-btn').addEventListener('click', loadDocuments);
    document.getElementById('grade-btn').addEventListener('click', gradeDocuments);
    document.getElementById('select-all').addEventListener('change', toggleSelectAll);
    document.getElementById('open-all-btn').addEventListener('click', openAllDocuments);
    document.getElementById('export-btn').addEventListener('click', exportResults);
    document.getElementById('search-docs').addEventListener('input', filterResults);
    document.getElementById('filter-status').addEventListener('change', filterResults);
    document.getElementById('rubric-select').addEventListener('change', updateRubricControls);
    document.getElementById('rubric-upload').addEventListener('change', handleRubricUpload);
    document.getElementById('delete-rubric-btn').addEventListener('click', deleteRubric);
}

// Load documents from folder
async function loadDocuments() {
    const folderId = document.getElementById('folder-id').value || 
                     prompt('Enter Google Drive Folder ID:');
    
    if (!folderId) return;
    
    try {
        showProgress('Loading documents...', 0);
        const response = await fetch(`/api/documents/list?folder_id=${folderId}`);
        const data = await response.json();
        
        if (data.error) {
            alert('Error: ' + data.error);
            hideProgress();
            return;
        }
        
        documents = data.documents;
        displayDocuments();
        document.getElementById('documents-container').classList.remove('hidden');
        hideProgress();
    } catch (error) {
        alert('Error loading documents: ' + error.message);
        hideProgress();
    }
}

// Display documents list
function displayDocuments() {
    const container = document.getElementById('documents-list');
    container.innerHTML = '';
    
    if (documents.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">No documents found in this folder.</p>';
        return;
    }
    
    documents.forEach(doc => {
        const item = document.createElement('div');
        item.className = 'document-item';
        item.innerHTML = `
            <input type="checkbox" value="${doc.id}" data-name="${doc.name}">
            <span class="document-item-name">${doc.name}</span>
            <a href="${doc.url}" target="_blank" class="btn-secondary" style="padding: 5px 10px; text-decoration: none; font-size: 12px;">Open</a>
        `;
        
        const checkbox = item.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', updateSelection);
        
        container.appendChild(item);
    });
}

// Update selection
function updateSelection(e) {
    const docId = e.target.value;
    if (e.target.checked) {
        selectedDocs.add(docId);
    } else {
        selectedDocs.delete(docId);
    }
    updateSelectedCount();
    updateRubricControls();
}

// Toggle select all
function toggleSelectAll(e) {
    const checkboxes = document.querySelectorAll('#documents-list input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = e.target.checked;
        if (e.target.checked) {
            selectedDocs.add(cb.value);
        } else {
            selectedDocs.delete(cb.value);
        }
    });
    updateSelectedCount();
    updateRubricControls();
}

// Update selected count
function updateSelectedCount() {
    document.getElementById('selected-count').textContent = `${selectedDocs.size} selected`;
}

// Update grade button and delete button state
function updateRubricControls() {
    const rubric = document.getElementById('rubric-select').value;
    const gradeBtn = document.getElementById('grade-btn');
    const deleteBtn = document.getElementById('delete-rubric-btn');
    
    gradeBtn.disabled = !rubric || selectedDocs.size === 0;
    deleteBtn.disabled = !rubric;
}

// Grade documents
async function gradeDocuments() {
    const rubricFilename = document.getElementById('rubric-select').value;
    const docIds = Array.from(selectedDocs);
    const customInstructions = document.getElementById('custom-instructions').value;
    
    if (!rubricFilename || docIds.length === 0) {
        alert('Please select a rubric and at least one document');
        return;
    }
    
    if (!confirm(`Grade ${docIds.length} document(s)? This will insert comments and scores into the documents.`)) {
        return;
    }
    
    // Show progress
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressContainer.classList.remove('hidden');
    document.getElementById('grade-btn').disabled = true;
    
    try {
        showProgress(`Grading ${docIds.length} documents...`, 10);
        
        const requestBody = {
            doc_ids: docIds,
            rubric_filename: rubricFilename
        };
        
        // Add custom instructions if provided
        if (customInstructions && customInstructions.trim()) {
            requestBody.custom_instructions = customInstructions.trim();
        }
        
        const response = await fetch('/api/grading/grade/batch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        showProgress('Grading complete!', 100);
        
        gradingResults = data.results;
        displayResults();
        
        // Show results section
        document.getElementById('results-section').classList.remove('hidden');
        
        // Scroll to results
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
        
        setTimeout(() => {
            hideProgress();
        }, 1000);
        
    } catch (error) {
        alert('Error grading documents: ' + error.message);
        hideProgress();
    } finally {
        document.getElementById('grade-btn').disabled = false;
    }
}

// Show progress
function showProgress(text, percent) {
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressContainer.classList.remove('hidden');
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

// Hide progress
function hideProgress() {
    document.getElementById('progress-container').classList.add('hidden');
}

// Display results
function displayResults() {
    const successResults = gradingResults.filter(r => r.success);
    const successCount = successResults.length;
    const avgScore = successCount > 0
        ? successResults.reduce((sum, r) => sum + (r.total_score || 0), 0) / successCount
        : 0;
    
    document.getElementById('total-graded').textContent = gradingResults.length;
    document.getElementById('avg-score').textContent = Math.round(avgScore);
    document.getElementById('success-count').textContent = successCount;
    
    // Build table
    const table = document.getElementById('results-table');
    table.innerHTML = `
        <div class="results-table">
            <table>
                <thead>
                    <tr>
                        <th>Document</th>
                        <th>Score</th>
                        <th>Comments</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${gradingResults.map(result => {
                        const doc = documents.find(d => d.id === result.doc_id);
                        const docName = doc ? doc.name : result.doc_id;
                        const docUrl = doc ? doc.url : `https://docs.google.com/document/d/${result.doc_id}`;
                        
                        return `
                            <tr>
                                <td>${docName}</td>
                                <td>${result.total_score || 'N/A'}</td>
                                <td>${result.comments_count || 0}</td>
                                <td class="${result.success ? 'status-success' : 'status-error'}">
                                    ${result.success ? '✓ Success' : '✗ Error'}
                                </td>
                                <td>
                                    <a href="${docUrl}" target="_blank" class="btn-secondary" style="padding: 5px 10px; text-decoration: none; font-size: 12px;">Open</a>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// Filter results
function filterResults() {
    const search = document.getElementById('search-docs').value.toLowerCase();
    const status = document.getElementById('filter-status').value;
    
    // Implementation for filtering table rows
    const rows = document.querySelectorAll('#results-table tbody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matchesSearch = !search || text.includes(search);
        const matchesStatus = status === 'all' || 
            (status === 'success' && row.querySelector('.status-success')) ||
            (status === 'error' && row.querySelector('.status-error'));
        
        row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
    });
}

// Open all documents
function openAllDocuments() {
    if (gradingResults.length === 0) return;
    
    const successResults = gradingResults.filter(r => r.success);
    successResults.forEach(result => {
        const doc = documents.find(d => d.id === result.doc_id);
        if (doc) {
            window.open(doc.url, '_blank');
        }
    });
}

// Export results
function exportResults() {
    if (gradingResults.length === 0) return;
    
    const csv = [
        ['Document', 'Score', 'Comments', 'Status', 'Summary'].join(','),
        ...gradingResults.map(r => {
            const doc = documents.find(d => d.id === r.doc_id);
            const docName = doc ? doc.name.replace(/,/g, ';') : r.doc_id;
            const summary = (r.summary || '').replace(/,/g, ';').replace(/\n/g, ' ');
            return [
                `"${docName}"`,
                r.total_score || '',
                r.comments_count || 0,
                r.success ? 'Success' : 'Error',
                `"${summary}"`
            ].join(',');
        })
    ].join('\n');
    
    const blob = new Blob([csv], {type: 'text/csv'});
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `grading_results_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Handle rubric upload
async function handleRubricUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const filename = file.name.toLowerCase();
    const isValidFile = filename.endsWith('.json') || filename.endsWith('.doc') || filename.endsWith('.docx');
    
    if (!isValidFile) {
        alert('Please upload a JSON file (.json) or Word document (.doc, .docx)');
        e.target.value = '';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const statusEl = document.getElementById('upload-status');
    statusEl.style.display = 'block';
    statusEl.className = 'upload-status info';
    statusEl.textContent = 'Uploading and processing...';
    
    try {
        const response = await fetch('/api/grading/rubrics/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            statusEl.className = 'upload-status error';
            statusEl.textContent = 'Error: ' + data.error;
            e.target.value = '';
            return;
        }
        
        // Success
        statusEl.className = 'upload-status success';
        statusEl.textContent = data.message || 'Rubric uploaded successfully!';
        
        // Reload rubrics list
        await loadRubrics();
        
        // Select the newly uploaded rubric
        const select = document.getElementById('rubric-select');
        const option = Array.from(select.options).find(opt => opt.value === data.filename);
        if (option) {
            select.value = data.filename;
            updateRubricControls();
        }
        
        // Clear file input
        e.target.value = '';
        
        // Hide status after 5 seconds
        setTimeout(() => {
            statusEl.style.display = 'none';
            statusEl.textContent = '';
        }, 5000);
        
    } catch (error) {
        statusEl.className = 'upload-status error';
        statusEl.textContent = 'Error uploading rubric: ' + error.message;
        e.target.value = '';
    }
}

// Delete rubric
async function deleteRubric() {
    const select = document.getElementById('rubric-select');
    const rubricFilename = select.value;
    
    if (!rubricFilename) {
        alert('Please select a rubric to delete');
        return;
    }
    
    // Get rubric name for confirmation
    const selectedOption = select.options[select.selectedIndex];
    const rubricName = selectedOption.textContent.split(' (')[0]; // Extract name before points
    
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the rubric "${rubricName}"?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    const statusEl = document.getElementById('upload-status');
    statusEl.style.display = 'block';
    statusEl.className = 'upload-status info';
    statusEl.textContent = 'Deleting rubric...';
    
    try {
        const response = await fetch(`/api/grading/rubrics/${encodeURIComponent(rubricFilename)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.error) {
            statusEl.className = 'upload-status error';
            statusEl.textContent = 'Error: ' + data.error;
            return;
        }
        
        // Success
        statusEl.className = 'upload-status success';
        statusEl.textContent = data.message || 'Rubric deleted successfully!';
        
        // Reload rubrics list
        await loadRubrics();
        
        // Clear selection
        select.value = '';
        updateRubricControls();
        
        // Hide status after 3 seconds
        setTimeout(() => {
            statusEl.style.display = 'none';
            statusEl.textContent = '';
        }, 3000);
        
    } catch (error) {
        statusEl.className = 'upload-status error';
        statusEl.textContent = 'Error deleting rubric: ' + error.message;
    }
}

