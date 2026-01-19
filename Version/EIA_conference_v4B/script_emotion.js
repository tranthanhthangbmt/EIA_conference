// ==========================================
// 1. GLOBALS & CONFIG
// ==========================================
// Simulation Config
// Simulation Config
const TOTAL_STEPS = 250;
let SIM_SPEED = 190; // Default per v13
let stepCount = 0;
let timer = null;

let charts = {};

// v13 Status Labels
const STATUS_LABELS = {
    NORMAL: "<span style='color:green'>🟢 Stable</span>",
    STRESSED: "<span style='color:orange'>🟠 Stressed</span>",
    CRITICAL: "<span style='color:red; font-weight:bold'>🔥 CRITICAL</span>",
    BURNOUT: "<span style='background:red; color:white; padding:2px'>⛔ BURNOUT</span>",
    RECOVERY: "<span style='color:blue'>💤 Recovery</span>",
    FLOW: "<span style='color:purple; font-weight:bold'>✨ FLOW</span>"
};

// ==========================================
// 2. HELPER FUNCTIONS
// ==========================================
function calculateEfficiency(stress) {
    // Yerkes-Dodson Law (Explicit Formula)
    // Optimal: 50 (1.0)
    // High Stress: > 70 (0.5), > 90 (0.2)
    // Low Stress (Boredom): < 20 (0.6)

    if (stress > 90) return 0.2;
    if (stress > 70) return 0.5;
    if (stress < 20) return 0.6; // Boredom penalty
    return 1.0; // Optimal flow
}

// ==========================================
// 3. AGENT CLASS
// ==========================================
class Agent {
    constructor(name, type) {
        this.name = name;
        this.type = type;

        this.energy = 100;
        this.mastery = 0;
        this.stress = 0;
        this.focus = 100;

        this.burnoutCount = 0;
        this.burnoutCooldown = 0;
        this.status = "Idle";

        this.history = [];
    }

    step() {
        // --- A. BURNOUT LOCK ---
        if (this.burnoutCooldown > 0) {
            this.burnoutCooldown--;
            this.energy = Math.min(100, this.energy + 2); // Slow recovery
            this.stress = Math.max(0, this.stress - 1);   // Slow stress relief
            this.status = "BURNOUT LOCK ⚠️";

            this.recordHistory();
            return { action: 'LOCKED', msg: `System CRASHED! (${this.burnoutCooldown})`, type: 'burnout' };
        }

        // --- B. DECISION ---
        let decision = this.makeDecision();

        // --- C. EXECUTION & EFFICIENCY ---
        this.energy = Math.max(0, this.energy - decision.cost);
        if (decision.cost < 0) this.status = "Resting 💤";
        else this.status = "Learning 🧠";

        // Calculate Efficiency (Yerkes-Dodson)
        let efficiency = calculateEfficiency(this.stress);

        // Fatigue Penalty
        if (this.energy < 20) efficiency *= 0.6;

        let actualGain = decision.gain * efficiency;
        if (decision.cost < 0) actualGain = 0;

        this.mastery += actualGain;

        // --- D. STATE DYNAMICS ---
        // Stress Update
        if (decision.difficulty > 0.6) {
            let strain = (decision.difficulty * 12) + (100 - this.energy) * 0.05;
            this.stress = Math.min(100, this.stress + strain);
        } else {
            this.stress = Math.max(0, this.stress - 8);
        }

        // Focus Update (Flow-based)
        let stressDist = Math.abs(this.stress - 50);
        this.focus = Math.max(0, (100 - (stressDist * 1.5)) * (this.energy / 100));

        // --- E. CRITICALITY CHECK ---
        if (this.type === 'EFA' && this.energy <= 5 && this.stress >= 90) {
            this.triggerBurnout();
        }

        this.recordHistory();

        let showEff = (efficiency * 100).toFixed(0);
        let msg = decision.cost < 0 ? "Recharging..." : `Gain: ${actualGain.toFixed(1)} (Eff: ${showEff}%)`;

        return { action: this.status, msg: msg, type: decision.cost < 0 ? 'recover' : 'learn' };
    }

    makeDecision() {
        if (this.type === 'EFA') {
            // Efficiency-First Agent (Greedy)
            if (this.energy < 5 || this.stress > 98) return { cost: -15, gain: 0, difficulty: 0 };
            return { cost: 15, gain: 15, difficulty: 0.9 };
        }
        else {
            // Homeostatic-Regulated Agent (Bio-PKT)
            if (this.stress > 70 || this.energy < 30) return { cost: 5, gain: 6, difficulty: 0.3 };
            if (this.energy < 15) return { cost: -15, gain: 0, difficulty: 0 };
            return { cost: 12, gain: 12, difficulty: 0.8 };
        }
    }

    triggerBurnout() {
        this.burnoutCount++;
        this.burnoutCooldown = 10; // 10 Steps as per PhanBien12
        this.status = "SYSTEM CRASH";
    }

    recordHistory() {
        this.history.push({ x: this.mastery, y: this.energy });
    }
}

// ==========================================
// 3. SIMULATION CONTROLLER
// ==========================================
let efa = new Agent('EFA', 'EFA');
let hra = new Agent('HRA', 'HRA');

function restartSim() {
    if (timer) clearInterval(timer);
    efa = new Agent('EFA', 'EFA');
    hra = new Agent('HRA', 'HRA');
    stepCount = 0;

    document.getElementById('console-log').innerHTML = '';
    initCharts();

    runGameLoop();
}

function runGameLoop() {
    if (timer) clearInterval(timer);
    timer = setInterval(tick, SIM_SPEED);
}

function updateSpeed(val) {
    SIM_SPEED = 210 - val;
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

    let resEFA = efa.step();
    let resHRA = hra.step();

    updateUI();
    updateCharts();

    // Log Notable Events
    if (resEFA.type === 'burnout') log(`[EFA] SYSTEM CRASH! (Rebooting...)`, 'greedy');
    if (resHRA.action === 'Resting 💤' && hra.energy > 30) log(`[HRA] Proactive Rest (Sandwich)`, 'bio');
}

// ==========================================
// 4. VISUALIZATION ENGINE
// ==========================================
function initCharts() {
    // 1. PHASE SPACE CHART
    const ctxPhase = document.getElementById('phaseChart').getContext('2d');
    if (charts.phase) charts.phase.destroy();

    charts.phase = new Chart(ctxPhase, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'EFA Trajectory (Sawtooth)',
                    data: [],
                    borderColor: '#f43f5e',
                    backgroundColor: '#f43f5e',
                    showLine: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0
                },
                {
                    label: 'HRA Trajectory (Spiral)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: '#10b981',
                    showLine: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
                x: { title: { display: true, text: 'Cumulative Knowledge (Mastery)', color: '#94a3b8' }, grid: { color: '#334155' } },
                y: { title: { display: true, text: 'Bio-Energy Reserve (%)', color: '#94a3b8' }, min: 0, max: 100, grid: { color: '#334155' } }
            },
            plugins: { legend: { labels: { color: '#e2e8f0' } } }
        }
    });

    // 2. RADARS
    charts.radarEFA = createRadar('radarGreedy', '#f43f5e');
    charts.radarHRA = createRadar('radarBio', '#10b981');

    // 3. LINE CHART
    const ctxLine = document.getElementById('lineChart').getContext('2d');
    if (charts.line) charts.line.destroy();
    charts.line = new Chart(ctxLine, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'EFA', borderColor: '#f43f5e', data: [], pointRadius: 0 }, { label: 'HRA', borderColor: '#10b981', data: [], pointRadius: 0 }] },
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
    // Phase Update
    charts.phase.data.datasets[0].data.push({ x: efa.mastery, y: efa.energy });
    charts.phase.data.datasets[1].data.push({ x: hra.mastery, y: hra.energy });
    charts.phase.update('none');

    // Radar Update
    updateRadarData(charts.radarEFA, efa);
    updateRadarData(charts.radarHRA, hra);

    // Line Update
    charts.line.data.labels.push(stepCount);
    charts.line.data.datasets[0].data.push(efa.mastery);
    charts.line.data.datasets[1].data.push(hra.mastery);
    charts.line.update('none');
}

function updateRadarData(chart, agent) {
    chart.data.datasets[0].data = [
        agent.energy,
        agent.focus,
        100 - agent.stress,
        Math.max(0, 100 - (agent.burnoutCount * 25))
    ];
    chart.update('none');
}

function updateUI() {
    document.getElementById('scoreGreedy').innerText = Math.round(efa.mastery);
    document.getElementById('burnGreedy').innerText = efa.burnoutCount;
    document.getElementById('statusGreedy').innerHTML = efa.status; // Use innerHTML
    if (efa.lastEfficiency) document.getElementById('efa-efficiency').innerText = efa.lastEfficiency + "%";

    document.getElementById('scoreBio').innerText = Math.round(hra.mastery);
    document.getElementById('burnBio').innerText = hra.burnoutCount;
    document.getElementById('statusBio').innerHTML = hra.status; // Use innerHTML
    if (hra.lastEfficiency) document.getElementById('bio-efficiency').innerText = hra.lastEfficiency + "%";
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
