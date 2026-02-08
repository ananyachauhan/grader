// Assignment Detail Page JavaScript
let currentAssignmentId = null;
let currentSectionId = null;
let currentSectionNumber = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get assignment ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    currentAssignmentId = urlParams.get('assignment_id') || window.location.pathname.split('/').pop();
    currentSectionId = urlParams.get('section_id');
    currentSectionNumber = urlParams.get('section_number') || '900';
    
    if (currentAssignmentId) {
        loadAssignmentDetail();
    } else {
        document.getElementById('assignment-detail-content').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <p style="color: #c62828;">Error: Assignment ID not found</p>
                <a href="/assignments" class="btn btn-primary" style="margin-top: 20px;">Back to Assignments</a>
            </div>
        `;
    }
});

async function loadAssignmentDetail() {
    try {
        // Load assignment data, summary, and history in parallel
        const [assignmentRes, summaryRes, historyRes] = await Promise.all([
            fetch(`/api/assignments/${currentAssignmentId}`),
            fetch(`/api/assignments/${currentAssignmentId}/summary`),
            fetch(`/api/assignments/${currentAssignmentId}/history`)
        ]);
        
        const assignmentData = await assignmentRes.json();
        const summaryData = await summaryRes.json();
        const historyData = await historyRes.json();
        
        // Load rubric if assignment has one
        let rubricData = null;
        if (assignmentData.assignment && assignmentData.assignment.rubric_filename) {
            try {
                const rubricRes = await fetch(`/api/grading/rubrics/${assignmentData.assignment.rubric_filename}`);
                if (rubricRes.ok) {
                    const rubricResult = await rubricRes.json();
                    rubricData = rubricResult.rubric;
                }
            } catch (error) {
                console.error('Error loading rubric:', error);
            }
        }
        
        if (assignmentData.error) {
            document.getElementById('assignment-detail-content').innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <p style="color: #c62828;">Error: ${assignmentData.error}</p>
                    <a href="/assignments" class="btn btn-primary" style="margin-top: 20px;">Back to Assignments</a>
                </div>
            `;
            return;
        }
        
        const assignment = assignmentData.assignment;
        const summary = summaryData.summary || {};
        const history = historyData.history || [];
        
        // Update breadcrumb
        document.getElementById('breadcrumb-assignment-name').textContent = assignment.name;
        
        // Build detail content
        let detailHTML = `
            <div class="page-header">
                <h1>${assignment.name}</h1>
                <p>BUSN 403 - Business Writing and Communication</p>
            </div>
            
            <!-- Actions Section -->
            <div class="card">
                <div class="card-header">
                    <h2>Actions</h2>
                </div>
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button class="btn btn-primary" id="grade-btn" ${assignment.status === 'completed' ? 'disabled' : ''}>
                        Grade Assignment
                    </button>
                    <button class="btn btn-secondary" id="edit-btn">
                        Edit Assignment
                    </button>
                    <button class="btn btn-secondary" id="history-btn">
                        View History
                    </button>
                    <button class="btn btn-danger" id="delete-btn">
                        Delete Assignment
                    </button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>Assignment Information</h2>
                </div>
                ${assignment.description ? `<p style="color: var(--text-medium); margin-bottom: 20px;">${assignment.description}</p>` : ''}
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                    <div>
                        <strong>Status:</strong> <span class="assignment-status ${assignment.status}">${assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1)}</span>
                    </div>
                    <div>
                        <strong>Created:</strong> ${new Date(assignment.created_at).toLocaleDateString()}
                    </div>
                    <div>
                        <strong>Folder ID:</strong> <code style="font-size: 12px; background: var(--bg-gray); padding: 2px 6px; border-radius: 3px;">${assignment.drive_folder_id}</code>
                    </div>
                </div>
            </div>
            
            ${rubricData ? `
            <div class="card">
                <div class="card-header">
                    <h2>Grading Rubric</h2>
                </div>
                <div style="margin-bottom: 16px;">
                    <h3 style="color: var(--aggie-maroon); font-size: 18px; margin-bottom: 8px;">${rubricData.name}</h3>
                    <p style="color: var(--text-medium); font-size: 14px;">Total Points: <strong>${rubricData.total_points}</strong></p>
                </div>
                <div style="border-top: 1px solid var(--border-color); padding-top: 16px;">
                    ${rubricData.criteria && rubricData.criteria.length > 0 ? `
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: var(--bg-gray); border-bottom: 2px solid var(--aggie-maroon);">
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Criterion</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; color: var(--text-dark); width: 120px;">Max Points</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: var(--text-dark);">Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rubricData.criteria.map((criterion, index) => `
                            <tr style="border-bottom: 1px solid var(--border-color); ${index % 2 === 0 ? 'background: #fafafa;' : ''}">
                                <td style="padding: 12px; font-weight: 500; color: var(--text-dark);">${criterion.name}</td>
                                <td style="padding: 12px; text-align: center; color: var(--aggie-maroon); font-weight: 600;">${criterion.max_points}</td>
                                <td style="padding: 12px; color: var(--text-medium); font-size: 14px;">${criterion.description || 'No description provided'}</td>
                            </tr>
                            `).join('')}
                        </tbody>
                    </table>
                    ` : '<p style="color: var(--text-medium);">No criteria defined.</p>'}
                </div>
            </div>
            ` : ''}
            
            ${assignment.custom_instructions ? `
            <div class="card">
                <div class="card-header">
                    <h2>Custom Grading Instructions</h2>
                </div>
                <p style="color: var(--text-medium); white-space: pre-wrap;">${assignment.custom_instructions}</p>
            </div>
            ` : ''}
        `;
        
        // Add grading summary
        if (summary.graded_documents > 0) {
            detailHTML += `
                <div class="card">
                    <div class="card-header">
                        <h2>Grading Summary</h2>
                    </div>
                    ${summary.performance_summary ? `
                    <div style="margin-bottom: 24px; padding: 16px; background: var(--bg-gray); border-radius: 4px; border-left: 4px solid var(--aggie-maroon);">
                        <p style="color: var(--text-dark); line-height: 1.6; margin: 0;">${summary.performance_summary}</p>
                    </div>
                    ` : ''}
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 20px;">
                        <div>
                            <div style="font-size: 32px; font-weight: 600; color: var(--aggie-maroon);">${summary.graded_documents}</div>
                            <div style="color: var(--text-medium); font-size: 14px; margin-top: 4px;">Graded Documents</div>
                        </div>
                        <div>
                            <div style="font-size: 32px; font-weight: 600; color: var(--aggie-maroon);">${summary.ungraded_documents || 0}</div>
                            <div style="color: var(--text-medium); font-size: 14px; margin-top: 4px;">Ungraded Documents</div>
                        </div>
                        ${summary.average_score !== null ? `
                        <div>
                            <div style="font-size: 32px; font-weight: 600; color: var(--aggie-maroon);">${summary.average_score.toFixed(1)}</div>
                            <div style="color: var(--text-medium); font-size: 14px; margin-top: 4px;">Average Score (out of ${summary.total_points})</div>
                        </div>
                        <div>
                            <div style="font-size: 32px; font-weight: 600; color: var(--aggie-maroon);">${summary.min_score} - ${summary.max_score}</div>
                            <div style="color: var(--text-medium); font-size: 14px; margin-top: 4px;">Score Range</div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        } else {
            detailHTML += `
                <div class="card">
                    <div class="card-header">
                        <h2>Grading Summary</h2>
                    </div>
                    <p style="color: var(--text-medium);">No documents have been graded yet.</p>
                </div>
            `;
        }
        
        // Set content
        document.getElementById('assignment-detail-content').innerHTML = detailHTML;
        
        // Add event listeners for buttons
        document.getElementById('grade-btn').addEventListener('click', () => {
            const url = `/grade?assignment_id=${currentAssignmentId}&section_id=${currentSectionId}&section_number=${currentSectionNumber}`;
            window.location.href = url;
        });
        
        document.getElementById('edit-btn').addEventListener('click', () => {
            const url = `/assignments?section_id=${currentSectionId}&section_number=${currentSectionNumber}&edit=${currentAssignmentId}`;
            window.location.href = url;
        });
        
        document.getElementById('history-btn').addEventListener('click', () => {
            viewHistory(history);
        });
        
        document.getElementById('delete-btn').addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this assignment? This action cannot be undone.')) {
                deleteAssignment();
            }
        });
        
    } catch (error) {
        document.getElementById('assignment-detail-content').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <p style="color: #c62828;">Error loading assignment details: ${error.message}</p>
                <a href="/assignments" class="btn btn-primary" style="margin-top: 20px;">Back to Assignments</a>
            </div>
        `;
    }
}

function viewHistory(history) {
    if (history.length === 0) {
        alert('No grading history yet.');
        return;
    }
    
    const historyText = history.map(h => 
        `Graded ${h.doc_ids.length} documents on ${new Date(h.created_at).toLocaleString()}\nStatus: ${h.status}`
    ).join('\n\n');
    
    alert('Grading History:\n\n' + historyText);
}

async function deleteAssignment() {
    try {
        const response = await fetch(`/api/assignments/${currentAssignmentId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        // Redirect back to assignments page
        const url = `/assignments?section_id=${currentSectionId}&section_number=${currentSectionNumber}`;
        window.location.href = url;
    } catch (error) {
        alert('Error deleting assignment: ' + error.message);
    }
}

