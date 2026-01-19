// ==========================================
// 1. GLOBALS & CONFIG
// ==========================================
// Simulation Config
const TOTAL_STEPS = 200;
let SIM_SPEED = 50;
let stepCount = 0;
let timer = null;

// Chart Instances
let charts = {};

// ==========================================
// 2. AGENT CLASS (Psychometric Digital Twin)
// ==========================================
class Agent {
    constructor(name, type) {
        this.name = name;
        this.type = type; // 'GREEDY' or 'BIO'

        // Physical State
        this.energy = 100;    // 0-100%
        this.mastery = 0;     // Cumulative Knowledge

        // Psychological State
        this.stress = 0;      // 0-100 (Anxiety)
        this.focus = 100;     // 0-100 (Flow/Attention)
        this.burnoutCount = 0;
        this.isRecovering = false;

        // Trajectory History for Phase Space
        this.history = [];
    }

    step() {
        // --- A. RECOVERY LOGIC (Biological Constraints) ---
        if (this.energy < 15) {
            this.isRecovering = true;
            this.burnoutCount++;
            return { action: 'BURNOUT', msg: 'CRITICAL FAILURE', type: 'burnout' };
        }

        if (this.isRecovering) {
            this.energy += 10;
            this.stress = Math.max(0, this.stress - 15);
            this.focus = Math.min(100, this.focus + 10);

            if (this.energy > 90) this.isRecovering = false;
            return { action: 'RECOVER', msg: 'Recharging...', type: 'recover' };
        }

        // --- B. DECISION LOGIC (The Core Difference) ---
        let decision = this.makeDecision();

        // --- C. EXECUTION PHYSICS (Interaction with Environment) ---
        let cost = decision.cost;
        let gain = decision.gain;

        // 1. Fatigue Effect (Diminishing Returns)
        if (this.energy < 50) {
            let fatigueFactor = this.energy / 50;
            gain *= fatigueFactor;
        }

        // 2. Anxiety Effect (Yerkes-Dodson Law - Over-stress kills performance)
        if (this.stress > 80) {
            gain *= 0.5; // Choking under pressure
        }

        // Apply State Changes
        this.energy = Math.max(0, this.energy - cost);
        this.mastery += gain;

        // 3. Stress Dynamics (Yerkes-Dodson)
        // Hard tasks increase stress, especially when tired
        if (decision.difficulty > 0.7) {
            let strain = (decision.difficulty * 20) - (this.energy * 0.1);
            if (strain > 0) this.stress += strain;
        } else {
            this.stress = Math.max(0, this.stress - 5); // Easy task relaxes
        }
        this.stress = Math.min(100, this.stress);

        // 4. Focus Dynamics
        // Energy + Low Stress = High Focus
        this.focus = Math.max(0, this.energy - (this.stress * 0.5));

        // Record Trajectory
        this.history.push({ x: this.mastery, y: this.energy });

        return { action: 'LEARN', msg: `Learning (Diff: ${decision.difficulty.toFixed(1)})`, type: 'learn' };
    }

    makeDecision() {
        if (this.type === 'GREEDY') {
            // RATIONAL GREEDY: Only cares about GAIN.
            // Myopic Optimization: "I can get 10 points now? I take it."
            // Ignores Cost (15 energy) and Risk (0.9 difficulty).
            return { cost: 15, gain: 10, difficulty: 0.9 };
        }
        else {
            // BIO-PKT: Homeostatic Regulation.
            // Cares about SUSTAINABILITY.

            if (this.energy > 70) {
                // High Energy: Push hard
                return { cost: 15, gain: 10, difficulty: 0.9 };
            }
            if (this.energy > 30) {
                // Medium Energy: Pace yourself
                return { cost: 8, gain: 6, difficulty: 0.5 };
            }
            // Low Energy: Active Recovery (Negative Cost = Gain Energy)
            return { cost: -15, gain: 0, difficulty: 0 };
        }
    }
}

// ==========================================
// 3. SIMULATION CONTROLLER
// ==========================================
let greedy = new Agent('Greedy', 'GREEDY');
let bio = new Agent('Bio', 'BIO');

function restartSim() {
    if (timer) clearInterval(timer);
    greedy = new Agent('Greedy', 'GREEDY');
    bio = new Agent('Bio', 'BIO');
    stepCount = 0;

    // Clear UI & Charts
    document.getElementById('console-log').innerHTML = '';
    initCharts();

    // Start Loop
    runGameLoop();
}

function runGameLoop() {
    if (timer) clearInterval(timer);
    timer = setInterval(tick, SIM_SPEED);
}

function updateSpeed(val) {
    SIM_SPEED = 210 - val; // Invert logic: val 10=slow, 200=fast
    document.getElementById('valSpeed').innerText = SIM_SPEED;
    if (timer) runGameLoop();
}

function tick() {
    stepCount++;
    if (stepCount > TOTAL_STEPS) {
        clearInterval(timer);
        log("Experiment Completed.", "system");
        return;
    }

    let resG = greedy.step();
    let resB = bio.step();

    updateUI();
    updateCharts();

    // Log Notable Events
    if (resG.action === 'BURNOUT') log(`[GREEDY] CRASHED due to burnout!`, 'greedy');
    if (resB.action === 'RECOVER' && !bio.isRecovering) log(`[BIO] Entering Strategic Rest`, 'bio');
}

// ==========================================
// 4. VISUALIZATION ENGINE (Chart.js)
// ==========================================
function initCharts() {
    // 1. PHASE SPACE CHART (Energy vs Mastery) - The "Science Plot"
    const ctxPhase = document.getElementById('phaseChart').getContext('2d');
    if (charts.phase) charts.phase.destroy();

    charts.phase = new Chart(ctxPhase, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Greedy Trajectory',
                    data: [],
                    borderColor: '#f43f5e',
                    backgroundColor: '#f43f5e',
                    showLine: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1
                },
                {
                    label: 'Bio-PKT Trajectory',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: '#10b981',
                    showLine: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4 // Smoother curve for Bio
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
                x: { title: { display: true, text: 'Cumulative Knowledge (Mastery)', color: '#94a3b8' }, grid: { color: '#334155' }, min: 0, max: 1500 },
                y: { title: { display: true, text: 'Bio-Energy Reserve (%)', color: '#94a3b8' }, min: 0, max: 100, grid: { color: '#334155' } }
            },
            plugins: { legend: { labels: { color: '#e2e8f0' } } }
        }
    });

    // 2. RADAR CHARTS (Dual)
    charts.radarGreedy = createRadar('radarGreedy', '#f43f5e');
    charts.radarBio = createRadar('radarBio', '#10b981');

    // 3. LINE CHART (Knowledge over Time)
    const ctxLine = document.getElementById('lineChart').getContext('2d');
    if (charts.line) charts.line.destroy();
    charts.line = new Chart(ctxLine, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Greedy', borderColor: '#f43f5e', data: [], pointRadius: 0 }, { label: 'Bio-PKT', borderColor: '#10b981', data: [], pointRadius: 0 }] },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: { x: { display: false }, y: { grid: { color: '#334155' } } },
            plugins: { legend: { display: false } }
        }
    });
}

function createRadar(id, color) {
    return new Chart(document.getElementById(id).getContext('2d'), {
        type: 'radar',
        data: {
            labels: ['Energy', 'Focus', 'Calmness', 'Consistency'],
            datasets: [{ label: 'State', data: [100, 100, 100, 100], backgroundColor: color + '33', borderColor: color, borderWidth: 2 }]
        },
        options: {
            scales: {
                r: {
                    min: 0, max: 100,
                    ticks: { display: false },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#94a3b8', font: { size: 10 } }
                }
            },
            plugins: { legend: { display: false } },
            animation: false
        }
    });
}

function updateCharts() {
    // Update Phase Space
    charts.phase.data.datasets[0].data.push({ x: greedy.mastery, y: greedy.energy });
    charts.phase.data.datasets[1].data.push({ x: bio.mastery, y: bio.energy });
    charts.phase.update('none');

    // Update Radars
    updateRadarData(charts.radarGreedy, greedy);
    updateRadarData(charts.radarBio, bio);

    // Update Line Chart
    charts.line.data.labels.push(stepCount);
    charts.line.data.datasets[0].data.push(greedy.mastery);
    charts.line.data.datasets[1].data.push(bio.mastery);
    charts.line.update('none');
}

function updateRadarData(chart, agent) {
    chart.data.datasets[0].data = [
        agent.energy,
        agent.focus,
        100 - agent.stress, // Calmness (inverse of stress)
        Math.max(0, 100 - (agent.burnoutCount * 20)) // Consistency (Penalty for crashing)
    ];
    chart.update('none');
}

function updateUI() {
    // Greedy UI
    document.getElementById('scoreGreedy').innerText = Math.round(greedy.mastery);
    document.getElementById('burnGreedy').innerText = greedy.burnoutCount;
    document.getElementById('statusGreedy').innerText = greedy.isRecovering ? "CRASHED" : "Grinding";

    // Bio UI
    document.getElementById('scoreBio').innerText = Math.round(bio.mastery);
    document.getElementById('burnBio').innerText = bio.burnoutCount;
    document.getElementById('statusBio').innerText = bio.isRecovering ? "Resting" : "Optimized";
}

function log(msg, type) {
    const box = document.getElementById('console-log');
    const div = document.createElement('div');
    div.innerText = `[T=${stepCount}] ${msg}`;
    div.className = `log-line log-${type}`;
    if (type === 'system') div.style.color = '#38bdf8';
    box.prepend(div);
}

window.onload = restartSim;
