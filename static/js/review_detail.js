// Review detail page JavaScript - Shows single document
let sessionData = null;
let currentDocIndex = 0;
let currentResult = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get session ID from URL path (e.g., /review/123)
    const pathParts = window.location.pathname.split('/');
    const sessionId = pathParts[pathParts.length - 1];
    
    // Get doc_index from URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const docIndexParam = urlParams.get('doc_index');
    currentDocIndex = docIndexParam ? parseInt(docIndexParam) : 0;
    
    if (!sessionId || isNaN(sessionId)) {
        alert('Invalid session ID');
        window.location.href = '/review';
        return;
    }
    
    loadSession(sessionId);
});

async function loadSession(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        if (!response.ok) {
            throw new Error('Failed to load session');
        }
        
        sessionData = await response.json();
        
        // Validate doc_index
        if (!sessionData.results || currentDocIndex >= sessionData.results.length) {
            alert('Invalid document index');
            window.location.href = '/review';
            return;
        }
        
        currentResult = sessionData.results[currentDocIndex];
        displayDocument();
    } catch (error) {
        console.error('Error loading session:', error);
        alert('Failed to load session: ' + error.message);
    }
}

function displayDocument() {
    if (!sessionData || !currentResult) return;
    
    // Update header
    const docId = currentResult.converted_doc_id || currentResult.doc_id;
    document.getElementById('assignment-name').textContent = sessionData.assignment_name || 'Review Document';
    document.getElementById('breadcrumb-session-id').textContent = `Document ${currentDocIndex + 1}`;
    
    const date = new Date(sessionData.created_at);
    const status = sessionData.status.replace('_', ' ').toUpperCase();
    document.getElementById('session-info').textContent = 
        `Session #${sessionData.id} • Document ${currentDocIndex + 1} of ${sessionData.doc_ids.length} • ${date.toLocaleString()} • Status: ${status}`;
    
    // Show/hide buttons based on status
    if (sessionData.status === 'pending_review') {
        document.getElementById('approve-btn').style.display = 'inline-block';
        document.getElementById('reject-btn').style.display = 'inline-block';
    } else {
        document.getElementById('approve-btn').style.display = 'none';
        document.getElementById('reject-btn').style.display = 'none';
    }
    
    // Remove tabs container - we're showing single document
    const tabsContainer = document.getElementById('document-tabs');
    if (tabsContainer) {
        tabsContainer.style.display = 'none';
    }
    
    // Display single document
    displaySingleDocument();
}

function displaySingleDocument() {
    const contentContainer = document.getElementById('document-content');
    
    if (!currentResult.success) {
        contentContainer.innerHTML = `
            <div class="document-content active">
                <div class="card" style="background: #ffebee; border-color: #c62828;">
                    <h3 style="color: #c62828;">Error Grading Document</h3>
                    <p>${currentResult.error || 'Unknown error'}</p>
                </div>
            </div>
        `;
        return;
    }
    
    const docId = currentResult.converted_doc_id || currentResult.doc_id;
    const documentText = currentResult.document_text || 'Document text not available';
    
    // Get rubric criteria for score editing
    const criteria = sessionData.rubric?.criteria || [];
    const scores = currentResult.scores || {};
    const criterionComments = currentResult.criterion_comments || {};
    
    contentContainer.innerHTML = `
        <div class="document-content active">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                <!-- Left: Essay -->
                <div>
                    <h3 style="margin-bottom: 16px;">Student Essay</h3>
                    <div class="essay-container">${escapeHtml(documentText)}</div>
                </div>
                
                <!-- Right: Feedback -->
                <div>
                    <h3 style="margin-bottom: 16px;">Feedback & Scores</h3>
                    
                    <!-- Strengths -->
                    <div class="feedback-section">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: var(--text-dark);">
                            Strengths
                        </label>
                        <textarea id="strengths-0" class="feedback-textarea">${escapeHtml(currentResult.strengths || '')}</textarea>
                    </div>
                    
                    <!-- Key Issues -->
                    <div class="feedback-section">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: var(--text-dark);">
                            Key Issues
                        </label>
                        <textarea id="key-issues-0" class="feedback-textarea">${escapeHtml(currentResult.key_issues || '')}</textarea>
                    </div>
                    
                    <!-- Suggestions -->
                    <div class="feedback-section">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: var(--text-dark);">
                            Suggestions
                        </label>
                        <textarea id="suggestions-0" class="feedback-textarea">${escapeHtml(currentResult.suggestions || '')}</textarea>
                    </div>
                    
                    <!-- Scores -->
                    <div class="feedback-section">
                        <label style="display: block; margin-bottom: 16px; font-weight: 600; color: var(--text-dark);">
                            Scores
                        </label>
                        <div class="card" style="padding: 0;">
                            ${criteria.map(criterion => {
                                const criterionName = criterion.name;
                                const maxPoints = criterion.max_points;
                                const currentScore = scores[criterionName] || 0;
                                const comment = criterionComments[criterionName] || '';
                                return `
                                    <div class="criterion-row">
                                        <div>
                                            <strong>${escapeHtml(criterionName)}</strong>
                                            <div style="font-size: 12px; color: var(--text-medium); margin-top: 4px;">
                                                Max: ${maxPoints} points
                                            </div>
                                        </div>
                                        <div>
                                            <input type="number" 
                                                   id="score-0-${criterionName.replace(/\s+/g, '-')}" 
                                                   class="score-input" 
                                                   value="${currentScore}" 
                                                   min="0" 
                                                   max="${maxPoints}"
                                                   step="0.5">
                                        </div>
                                        <div style="font-size: 12px; color: var(--text-medium);">
                                            ${escapeHtml(comment)}
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                            <div style="padding: 12px; background: var(--bg-gray); border-top: 2px solid var(--border-color);">
                                <strong>Total Score: <span id="total-score-0">${currentResult.total_score || 0}</span></strong>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add event listeners for score updates
    if (criteria.length > 0) {
        criteria.forEach(criterion => {
            const inputId = `score-0-${criterion.name.replace(/\s+/g, '-')}`;
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('input', () => updateTotalScore(0));
            }
        });
    }
}

function updateTotalScore(index) {
    const criteria = sessionData.rubric?.criteria || [];
    let total = 0;
    
    criteria.forEach(criterion => {
        const inputId = `score-${index}-${criterion.name.replace(/\s+/g, '-')}`;
        const input = document.getElementById(inputId);
        if (input) {
            const score = parseFloat(input.value) || 0;
            total += score;
        }
    });
    
    const totalElement = document.getElementById(`total-score-${index}`);
    if (totalElement) {
        totalElement.textContent = total.toFixed(1);
    }
}

async function approveSession() {
    if (!confirm('Approve this document and sync feedback to Google Docs? This action cannot be undone.')) {
        return;
    }
    
    // Collect edited feedback for this single document
    const strengths = document.getElementById('strengths-0')?.value || currentResult.strengths;
    const keyIssues = document.getElementById('key-issues-0')?.value || currentResult.key_issues;
    const suggestions = document.getElementById('suggestions-0')?.value || currentResult.suggestions;
    
    // Get edited scores
    const criteria = sessionData.rubric?.criteria || [];
    const scores = {};
    let totalScore = 0;
    
    criteria.forEach(criterion => {
        const inputId = `score-0-${criterion.name.replace(/\s+/g, '-')}`;
        const input = document.getElementById(inputId);
        if (input) {
            const score = parseFloat(input.value) || 0;
            scores[criterion.name] = score;
            totalScore += score;
        }
    });
    
    // Update only this document's result in the results array
    const editedResults = [...sessionData.results];
    editedResults[currentDocIndex] = {
        ...currentResult,
        strengths,
        key_issues: keyIssues,
        suggestions,
        scores,
        total_score: totalScore
    };
    
    try {
        // Approve this single document
        const response = await fetch(`/api/sessions/${sessionData.id}/approve-document`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                doc_index: currentDocIndex,
                result: editedResults[currentDocIndex],
                user_email: 'admin@busn403.edu', // TODO: Get from auth
                review_notes: ''
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Error approving document: ' + data.error);
            return;
        }
        
        alert('Document approved! Feedback has been synced to Google Docs.');
        window.location.href = '/review';
    } catch (error) {
        alert('Error approving document: ' + error.message);
    }
}

async function rejectSession() {
    const notes = prompt('Enter rejection notes (optional):');
    if (notes === null) return; // User cancelled
    
    try {
        const response = await fetch(`/api/sessions/${sessionData.id}/reject-document`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                doc_index: currentDocIndex,
                user_email: 'admin@busn403.edu', // TODO: Get from auth
                review_notes: notes || ''
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Error rejecting document: ' + data.error);
            return;
        }
        
        alert('Document rejected.');
        window.location.href = '/review';
    } catch (error) {
        alert('Error rejecting document: ' + error.message);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions available globally
window.approveSession = approveSession;
window.rejectSession = rejectSession;
