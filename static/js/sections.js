// Sections page JavaScript
document.addEventListener('DOMContentLoaded', () => {
    loadSections();
});

async function loadSections() {
    try {
        const response = await fetch('/api/sections');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('sections-grid').innerHTML = `<p style="color: #c62828;">Error: ${data.error}</p>`;
            return;
        }
        
        displaySections(data.sections);
    } catch (error) {
        document.getElementById('sections-grid').innerHTML = `<p style="color: #c62828;">Error loading sections: ${error.message}</p>`;
    }
}

function displaySections(sections) {
    const container = document.getElementById('sections-grid');
    
    if (sections.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: var(--text-medium); grid-column: 1 / -1;">
                <div style="font-size: 64px; margin-bottom: 20px;">📚</div>
                <p style="font-size: 20px; margin-bottom: 8px;">No sections available</p>
                <p style="font-size: 16px;">Contact your administrator to add sections</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = sections.map(section => `
        <div class="section-card" data-section-id="${section.id}" data-section-number="${section.section_number}">
            <div style="font-size: 48px; margin-bottom: 16px;">🎓</div>
            <h2>Section ${section.section_number}</h2>
            <p style="font-size: 20px; font-weight: 500; color: var(--aggie-maroon); margin: 12px 0;">${section.assignment_count} Assignment${section.assignment_count !== 1 ? 's' : ''}</p>
            <p class="section-subtitle">Click to view assignments</p>
        </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.section-card').forEach(card => {
        card.addEventListener('click', () => {
            const sectionId = card.dataset.sectionId;
            const sectionNumber = card.dataset.sectionNumber;
            window.location.href = `/assignments?section_id=${sectionId}&section_number=${sectionNumber}`;
        });
        card.style.cursor = 'pointer';
    });
}

