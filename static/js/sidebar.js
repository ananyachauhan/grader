// Unified Sidebar Navigation
let sectionsData = [];
let currentSectionId = null;
let currentSectionNumber = null;

// Initialize sidebar on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSidebar();
});

async function initializeSidebar() {
    // Get current page info from URL
    const urlParams = new URLSearchParams(window.location.search);
    currentSectionId = urlParams.get('section_id');
    currentSectionNumber = urlParams.get('section_number');
    
    // Determine current page
    const path = window.location.pathname;
    const currentPage = getCurrentPage(path);
    
    // Load sections if we're in a section context or on sections page
    if (currentSectionId || path === '/' || path.includes('/assignments') || path.includes('/grade')) {
        await loadSections();
    }
    
    // Render sidebar
    renderSidebar(currentPage);
}

function getCurrentPage(path) {
    if (path === '/') return 'sections';
    if (path === '/review' || path.startsWith('/review/')) return 'review';
    if (path === '/assignments') return 'assignments';
    if (path === '/grade') return 'grade';
    if (path.startsWith('/assignment/')) return 'assignment-detail';
    return 'sections';
}

async function loadSections() {
    try {
        const response = await fetch('/api/sections');
        const data = await response.json();
        if (data.sections) {
            sectionsData = data.sections;
        }
    } catch (error) {
        console.error('Error loading sections for sidebar:', error);
    }
}

function renderSidebar(currentPage) {
    const sidebar = document.querySelector('.sidebar-nav');
    if (!sidebar) return;
    
    sidebar.innerHTML = '';
    
    // Sections menu item (with submenu if we have sections)
    const sectionsItem = document.createElement('li');
    sectionsItem.className = 'sidebar-nav-item';
    
    if (sectionsData.length > 0 && (currentSectionId || currentPage !== 'sections')) {
        sectionsItem.classList.add('has-submenu');
        // Auto-expand if we're in a section context
        if (currentSectionId) {
            sectionsItem.classList.add('expanded');
        }
    }
    
    const sectionsLink = document.createElement('a');
    sectionsLink.href = '/';
    sectionsLink.className = 'sidebar-nav-link';
    if (currentPage === 'sections' || currentPage === 'assignments' || currentPage === 'grade' || currentPage === 'assignment-detail') {
        sectionsLink.classList.add('active');
    }
    sectionsLink.innerHTML = '<span style="color: #ffffff !important; font-size: 22px; text-shadow: 0 1px 2px rgba(0,0,0,0.3);">Sections</span>';
    
    // Add click handler for expandable menu
    if (sectionsItem.classList.contains('has-submenu')) {
        sectionsLink.addEventListener('click', (e) => {
            if (currentPage === 'sections') {
                e.preventDefault();
                sectionsItem.classList.toggle('expanded');
            }
        });
    }
    
    sectionsItem.appendChild(sectionsLink);
    
    // Add submenu for sections
    if (sectionsData.length > 0 && (currentSectionId || currentPage !== 'sections')) {
        const submenu = document.createElement('ul');
        submenu.className = 'sidebar-nav-submenu';
        
        sectionsData.forEach(section => {
            const subItem = document.createElement('li');
            subItem.className = 'sidebar-nav-submenu-item';
            
            const subLink = document.createElement('a');
            subLink.href = `/assignments?section_id=${section.id}&section_number=${section.section_number}`;
            subLink.className = 'sidebar-nav-submenu-link';
            
            // Mark active if this is the current section
            if (currentSectionId && parseInt(currentSectionId) === section.id) {
                subLink.classList.add('active');
            }
            
            subLink.textContent = `Section ${section.section_number}`;
            subItem.appendChild(subLink);
            submenu.appendChild(subItem);
        });
        
        sectionsItem.appendChild(submenu);
    }
    
    sidebar.appendChild(sectionsItem);
    
    // Review menu item
    const reviewItem = document.createElement('li');
    reviewItem.className = 'sidebar-nav-item';
    
    const reviewLink = document.createElement('a');
    reviewLink.href = '/review';
    reviewLink.className = 'sidebar-nav-link';
    if (currentPage === 'review') {
        reviewLink.classList.add('active');
    }
    reviewLink.innerHTML = '<span style="color: #ffffff !important; font-size: 22px; text-shadow: 0 1px 2px rgba(0,0,0,0.3);">Review</span>';
    
    reviewItem.appendChild(reviewLink);
    sidebar.appendChild(reviewItem);
}

