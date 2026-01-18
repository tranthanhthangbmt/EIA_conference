// --- CONFIGURATION CONSTANTS (WILL BE UPDATED BY UI) ---
let SIM_CONFIG = {
    DAYS: 7,
    HOURS_PER_DAY: 10,
    E_MAX: 100.0,
    E_CRITICAL: 20.0,
    E_SAFE_MARGIN: 40.0,
    ALPHA_HIGH: 18.0,
    GAIN_HIGH: 10.0,
    ALPHA_LOW: 3.0,
    GAIN_LOW: 4.0,
    RECOVERY_RATE: 15.0,
    BURNOUT_LOCKOUT: 2
};

// --- SIMULATION LOGIC ---

class VirtualLearner {
    constructor(strategyName) {
        this.strategy = strategyName;
        this.reset();
    }

    reset() {
        this.energy = SIM_CONFIG.E_MAX;
        this.totalKnowledge = 0;
        this.burnoutCount = 0;
        this.isBurntOut = 0; // Countdown timer
        
        this.history = {
            energy: [],
            knowledge: [],
            action: [] // 0: Rest, 1: Low, 2: High
        };
    }

    step() {
        // A. Handle Burnout State
        if (this.isBurntOut > 0) {
            this.energy = Math.min(SIM_CONFIG.E_MAX, this.energy + SIM_CONFIG.RECOVERY_RATE);
            this.logState(0);
            this.isBurntOut--;
            return;
        }

        // B. Decision Making
        let actionType = "REST";

        if (this.strategy === "Greedy") {
            if (this.energy > 0) {
                actionType = "HIGH";
            } else {
                actionType = "REST";
            }
        } else if (this.strategy === "Bio-PKT") {
            if (this.energy > SIM_CONFIG.E_SAFE_MARGIN) {
                actionType = "HIGH";
            } else if (this.energy > SIM_CONFIG.E_CRITICAL) {
                actionType = "LOW";
            } else {
                actionType = "REST";
            }
        }

        // C. Execute Action
        let currentGain = 0;
        let energyCost = 0;
        let actionCode = 0;

        if (actionType === "HIGH") {
            currentGain = SIM_CONFIG.GAIN_HIGH;
            energyCost = SIM_CONFIG.ALPHA_HIGH;
            actionCode = 2;
        } else if (actionType === "LOW") {
            currentGain = SIM_CONFIG.GAIN_LOW;
            energyCost = SIM_CONFIG.ALPHA_LOW;
            actionCode = 1;
        } else {
            currentGain = 0;
            energyCost = -SIM_CONFIG.RECOVERY_RATE;
            actionCode = 0;
        }

        // Update State
        this.totalKnowledge += currentGain;
        this.energy -= energyCost;
        this.energy = Math.max(0, Math.min(SIM_CONFIG.E_MAX, this.energy));

        // D. Burnout Check
        if (this.energy < SIM_CONFIG.E_CRITICAL && actionType === "HIGH") {
            this.isBurntOut = SIM_CONFIG.BURNOUT_LOCKOUT;
            this.burnoutCount++;
            this.totalKnowledge -= currentGain * 0.5; // Penalty
        }

        this.logState(actionCode);
    }

    logState(actionCode) {
        this.history.energy.push(this.energy);
        this.history.knowledge.push(this.totalKnowledge);
        this.history.action.push(actionCode);
    }
}

// --- VISUALIZATION SETUP ---

let energyChart, knowledgeChart;
const agentGreedy = new VirtualLearner("Greedy");
const agentBio = new VirtualLearner("Bio-PKT");

function initCharts() {
    // Shared Options
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                labels: { color: '#94a3b8' }
            }
        },
        scales: {
            x: {
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#94a3b8' }
            },
            y: {
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#94a3b8' }
            }
        }
    };

    // Energy Chart
    const ctxEnergy = document.getElementById('energyChart').getContext('2d');
    energyChart = new Chart(ctxEnergy, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Greedy (Baseline)',
                    borderColor: '#ff4757',
                    backgroundColor: 'rgba(255, 71, 87, 0.1)',
                    borderWidth: 2,
                    data: [],
                    tension: 0.3,
                    pointRadius: 0
                },
                {
                    label: 'Bio-PKT (Proposed)',
                    borderColor: '#2ed573',
                    backgroundColor: 'rgba(46, 213, 115, 0.1)',
                    borderWidth: 2,
                    data: [],
                    tension: 0.3,
                    pointRadius: 0
                },
                // Critical Threshold Line hack
                {
                    label: 'Critical Threshold',
                    borderColor: 'rgba(255, 255, 255, 0.3)',
                    borderDash: [5, 5],
                    borderWidth: 1,
                    data: [],
                    pointRadius: 0
                }
            ]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    min: 0,
                    max: 110
                }
            }
        }
    });

    // Knowledge Chart
    const ctxKnowledge = document.getElementById('knowledgeChart').getContext('2d');
    knowledgeChart = new Chart(ctxKnowledge, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Greedy (Baseline)',
                    borderColor: '#ff4757',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    data: [],
                    pointRadius: 0
                },
                {
                    label: 'Bio-PKT (Proposed)',
                    borderColor: '#2ed573',
                    borderWidth: 3,
                    data: [],
                    pointRadius: 0
                }
            ]
        },
        options: commonOptions
    });
}

function runSimulation() {
    // 1. Get Params from UI
    SIM_CONFIG.DAYS = parseInt(document.getElementById('simDays').value);
    SIM_CONFIG.HOURS_PER_DAY = parseInt(document.getElementById('hoursPerDay').value);
    SIM_CONFIG.E_CRITICAL = parseInt(document.getElementById('eCritical').value);
    SIM_CONFIG.E_SAFE_MARGIN = parseInt(document.getElementById('eSafeMargin').value);
    SIM_CONFIG.ALPHA_HIGH = parseInt(document.getElementById('alphaHigh').value);
    SIM_CONFIG.ALPHA_LOW = parseInt(document.getElementById('alphaLow').value);
    SIM_CONFIG.RECOVERY_RATE = parseInt(document.getElementById('recoveryRate').value);

    // 2. Reset Agents
    agentGreedy.reset();
    agentBio.reset();

    // 3. Run Loop
    const totalSteps = SIM_CONFIG.DAYS * SIM_CONFIG.HOURS_PER_DAY;
    const timeLabels = [];
    const criticalLine = [];

    for (let t = 0; t < totalSteps; t++) {
        // Daily Energy Reset (Simulate Sleeping)
        if (t > 0 && t % SIM_CONFIG.HOURS_PER_DAY === 0) {
            agentGreedy.energy = SIM_CONFIG.E_MAX;
            agentBio.energy = SIM_CONFIG.E_MAX;
        }

        agentGreedy.step();
        agentBio.step();

        timeLabels.push(`H${t}`);
        criticalLine.push(SIM_CONFIG.E_CRITICAL);
    }

    // 4. Update UI Stats
    document.getElementById('greedyScore').textContent = agentGreedy.totalKnowledge.toFixed(0);
    document.getElementById('greedyBurnout').textContent = `Burnouts: ${agentGreedy.burnoutCount}`;
    
    document.getElementById('bioScore').textContent = agentBio.totalKnowledge.toFixed(0);
    document.getElementById('bioBurnout').textContent = `Burnouts: ${agentBio.burnoutCount}`;

    const imp = ((agentBio.totalKnowledge - agentGreedy.totalKnowledge) / agentGreedy.totalKnowledge) * 100;
    document.getElementById('improvementScore').textContent = `+${imp.toFixed(1)}%`;

    // 5. Update Charts
    energyChart.data.labels = timeLabels;
    energyChart.data.datasets[0].data = agentGreedy.history.energy;
    energyChart.data.datasets[1].data = agentBio.history.energy;
    energyChart.data.datasets[2].data = criticalLine; // Threshold line
    energyChart.update();

    knowledgeChart.data.labels = timeLabels;
    knowledgeChart.data.datasets[0].data = agentGreedy.history.knowledge;
    knowledgeChart.data.datasets[1].data = agentBio.history.knowledge;
    knowledgeChart.update();
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    runSimulation();

    // Bind all inputs
    document.querySelectorAll('input[type="range"]').forEach(input => {
        input.addEventListener('input', runSimulation);
    });

    document.getElementById('resetBtn').addEventListener('click', () => {
        // Reset values to defaults (manually matching HTML defaults)
        document.getElementById('simDays').value = 7;
        document.getElementById('hoursPerDay').value = 10;
        document.getElementById('eCritical').value = 20;
        document.getElementById('eSafeMargin').value = 40;
        document.getElementById('alphaHigh').value = 18;
        document.getElementById('alphaLow').value = 3;
        document.getElementById('recoveryRate').value = 15;
        
        // Trigger updates for outputs
        document.querySelectorAll('input[type="range"]').forEach(input => {
           input.nextElementSibling.value = input.value; 
        });

        runSimulation();
    });
});
