
// ==========================================
// SYSTEM PILLAR: 3D PHASE SPACE (v16.0)
// ==========================================
// Visualizes the "Burnout Plane" (Energy vs Mastery vs Stress)
// Hooked from script_emotion.js via window.update3DChart()

let plotDiv = null;

// Initialize Plotly 3D Chart
function init3DChart() {
    plotDiv = document.getElementById('phaseSpaceChart');
    if (!plotDiv) return;

    const startTraceEFA = {
        x: [0], y: [100], z: [0],
        mode: 'lines',
        type: 'scatter3d',
        name: 'EFA (Greedy)',
        line: { color: '#f43f5e', width: 6 },
        marker: { size: 0 }
    };

    const startTraceHRA = {
        x: [0], y: [100], z: [0],
        mode: 'lines',
        type: 'scatter3d',
        name: 'Bio-PKT (HRA)',
        line: { color: '#10b981', width: 6 },
        marker: { size: 0 }
    };

    // Burnout Plane (Visual Reference)
    const burnoutPlane = {
        x: [0, 100, 100, 0],
        y: [0, 0, 100, 100],
        z: [80, 80, 80, 80],
        i: [0, 0], j: [1, 2], k: [2, 3],
        type: 'mesh3d',
        opacity: 0.2,
        color: 'red',
        name: 'Burnout Threshold (>80 Stress)'
    };

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        scene: {
            xaxis: { title: 'Mastery', range: [0, 100], gridcolor: '#475569', backgroundcolor: "rgba(0,0,0,0)" },
            yaxis: { title: 'Energy', range: [0, 100], gridcolor: '#475569', backgroundcolor: "rgba(0,0,0,0)" },
            zaxis: { title: 'Stress', range: [0, 100], gridcolor: '#475569', backgroundcolor: "rgba(0,0,0,0)" },
            camera: {
                eye: { x: 1.6, y: 1.6, z: 1.4 }
            }
        },
        margin: { l: 0, r: 0, b: 0, t: 0 },
        legend: { font: { color: 'white' } }
    };

    Plotly.newPlot('phaseSpaceChart', [startTraceEFA, startTraceHRA, burnoutPlane], layout);
}

// Called by script_emotion.js tick()
window.update3DChart = function () {
    if (!plotDiv) { init3DChart(); return; }

    if (typeof efa === 'undefined' || typeof hra === 'undefined') return;

    // Plotly extendTraces is efficient for real-time
    Plotly.extendTraces('phaseSpaceChart', {
        x: [[efa.mastery], [hra.mastery]],
        y: [[efa.energy], [hra.energy]],
        z: [[efa.stress], [hra.stress]]
    }, [0, 1]);

    // Auto-rotate slight camera movement if desired?
    // Maybe too dizzying. Kept static.
};

// Auto-init on load
document.addEventListener('DOMContentLoaded', init3DChart);
