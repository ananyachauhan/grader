// Review dashboard JavaScript - Shows individual documents
let allDocuments = [];
let filteredDocuments = [];
let currentFilter = 'all';

// Make filterDocuments available globally
window.filterDocuments = filterDocuments;
window.reviewDocument = reviewDocument;
window.viewDocument = viewDocument;
window.gradeDocument = gradeDocument;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllDocuments();
});

async function loadAllDocuments() {
    try {
        // Get all sections
        const sectionsRes = await fetch('/api/sections');
        const sectionsData = await sectionsRes.json();
        
        if (!sectionsData.sections) {
            displayError('Failed to load sections');
            return;
        }
        
        // Get all documents from all assignments
        const allDocsData = [];
        for (const section of sectionsData.sections) {
            const assignmentsRes = await fetch(`/api/sections/${section.id}/assignments`);
            const assignmentsData = await assignmentsRes.json();
            
            if (assignmentsData.assignments) {
                for (const assignment of assignmentsData.assignments) {
                    const docsRes = await fetch(`/api/assignments/${assignment.id}/documents`);
                    if (docsRes.ok) {
                        const docsData = await docsRes.json();
                        if (docsData.documents) {
                            for (const doc of docsData.documents) {
                                allDocsData.push({
                                    ...doc,
                                    section_number: section.section_number
                                });
                            }
                        }
                    }
                }
            }
        }
        
        allDocuments = allDocsData;
        filterDocuments(currentFilter);
        
    } catch (error) {
        console.error('Error loading documents:', error);
        displayError('Failed to load documents: ' + error.message);
    }
}

function filterDocuments(status) {
    currentFilter = status;
    
    if (status === 'all') {
        filteredDocuments = allDocuments;
    } else {
        filteredDocuments = allDocuments.filter(doc => doc.status === status);
    }
    
    // Update active tab
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.status === status) {
            tab.classList.add('active');
        }
    });
    
    // Update counts
    updateCounts();
    
    // Display documents
    displayDocuments();
}

function updateCounts() {
    const all = allDocuments.length;
    const pending = allDocuments.filter(d => d.status === 'pending_review').length;
    const ungraded = allDocuments.filter(d => d.status === 'ungraded').length;
    const reviewed = allDocuments.filter(d => d.status === 'reviewed').length;
    
    document.getElementById('all-count').textContent = all;
    document.getElementById('pending-count').textContent = pending;
    document.getElementById('ungraded-count').textContent = ungraded;
    document.getElementById('reviewed-count').textContent = reviewed;
}

function displayDocuments() {
    const container = document.getElementById('sessions-container');
    
    if (filteredDocuments.length === 0) {
        container.innerHTML = `
            <div class="card">
                <div style="text-align: center; padding: 40px; color: var(--text-medium);">
                    <p>No documents found with status: ${currentFilter === 'all' ? 'all statuses' : currentFilter.replace('_', ' ')}.</p>
                </div>
            </div>
        `;
        return;
    }
    
    // Sort by assignment name, then by document name
    const sorted = [...filteredDocuments].sort((a, b) => {
        if (a.assignment_name !== b.assignment_name) {
            return a.assignment_name.localeCompare(b.assignment_name);
        }
        return a.doc_name.localeCompare(b.doc_name);
    });
    
    container.innerHTML = sorted.map(doc => {
        const statusClass = doc.status === 'reviewed' ? 'success' : 
                           doc.status === 'pending_review' ? 'warning' : 
                           doc.status === 'ungraded' ? 'info' : 'secondary';
        
        // Determine action button based on status
        let actionButton = '';
        if (doc.status === 'pending_review' && doc.session_id) {
            // Review button - link to review detail page with doc_index
            actionButton = `
                <button class="btn btn-primary" onclick="reviewDocument(${doc.session_id}, ${doc.doc_index || 0})">
                    Review
                </button>
            `;
        } else if (doc.status === 'ungraded') {
            // Grade button - link to grading page
            actionButton = `
                <button class="btn btn-secondary" onclick="gradeDocument(${doc.assignment_id}, '${doc.doc_id}')">
                    Grade
                </button>
            `;
        } else if (doc.status === 'reviewed') {
            // View button - link to review detail page (read-only)
            actionButton = `
                <button class="btn btn-secondary" onclick="viewDocument(${doc.session_id}, ${doc.doc_index || 0})">
                    View
                </button>
            `;
        }
        
        const gradedDate = doc.graded_at ? new Date(doc.graded_at).toLocaleString() : 'N/A';
        const reviewedDate = doc.reviewed_at ? new Date(doc.reviewed_at).toLocaleString() : 'N/A';
        
        return `
            <div class="card" style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 8px 0; color: var(--text-dark);">${escapeHtml(doc.doc_name)}</h3>
                        <p style="margin: 0 0 8px 0; color: var(--text-medium); font-size: 14px;">
                            ${escapeHtml(doc.assignment_name)} • Section ${doc.section_number || 'N/A'}
                        </p>
                        <div style="display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: var(--text-medium);">
                            ${doc.graded_at ? `<span>Graded: ${gradedDate}</span>` : ''}
                            ${doc.reviewed_at ? `<span>Reviewed: ${reviewedDate}</span>` : ''}
                        </div>
                        <span class="badge badge-${statusClass}" style="display: inline-block; margin-top: 8px;">
                            ${doc.status.replace('_', ' ').toUpperCase()}
                        </span>
                    </div>
                    <div>
                        ${actionButton}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function reviewDocument(sessionId, docIndex) {
    window.location.href = `/review/${sessionId}?doc_index=${docIndex}`;
}

function viewDocument(sessionId, docIndex) {
    window.location.href = `/review/${sessionId}?doc_index=${docIndex}`;
}

function gradeDocument(assignmentId, docId) {
    // Get section info from URL or use default
    const urlParams = new URLSearchParams(window.location.search);
    const sectionId = urlParams.get('section_id');
    const sectionNumber = urlParams.get('section_number') || '900';
    
    if (sectionId) {
        window.location.href = `/grade?assignment_id=${assignmentId}&section_id=${sectionId}&section_number=${sectionNumber}&doc_id=${docId}`;
    } else {
        window.location.href = `/grade?assignment_id=${assignmentId}&doc_id=${docId}`;
    }
}

function displayError(message) {
    const container = document.getElementById('sessions-container');
    container.innerHTML = `
        <div class="card">
            <div style="text-align: center; padding: 40px; color: #c62828;">
                <p>${message}</p>
            </div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
