// ==========================================
// 1. GLOBALS & CONFIG
// ==========================================
// Simulation Config
const TOTAL_STEPS = 250; // Increased to show the long-term overtaking
let SIM_SPEED = 50;
let stepCount = 0;
let timer = null;

// Chart Instances
let charts = {};

// ==========================================
// 2. AGENT CLASS (Bio-Cybernetic Framework)
// ==========================================
class Agent {
    constructor(name, type) {
        this.name = name;
        this.type = type; // 'EFA' (Efficiency-First) or 'HRA' (Homeostatic)

        // Critical State Variables
        this.energy = 100;    // Bio-Energy Reserve
        this.mastery = 0;     // Cumulative Knowledge
        this.stress = 0;      // 0-100 (Cortisol Equivalent)
        this.focus = 100;     // Attention Span

        // Burnout Dynamics
        this.burnoutCount = 0;
        this.burnoutCooldown = 0; // Steps remaining in 'Lockout'
        this.status = "Idle";

        // Trajectory History
        this.history = [];
    }

    step() {
        // --- A. BURNOUT LOCKOUT (The "Penalty Box") ---
        if (this.burnoutCooldown > 0) {
            this.burnoutCooldown--;
            // Slow Recovery during crash
            this.energy = Math.min(100, this.energy + 2);
            this.stress = Math.max(0, this.stress - 2);
            this.status = "BURNOUT LOCK ⚠️";

            // NO LEARNING happens here (Dead Time)
            this.recordHistory();
            return { action: 'LOCKED', msg: `System CRASHED! Rebooting... (${this.burnoutCooldown})`, type: 'burnout' };
        }

        // --- B. DECISION ENGINE ---
        let decision = this.makeDecision();

        // --- C. EXECUTION PHYSICS (Yerkes-Dodson Law) ---
        // 1. Apply Cost
        this.energy = Math.max(0, this.energy - decision.cost);
        if (decision.cost < 0) this.status = "Resting 💤";
        else this.status = "Learning 🧠";

        // 2. Calculate Efficiency Factor (alpha)
        let efficiency = 1.0;

        // Stress Penalty (Inverted-U)
        // Optimal Stress is 30-60. Above 80 is drastic loss.
        if (this.stress > 80) efficiency *= 0.4; // Choking under pressure
        else if (this.stress > 60) efficiency *= 0.8;

        // Fatigue Penalty
        if (this.energy < 20) efficiency *= 0.6; // Exhaustion

        // 3. Apply Gain
        let actualGain = decision.gain * efficiency;
        if (decision.cost < 0) actualGain = 0; // Rest = No gain

        this.mastery += actualGain;

        // --- D. STATE DYNAMICS ---
        // Stress Update
        if (decision.difficulty > 0.6) {
            // Hard tasks spike stress, especially if tired (Reduced factor from 15 to 12 for better "Sprint")
            let strain = (decision.difficulty * 12) + (100 - this.energy) * 0.05;
            this.stress = Math.min(100, this.stress + strain);
        } else {
            // Easy tasks/Rest reduce stress
            this.stress = Math.max(0, this.stress - 8);
        }

        // 4. Focus Dynamics (Flow State: Peak at Stress=50)
        // Bell Curve Proxy: Focus is highest when Stress is moderate (eustress).
        let stressDist = Math.abs(this.stress - 50);
        // 100 at s=50, 25 at s=0/100, scaled by Energy
        this.focus = Math.max(0, (100 - (stressDist * 1.5)) * (this.energy / 100));

        // --- E. CRITICALITY CHECK (Burnout Trigger) ---
        // EFA crashes if pushed too far
        if (this.type === 'EFA' && this.energy <= 5 && this.stress >= 90) {
            this.triggerBurnout("Critical Failure");
        }

        this.recordHistory();

        // Formatting Message
        let type = decision.cost < 0 ? 'recover' : 'learn';
        let msg = decision.cost < 0 ? "Recharging..." : `Gain: ${actualGain.toFixed(1)} (Eff: ${(efficiency * 100).toFixed(0)}%)`;

        return { action: this.status, msg: msg, type: type };
    }

    makeDecision() {
        if (this.type === 'EFA') {
            // == EFFICIENCY-FIRST AGENT (Rational Greedy/Reactive) ==
            // Logic: Maximize Gain/Time. Only rest if FORCED.

            // Reactive Safety Net (Only when critically low)
            if (this.energy < 5 || this.stress > 98) {
                return { cost: -15, gain: 0, difficulty: 0 }; // Forced Rest
            }

            // Otherwise: Rational Greedy (High Difficulty = High Nominal Gain)
            // Agnostic to Stress Efficiency loss (The "Blind Spot")
            return { cost: 15, gain: 15, difficulty: 0.9 };
        }
        else {
            // == HOMEOSTATIC-REGULATED AGENT (Bio-PKT/Proactive) ==
            // Logic: Maintain Equilibrium [40-60 Stress]. Sandwich Scheduling.

            // Proactive Safety Check
            if (this.stress > 70 || this.energy < 30) {
                // "Sandwich": Insert Low Load task to recover
                return { cost: 5, gain: 6, difficulty: 0.3 }; // Review/Easy Task
            }

            if (this.energy < 20) {
                return { cost: -15, gain: 0, difficulty: 0 }; // Active Rest
            }

            // If "In the Zone" (Flow), push hard
            return { cost: 12, gain: 12, difficulty: 0.8 };
        }
    }

    triggerBurnout(reason) {
        this.burnoutCount++;
        this.burnoutCooldown = 15; // Increased Lockout to 15 steps (More punitive)
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
    // 1. PHASE SPACE CHART (Mastery vs Energy) - The "Science Plot"
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
                x: { title: { display: true, text: 'Cumulative Knowledge (Mastery)', color: '#94a3b8' }, grid: { color: '#334155' } }, // Removed Max Limit
                y: { title: { display: true, text: 'Bio-Energy Reserve (%)', color: '#94a3b8' }, min: 0, max: 100, grid: { color: '#334155' } }
            },
            plugins: { legend: { labels: { color: '#e2e8f0' } } }
        }
    });

    // 2. RADARS
    charts.radarEFA = createRadar('radarGreedy', '#f43f5e'); // Using existing ID
    charts.radarHRA = createRadar('radarBio', '#10b981');   // Using existing ID

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
            labels: ['Energy', 'Focus', 'Calmness', 'Consistency'], // Updated Labels
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
        100 - agent.stress, // Calmness
        Math.max(0, 100 - (agent.burnoutCount * 25)) // Consistency
    ];
    chart.update('none');
}

function updateUI() {
    // EFA UI
    document.getElementById('scoreGreedy').innerText = Math.round(efa.mastery);
    document.getElementById('burnGreedy').innerText = efa.burnoutCount;
    document.getElementById('statusGreedy').innerText = efa.status;

    // HRA UI
    document.getElementById('scoreBio').innerText = Math.round(hra.mastery);
    document.getElementById('burnBio').innerText = hra.burnoutCount;
    document.getElementById('statusBio').innerText = hra.status;
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
