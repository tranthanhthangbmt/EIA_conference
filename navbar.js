// Global Scientific Navbar Injection
document.addEventListener("DOMContentLoaded", function () {
    const navbarHTML = `
    <nav class="sci-navbar">
        <div class="nav-brand">🧬 Bio-PKT v16</div>
        <div class="nav-links">
            <a href="index.html" class="nav-item" title="Home Hub" id="nav-home">🏠 Hub</a>
            <span class="nav-sep">|</span>
            <a href="graph.html" class="nav-item" title="Level 1: Micro-Mechanism" id="nav-graph">🕸️ Micro</a>
            <a href="emotion.html" class="nav-item" title="Level 2: Psych-Dynamics" id="nav-emotion">🧠 Psych</a>
            <a href="energy.html" class="nav-item" title="Level 2: Bio-Dynamics" id="nav-energy">⚡ Bio</a>
            <a href="treeKnowledge.html" class="nav-item" title="Level 3: Macro-System" id="nav-sys">🌌 Macro</a>
            <span class="nav-sep">|</span>
            <a href="dashboard.html" class="nav-item highlight" title="Level 4: Critical Evidence" id="nav-dash">📊 Report</a>
        </div>
    </nav>
    `;

    document.body.insertAdjacentHTML("afterbegin", navbarHTML);

    // Highlight current page
    // Highlight current page and Update Brand Title
    const currentPath = window.location.pathname.split("/").pop();
    const linkMap = {
        'index.html': { id: 'nav-home', title: '' },
        'graph.html': { id: 'nav-graph', title: 'Micro-View' },
        'emotion.html': { id: 'nav-emotion', title: 'Psych-Dynamics' },
        'energy.html': { id: 'nav-energy', title: 'Bio-Dynamics' },
        'treeKnowledge.html': { id: 'nav-sys', title: 'Phase Space' },
        'dashboard.html': { id: 'nav-dash', title: 'Final Report' }
    };

    // Handle root
    let activeKey = linkMap[currentPath] ? currentPath : 'index.html';
    if (currentPath === '') activeKey = 'index.html';

    const activeData = linkMap[activeKey];
    const activeEl = document.getElementById(activeData.id);
    if (activeEl) activeEl.classList.add('active');

    // Update Brand ID
    if (activeData.title) {
        document.querySelector('.nav-brand').innerHTML = `🧬 Bio-PKT <span style="opacity:0.5; margin:0 5px;">|</span> ${activeData.title}`;
    }
});
