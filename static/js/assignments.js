// Assignments page JavaScript
// Use different variable names to avoid conflict with sidebar.js
let assignmentsSectionId = null;
let assignmentsSectionNumber = null;
let rubrics = [];

// Fallback: Try to load if DOM is already ready
if (document.readyState === 'loading') {
    // DOMContentLoaded hasn't fired yet, wait for it
} else {
    // DOM is already ready, run immediately
    setTimeout(() => {
        if (document.getElementById('assignments-list')) {
            assignmentsSectionId = new URLSearchParams(window.location.search).get('section_id');
            assignmentsSectionNumber = new URLSearchParams(window.location.search).get('section_number') || '900';
            console.log('Running fallback initialization');
            loadAssignments();
        }
    }, 100);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    try {
        assignmentsSectionId = new URLSearchParams(window.location.search).get('section_id');
        assignmentsSectionNumber = new URLSearchParams(window.location.search).get('section_number') || '900';
        
        console.log('Assignments page initialized:', { assignmentsSectionId, assignmentsSectionNumber });
        
        const sectionNumberEl = document.getElementById('section-number');
        const sectionHeaderEl = document.getElementById('section-header-number');
        
        if (sectionNumberEl) sectionNumberEl.textContent = assignmentsSectionNumber;
        if (sectionHeaderEl) sectionHeaderEl.textContent = assignmentsSectionNumber;
        
        loadAssignments();
        loadRubrics();
        setupEventListeners();
    } catch (error) {
        console.error('Error initializing assignments page:', error);
        const container = document.getElementById('assignments-list');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: var(--text-medium); grid-column: 1 / -1;">
                    <div style="font-size: 64px; margin-bottom: 20px;">❌</div>
                    <p style="font-size: 20px; margin-bottom: 8px; color: #c62828;">Initialization Error</p>
                    <p style="font-size: 16px; margin-bottom: 20px;">${error.message}</p>
                    <button onclick="window.location.reload()" class="btn btn-secondary" style="margin-top: 10px;">Reload Page</button>
                </div>
            `;
        }
    }
});

function setupEventListeners() {
    const createBtn = document.getElementById('create-assignment-btn');
    if (createBtn) {
        createBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            openAssignmentModal();
        });
    } else {
        console.error('Create assignment button not found');
    }
    
    const closeBtn = document.getElementById('close-modal');
    const cancelBtn = document.getElementById('cancel-form');
    const modal = document.getElementById('assignment-modal');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            closeAssignmentModal();
        });
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            closeAssignmentModal();
        });
    }
    
    // Close modal when clicking outside
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAssignmentModal();
            }
        });
        
        // Prevent modal content clicks from closing modal
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }
    
    const form = document.getElementById('assignment-form');
    if (form) {
        form.addEventListener('submit', handleAssignmentSubmit);
    }
    
    const deleteBtn = document.getElementById('delete-assignment-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', handleDeleteAssignment);
    }
    
    // Rubric upload handler
    const rubricUploadInput = document.getElementById('rubric-upload-inline');
    if (rubricUploadInput) {
        rubricUploadInput.addEventListener('change', handleRubricUpload);
    }
    
    // Check if we need to open edit modal from URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const editId = urlParams.get('edit');
    if (editId) {
        openAssignmentModal(parseInt(editId));
    }
}

async function loadAssignments() {
    console.log('loadAssignments() called');
    const container = document.getElementById('assignments-list');
    
    if (!container) {
        console.error('assignments-list container not found');
        return;
    }
    
    console.log('Container found, clearing loading message');
    // Immediately clear loading message
    container.innerHTML = '<p style="text-align: center; padding: 40px; color: #666;">Loading...</p>';
    
    // Check if section_id is available
    if (!assignmentsSectionId) {
        console.warn('No section_id found in URL');
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: var(--text-medium); grid-column: 1 / -1;">
                <div style="font-size: 64px; margin-bottom: 20px;">⚠️</div>
                <p style="font-size: 20px; margin-bottom: 8px; color: #c62828;">Missing Section Information</p>
                <p style="font-size: 16px; margin-bottom: 20px;">Please go back to the sections page and select a section.</p>
                <a href="/" class="btn btn-primary" style="margin-top: 10px;">Go to Sections</a>
            </div>
        `;
        return;
    }
    
    try {
        console.log('Loading assignments for section:', assignmentsSectionId);
        const response = await fetch(`/api/sections/${assignmentsSectionId}/assignments`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Assignments data received:', data);
        
        if (data.error) {
            container.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: var(--text-medium); grid-column: 1 / -1;">
                    <div style="font-size: 64px; margin-bottom: 20px;">❌</div>
                    <p style="font-size: 20px; margin-bottom: 8px; color: #c62828;">Error Loading Assignments</p>
                    <p style="font-size: 16px; margin-bottom: 20px;">${data.error}</p>
                    <button onclick="loadAssignments()" class="btn btn-secondary" style="margin-top: 10px;">Retry</button>
                </div>
            `;
            return;
        }
        
        displayAssignments(data.assignments || []);
    } catch (error) {
        console.error('Error loading assignments:', error);
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: var(--text-medium); grid-column: 1 / -1;">
                <div style="font-size: 64px; margin-bottom: 20px;">❌</div>
                <p style="font-size: 20px; margin-bottom: 8px; color: #c62828;">Error Loading Assignments</p>
                <p style="font-size: 16px; margin-bottom: 20px;">${error.message}</p>
                <button onclick="loadAssignments()" class="btn btn-secondary" style="margin-top: 10px;">Retry</button>
            </div>
        `;
    }
}

// Make loadAssignments globally accessible for retry button
window.loadAssignments = loadAssignments;

function displayAssignments(assignments) {
    const container = document.getElementById('assignments-list');
    
    if (!assignments || assignments.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: var(--text-medium); grid-column: 1 / -1;">
                <div style="font-size: 64px; margin-bottom: 20px;">📝</div>
                <p style="font-size: 20px; margin-bottom: 8px; color: var(--text-dark);">No assignments yet</p>
                <p style="font-size: 16px; margin-bottom: 24px;">Get started by creating your first assignment for this section.</p>
                <button onclick="document.getElementById('create-assignment-btn').click()" class="btn btn-primary" style="margin-top: 10px;">
                    + Create Assignment
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = assignments.map(assignment => {
        return `
            <div class="assignment-tile" data-assignment-id="${assignment.id}">
                <h3>${assignment.name}</h3>
                ${assignment.description ? `<p style="color: var(--text-medium); margin: 8px 0; font-size: 14px;">${assignment.description}</p>` : ''}
                <div style="display: flex; gap: 12px; align-items: center; font-size: 13px; color: var(--text-medium); margin-top: 12px;">
                    <span class="assignment-status ${assignment.status}">${assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1)}</span>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click listeners to tiles
    container.querySelectorAll('.assignment-tile').forEach(tile => {
        tile.addEventListener('click', (e) => {
            const assignmentId = tile.dataset.assignmentId;
            const url = `/assignment/${assignmentId}?section_id=${assignmentsSectionId}&section_number=${assignmentsSectionNumber}`;
            window.location.href = url;
        });
    });
}

async function loadRubrics() {
    try {
        const response = await fetch('/api/grading/rubrics');
        const data = await response.json();
        rubrics = data.rubrics || [];
        
        const select = document.getElementById('assignment-rubric');
        if (select) {
            const currentValue = select.value; // Preserve current selection
            select.innerHTML = '<option value="">Select a rubric...</option>';
            rubrics.forEach(rubric => {
                const option = document.createElement('option');
                option.value = rubric.filename;
                option.textContent = `${rubric.name} (${rubric.total_points} pts)`;
                select.appendChild(option);
            });
            // Restore selection if it still exists
            if (currentValue) {
                select.value = currentValue;
            }
        }
    } catch (error) {
        console.error('Error loading rubrics:', error);
    }
}

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
    
    const statusEl = document.getElementById('rubric-upload-status');
    if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.style.color = '#666';
        statusEl.textContent = 'Uploading and processing...';
    }
    
    try {
        const response = await fetch('/api/grading/rubrics/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            if (statusEl) {
                statusEl.style.color = '#d32f2f';
                statusEl.textContent = 'Error: ' + data.error;
            } else {
                alert('Error: ' + data.error);
            }
            e.target.value = '';
            return;
        }
        
        // Success
        if (statusEl) {
            statusEl.style.color = '#2e7d32';
            statusEl.textContent = data.message || 'Rubric uploaded successfully!';
        }
        
        // Reload rubrics list
        await loadRubrics();
        
        // Select the newly uploaded rubric
        const select = document.getElementById('assignment-rubric');
        if (select && data.filename) {
            select.value = data.filename;
        }
        
        // Clear file input
        e.target.value = '';
        
        // Hide status after 5 seconds
        if (statusEl) {
            setTimeout(() => {
                statusEl.textContent = '';
                statusEl.style.display = 'none';
            }, 5000);
        }
        
    } catch (error) {
        if (statusEl) {
            statusEl.style.color = '#d32f2f';
            statusEl.textContent = 'Error uploading rubric: ' + error.message;
        } else {
            alert('Error uploading rubric: ' + error.message);
        }
        e.target.value = '';
    }
}

function openAssignmentModal(assignmentId = null) {
    try {
        const modal = document.getElementById('assignment-modal');
        if (!modal) {
            console.error('Modal element not found');
            alert('Error: Modal not found. Please refresh the page.');
            return;
        }
        
        const form = document.getElementById('assignment-form');
        const deleteBtn = document.getElementById('delete-assignment-btn');
        
        if (assignmentId) {
            document.getElementById('modal-title').textContent = 'Edit Assignment';
            document.getElementById('assignment-id').value = assignmentId;
            if (deleteBtn) deleteBtn.classList.remove('hidden');
            loadAssignmentData(assignmentId);
        } else {
            document.getElementById('modal-title').textContent = 'Create Assignment';
            document.getElementById('assignment-id').value = '';
            if (form) form.reset();
            if (deleteBtn) deleteBtn.classList.add('hidden');
        }
        
        modal.classList.remove('hidden');
        console.log('Modal opened');
    } catch (error) {
        console.error('Error opening modal:', error);
        alert('Error opening assignment form: ' + error.message);
    }
}

function closeAssignmentModal() {
    document.getElementById('assignment-modal').classList.add('hidden');
}

async function loadAssignmentData(assignmentId) {
    try {
        const response = await fetch(`/api/assignments/${assignmentId}`);
        const data = await response.json();
        
        if (data.error) {
            alert('Error loading assignment: ' + data.error);
            return;
        }
        
        const assignment = data.assignment;
        document.getElementById('assignment-name').value = assignment.name;
        document.getElementById('assignment-description').value = assignment.description || '';
        document.getElementById('assignment-rubric').value = assignment.rubric_filename;
        document.getElementById('assignment-instructions').value = assignment.custom_instructions || '';
        document.getElementById('assignment-folder').value = assignment.drive_folder_id;
        document.getElementById('assignment-status').value = assignment.status;
    } catch (error) {
        alert('Error loading assignment: ' + error.message);
    }
}

async function handleAssignmentSubmit(e) {
    e.preventDefault();
    
    const assignmentId = document.getElementById('assignment-id').value;
    const data = {
        name: document.getElementById('assignment-name').value,
        description: document.getElementById('assignment-description').value,
        rubric_filename: document.getElementById('assignment-rubric').value,
        custom_instructions: document.getElementById('assignment-instructions').value,
        drive_folder_id: document.getElementById('assignment-folder').value,
        status: document.getElementById('assignment-status').value,
        user_email: 'admin@busn403.edu', // TODO: Get from auth
        user_name: 'User',
        user_role: 'ta'
    };
    
    try {
        let response;
        if (assignmentId) {
            response = await fetch(`/api/assignments/${assignmentId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch(`/api/sections/${assignmentsSectionId}/assignments`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        closeAssignmentModal();
        loadAssignments();
    } catch (error) {
        alert('Error saving assignment: ' + error.message);
    }
}

async function editAssignment(assignmentId) {
    openAssignmentModal(assignmentId);
}

async function handleDeleteAssignment() {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) return;
    
    if (!confirm('Are you sure you want to delete this assignment? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/assignments/${assignmentId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        closeAssignmentModal();
        loadAssignments();
    } catch (error) {
        alert('Error deleting assignment: ' + error.message);
    }
}


