// Grading page JavaScript
let assignment = null;
let documents = [];
let selectedDocs = new Set();
let gradingResults = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const assignmentId = new URLSearchParams(window.location.search).get('assignment_id');
    const sectionId = new URLSearchParams(window.location.search).get('section_id');
    const sectionNumber = new URLSearchParams(window.location.search).get('section_number');
    
    checkAuthStatus();
    loadAssignment(assignmentId);
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('load-docs-btn').addEventListener('click', loadDocuments);
    document.getElementById('grade-btn').addEventListener('click', gradeDocuments);
    document.getElementById('select-all').addEventListener('change', toggleSelectAll);
    document.getElementById('open-all-btn').addEventListener('click', openAllDocuments);
    document.getElementById('save-results-btn').addEventListener('click', saveResults);
}

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/documents/auth/status');
        const data = await response.json();
        
        const authStatusDiv = document.getElementById('auth-status');
        const loadDocsBtn = document.getElementById('load-docs-btn');
        
        if (data.authenticated) {
            authStatusDiv.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; color: #2d7a32;">
                    <span style="font-size: 20px;">✓</span>
                    <span>Authenticated with Google account</span>
                </div>
            `;
            // Enable button if assignment is loaded and has folder ID
            if (assignment && assignment.drive_folder_id) {
                loadDocsBtn.disabled = false;
            }
        } else {
            authStatusDiv.innerHTML = `
                <div style="margin-bottom: 15px;">
                    <p style="color: #d32f2f; margin-bottom: 10px;">⚠ Not authenticated</p>
                    <p style="color: #666; font-size: 14px;">You need to authenticate with your Google account to access Drive files.</p>
                </div>
                <button id="auth-btn" class="btn btn-primary">Authenticate with Google</button>
            `;
            loadDocsBtn.disabled = true;
            
            // Add event listener for auth button
            const authBtn = document.getElementById('auth-btn');
            if (authBtn) {
                authBtn.addEventListener('click', initiateAuth);
            }
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        const authStatusDiv = document.getElementById('auth-status');
        authStatusDiv.innerHTML = `
            <p style="color: #d32f2f;">Error checking authentication status. Please try again.</p>
        `;
    }
}

async function initiateAuth() {
    try {
        const response = await fetch('/api/documents/auth');
        const data = await response.json();
        
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        if (data.auth_url) {
            // Open auth URL in a new window
            const authWindow = window.open(data.auth_url, 'Google Authentication', 'width=500,height=600');
            
            // Check if window was closed (user completed auth)
            const checkClosed = setInterval(() => {
                if (authWindow.closed) {
                    clearInterval(checkClosed);
                    // Recheck auth status
                    setTimeout(checkAuthStatus, 1000);
                }
            }, 500);
        }
    } catch (error) {
        alert('Error initiating authentication: ' + error.message);
    }
}

async function loadAssignment(assignmentId) {
    try {
        const response = await fetch(`/api/assignments/${assignmentId}`);
        const data = await response.json();
        
        if (data.error) {
            alert('Error loading assignment: ' + data.error);
            return;
        }
        
        assignment = data.assignment;
        console.log('Assignment loaded:', assignment);
        
        // Update UI
            document.getElementById('assignment-name-header').textContent = assignment.name;
            document.getElementById('breadcrumb-assignment-name').textContent = assignment.name;
            if (assignment.description) {
                document.getElementById('assignment-description').textContent = assignment.description;
            }
        document.getElementById('assignment-info').innerHTML = `
            <p><strong>Rubric:</strong> ${assignment.rubric_filename}</p>
            ${assignment.custom_instructions ? `<p><strong>Custom Instructions:</strong> ${assignment.custom_instructions}</p>` : ''}
            <p><strong>Drive Folder ID:</strong> ${assignment.drive_folder_id}</p>
            <p><strong>Status:</strong> <span style="color: ${assignment.status === 'active' ? '#2d7a32' : '#666'}">${assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1)}</span></p>
        `;
        
        // Enable load docs button if authenticated and folder ID exists
        const loadDocsBtn = document.getElementById('load-docs-btn');
        if (assignment.drive_folder_id) {
            // Check if authenticated, then enable
            try {
                const authResponse = await fetch('/api/documents/auth/status');
                const authData = await authResponse.json();
                if (authData.authenticated) {
                    loadDocsBtn.disabled = false;
                    console.log('Load docs button enabled');
                } else {
                    loadDocsBtn.disabled = true;
                    console.log('Load docs button disabled - not authenticated');
                }
            } catch (authError) {
                console.error('Error checking auth for button:', authError);
                loadDocsBtn.disabled = true;
            }
        } else {
            loadDocsBtn.disabled = true;
        }
    } catch (error) {
        console.error('Error loading assignment:', error);
        alert('Error loading assignment: ' + error.message);
    }
}

async function loadDocuments() {
    console.log('loadDocuments called', { assignment, folderId: assignment?.drive_folder_id });
    
    if (!assignment || !assignment.drive_folder_id) {
        alert('No drive folder configured for this assignment');
        return;
    }
    
    try {
        showProgress('Loading documents...', 0);
        const url = `/api/documents/list?folder_id=${assignment.drive_folder_id}`;
        console.log('Fetching documents from:', url);
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.error) {
            // Check if authentication is required
            if (data.auth_required && data.auth_url) {
                const shouldAuth = confirm('Authentication required to access Drive files. Would you like to authenticate now?');
                if (shouldAuth) {
                    window.open(data.auth_url, 'Google Authentication', 'width=500,height=600');
                }
            } else {
                alert('Error: ' + data.error);
            }
            hideProgress();
            return;
        }
        
        documents = data.documents || [];
        console.log('Documents loaded:', documents.length);
        displayDocuments();
        document.getElementById('documents-container').classList.remove('hidden');
        hideProgress();
    } catch (error) {
        console.error('Error loading documents:', error);
        alert('Error loading documents: ' + error.message);
        hideProgress();
    }
}

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
        const fileTypeBadge = doc.is_word_doc 
            ? '<span style="background: #ff9800; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-left: 8px;">Word</span>'
            : '<span style="background: #2d7a32; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-left: 8px;">Google Doc</span>';
        
        item.innerHTML = `
            <input type="checkbox" value="${doc.id}" data-name="${doc.name}" data-is-word="${doc.is_word_doc || false}">
            <span class="document-item-name">${doc.name}</span>
            ${fileTypeBadge}
            <a href="${doc.url}" target="_blank" class="btn btn-secondary" style="padding: 5px 10px; text-decoration: none; font-size: 12px;">Open</a>
        `;
        
        const checkbox = item.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', updateSelection);
        
        container.appendChild(item);
    });
}

function updateSelection(e) {
    const docId = e.target.value;
    if (e.target.checked) {
        selectedDocs.add(docId);
    } else {
        selectedDocs.delete(docId);
    }
    updateSelectedCount();
    updateGradeButton();
}

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
    updateGradeButton();
}

function updateSelectedCount() {
    document.getElementById('selected-count').textContent = `${selectedDocs.size} selected`;
}

function updateGradeButton() {
    const btn = document.getElementById('grade-btn');
    btn.disabled = selectedDocs.size === 0 || !assignment;
}

async function gradeDocuments() {
    if (!assignment || selectedDocs.size === 0) {
        alert('Please select at least one document');
        return;
    }
    
    if (!confirm(`Grade ${selectedDocs.size} document(s)? This will insert comments and scores into the documents.`)) {
        return;
    }
    
    const docIds = Array.from(selectedDocs);
    const progressContainer = document.getElementById('progress-container');
    progressContainer.classList.remove('hidden');
    document.getElementById('grade-btn').disabled = true;
    
    try {
        showProgress(`Grading ${docIds.length} documents...`, 10);
        
        // Build doc_types map to indicate which docs are Word documents
        const docTypes = {};
        docIds.forEach(docId => {
            const doc = documents.find(d => d.id === docId);
            docTypes[docId] = doc && doc.is_word_doc ? true : false;
        });
        
        const requestBody = {
            doc_ids: docIds,
            doc_types: docTypes,
            rubric_filename: assignment.rubric_filename
        };
        
        if (assignment.custom_instructions && assignment.custom_instructions.trim()) {
            requestBody.custom_instructions = assignment.custom_instructions.trim();
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
        
        document.getElementById('results-section').classList.remove('hidden');
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

function showProgress(text, percent) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

function hideProgress() {
    document.getElementById('progress-container').classList.add('hidden');
}

function displayResults() {
    const successResults = gradingResults.filter(r => r.success);
    const successCount = successResults.length;
    const avgScore = successCount > 0
        ? successResults.reduce((sum, r) => sum + (r.total_score || 0), 0) / successCount
        : 0;
    
    document.getElementById('total-graded').textContent = gradingResults.length;
    document.getElementById('avg-score').textContent = Math.round(avgScore);
    document.getElementById('success-count').textContent = successCount;
    
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
                        <th>Error Details</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${gradingResults.map(result => {
                        // Use converted_doc_id if available (for Word docs), otherwise use doc_id
                        const displayDocId = result.converted_doc_id || result.doc_id;
                        const originalDocId = result.original_doc_id || result.doc_id;
                        const doc = documents.find(d => d.id === originalDocId);
                        const docName = doc ? doc.name : originalDocId;
                        const docUrl = result.success ? `https://docs.google.com/document/d/${displayDocId}` : '#';
                        const wordDocNote = result.converted_doc_id ? ' <span style="color: #ff9800; font-size: 11px;">(Word doc - converted)</span>' : '';
                        const errorMsg = result.error ? `<div style="color: #d32f2f; font-size: 12px; max-width: 400px; word-wrap: break-word;">${result.error}</div>` : '<span style="color: #666;">-</span>';
                        
                        return `
                            <tr>
                                <td>${docName}${wordDocNote}</td>
                                <td>${result.total_score || 'N/A'}</td>
                                <td>${result.comments_count || 0}</td>
                                <td class="${result.success ? 'status-success' : 'status-error'}">
                                    ${result.success ? '✓ Success' : '✗ Error'}
                                </td>
                                <td>${errorMsg}</td>
                                <td>
                                    ${result.success ? `<a href="${docUrl}" target="_blank" class="btn btn-secondary" style="padding: 5px 10px; text-decoration: none; font-size: 12px;">Open Graded Doc</a>` : '<span style="color: var(--text-medium);">N/A</span>'}
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

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

async function saveResults() {
    if (gradingResults.length === 0) {
        alert('No results to save');
        return;
    }
    
    const assignmentId = new URLSearchParams(window.location.search).get('assignment_id');
    const docIds = Array.from(selectedDocs);
    
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                assignment_id: parseInt(assignmentId),
                doc_ids: docIds,
                results: gradingResults,
                user_email: 'admin@busn403.edu' // TODO: Get from auth
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Error saving results: ' + data.error);
            return;
        }
        
        alert('Results saved successfully! Status: Pending Review');
        
        // Optionally redirect back to assignments
        // window.location.href = `/assignments?section_id=${sectionId}&section_number=${sectionNumber}`;
        
    } catch (error) {
        alert('Error saving results: ' + error.message);
    }
}

