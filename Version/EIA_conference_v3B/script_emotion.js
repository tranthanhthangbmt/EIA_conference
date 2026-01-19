// ==========================================
// 1. GRAPH DEFINITION (DAG + SUBJECTS)
// ==========================================
const K_GRAPH = {
    'A': { id: 'A', label: 'Intro AI', level: 0, difficulty: 0.3, parents: [], subject: 'Theory', color: '#3b82f6' },
    'B': { id: 'B', label: 'Python Basics', level: 0, difficulty: 0.3, parents: [], subject: 'Theory', color: '#3b82f6' },
    'C': { id: 'C', label: 'ML Algos', level: 1, difficulty: 0.6, parents: ['A'], subject: 'Coding', color: '#f59e0b' },
    'D': { id: 'D', label: 'Data Proc', level: 1, difficulty: 0.6, parents: ['B'], subject: 'Coding', color: '#f59e0b' },
    'E': { id: 'E', label: 'Deep Learning', level: 2, difficulty: 0.8, parents: ['C', 'D'], subject: 'Math', color: '#ef4444' },
    'F': { id: 'F', label: 'Transformer', level: 3, difficulty: 1.0, parents: ['E'], subject: 'Math', color: '#ef4444' }
};
const NODE_IDS = Object.keys(K_GRAPH);

// GLOBALS
let greedyAgent, bioAgent;
let greedyData, bioData;
let simulationInterval;
let SIM_SPEED = 200; // Slower for cognitive inertia visibility
let chartEnergy;

// PARAMS (Hardcoded for Demo)
const PARAMS = { recovRate: 15, nonLinear: true };

// ==========================================
// 2. AGENT LOGIC (EMOTION + SWITCHING)
// ==========================================
class GraphAgent {
    constructor(name, strategy) {
        this.name = name;
        this.strategy = strategy;
        this.energy = 100;
        this.mastery = { 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 };
        this.currentNode = null;
        this.lastNode = null;
        this.burnoutCount = 0;

        // New State Variables
        this.emotion = 'Neutral'; // Neutral, Flow, Focused, Stressed, Exhausted, Frustrated, Relieved
        this.emoji = '😐';
        this.statusMsg = "Ready";

        this.logEnergy = [];
    }

    step() {
        // 1. Burnout Recovery
        if (this.energy < 20) {
            this.energy += 10;
            this.setEmotion('Exhausted');
            this.statusMsg = "Recovering (Burnout)";
            this.currentNode = null;
            return { action: 'REST', msg: this.statusMsg };
        }

        let targetNode = null;
        let unlockeds = NODE_IDS.filter(id => {
            if (this.mastery[id] >= 100) return false;
            let parents = K_GRAPH[id].parents;
            if (parents.length === 0) return true;
            return parents.every(p => this.mastery[p] >= 80);
        });

        // --- STRATEGY ---
        if (this.strategy === 'GREEDY') {
            // Picks Hardest Available (Rational Greedy)
            if (unlockeds.length > 0) {
                unlockeds.sort((a, b) => K_GRAPH[b].level - K_GRAPH[a].level);
                targetNode = unlockeds[0];
            }
        }
        else if (this.strategy === 'BIO') {
            // Picks based on Energy
            if (this.energy > 60) {
                // High Energy -> Hardest
                unlockeds.sort((a, b) => K_GRAPH[b].level - K_GRAPH[a].level);
                if (unlockeds.length > 0) targetNode = unlockeds[0];
            } else if (this.energy > 30) {
                // Med Energy -> Easiest (Pacing)
                unlockeds.sort((a, b) => K_GRAPH[a].level - K_GRAPH[b].level);
                if (unlockeds.length > 0) targetNode = unlockeds[0];
            } else {
                targetNode = null; // Rest
            }
        }

        // --- EXECUTION ---
        if (!targetNode) {
            this.energy = Math.min(100, this.energy + 15);
            this.setEmotion('Relieved');
            this.statusMsg = "Strategic Resting";
            this.currentNode = null;
            return { action: 'REST', msg: this.statusMsg };
        }

        // Subject Switching Logic
        let switchMsg = "";
        if (this.lastNode && K_GRAPH[targetNode].subject !== K_GRAPH[this.lastNode].subject) {
            switchMsg = `[Switch: ${K_GRAPH[this.lastNode].subject} -> ${K_GRAPH[targetNode].subject}]`;
            this.energy -= 5; // Switching Cost
        }

        // Learning Physics
        let cost = (K_GRAPH[targetNode].level + 1) * 8;
        if (PARAMS.nonLinear) cost *= (1 + (100 - this.energy) / 100);

        let gain = 10;
        if (this.energy < 50) gain *= (this.energy / 50); // Diminishing returns

        this.energy -= cost;
        this.mastery[targetNode] = Math.min(100, this.mastery[targetNode] + gain);

        this.lastNode = this.currentNode;
        this.currentNode = targetNode;

        // --- EMOTION UPDATE (FLOW THEORY) ---
        // Matrix: Energy (Resource) vs Difficulty (Challenge)
        let difficulty = K_GRAPH[targetNode].level; // 0=Theory, 1=Code, 2/3=Math
        this.setComplexEmotion(this.energy, difficulty);

        this.statusMsg = `Learning ${K_GRAPH[targetNode].label}`;

        return {
            action: 'LEARN',
            target: targetNode,
            msg: `${this.statusMsg} ${switchMsg}`,
            switch: switchMsg !== ""
        };
    }

    setComplexEmotion(energy, level) {
        // Levels: 0 (Easy), 1 (Med), 2+ (Hard)
        // Energy: High (>70), Med (30-70), Low (<30)

        if (energy <= 0) {
            this.setEmotion('Burnout'); return;
        }

        if (energy > 70) {
            // High Energy
            if (level >= 2) this.setEmotion('Flow');      // High Challenge + High Energy = FLOW
            else if (level === 1) this.setEmotion('Confident'); // Med Challenge + High Energy = CONFIDENT
            else this.setEmotion('Bored');                // Low Challenge + High Energy = BORED
        }
        else if (energy > 30) {
            // Med Energy
            if (level >= 2) this.setEmotion('Strained');  // High Challenge + Med Energy = STRAINED
            else if (level === 1) this.setEmotion('Focused');   // Med Challenge + Med Energy = FOCUSED
            else this.setEmotion('Relaxed');              // Low Challenge + Med Energy = RELAXED
        }
        else {
            // Low Energy
            if (level >= 2) this.setEmotion('Anxiety');   // High Challenge + Low Energy = ANXIETY
            else if (level === 1) this.setEmotion('Tired');     // Med Challenge + Low Energy = TIRED
            else this.setEmotion('Recovery');             // Low Challenge + Low Energy = RECOVERY (Active Rest)
        }
    }

    setEmotion(state) {
        this.emotion = state;
        switch (state) {
            // Positive (Bio Zone)
            case 'Flow': this.emoji = '🤩'; break;      // High High
            case 'Confident': this.emoji = '😎'; break; // High Med
            case 'Focused': this.emoji = '🙂'; break;   // Med Med
            case 'Relaxed': this.emoji = '😌'; break;   // Med Low
            case 'Recovery': this.emoji = '🛌'; break;  // Low Low (Active Rest)

            // Negative (Greedy Zone)
            case 'Bored': this.emoji = '🥱'; break;     // High Low (Wasted potential)
            case 'Strained': this.emoji = '😣'; break;  // Med High (Pushing it)
            case 'Tired': this.emoji = '😓'; break;     // Low Med
            case 'Anxiety': this.emoji = '😨'; break;   // Low High (DANGER)
            case 'Burnout': this.emoji = '😵'; break;   // CRASH

            default: this.emoji = '😐';
        }
    }

    logHistory() {
        this.logEnergy.push(this.energy);
        if (this.logEnergy.length > 100) this.logEnergy.shift();
    }

    getAverageMastery() {
        return Math.round(NODE_IDS.reduce((a, b) => a + this.mastery[b], 0) / NODE_IDS.length);
    }
}

// ==========================================
// 3. VISUALIZATION
// ==========================================
function initVisNetwork(containerId) {
    let nodes = NODE_IDS.map(id => ({
        id: id,
        label: K_GRAPH[id].label + "\n0%",
        level: K_GRAPH[id].level,
        shape: 'box',
        font: { color: 'white' },
        // Default style
        color: { background: '#334155', border: K_GRAPH[id].color }, // Border indicates Subject
        borderWidth: 2
    }));

    let edges = [];
    NODE_IDS.forEach(id => {
        K_GRAPH[id].parents.forEach(p => edges.push({ from: p, to: id, arrows: 'to' }));
    });

    let data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    let options = {
        layout: { hierarchical: { direction: 'LR', sortMethod: 'directed', levelSeparation: 120 } },
        physics: false,
        nodes: { borderWidthSelected: 4 }
    };

    return {
        net: new vis.Network(document.getElementById(containerId), data, options),
        nodes: data.nodes
    };
}

function updateAgentVis(agent, visData) {
    let updates = [];
    NODE_IDS.forEach(id => {
        let m = agent.mastery[id];
        // Base color based on mastery
        let bg = '#334155';
        if (m >= 100) bg = '#10b981'; // Green (Done)
        else if (m > 0) bg = '#64748b'; // In progress

        // Active Node Highlight
        let borderWidth = 2;
        let borderColor = K_GRAPH[id].color; // Subject Color

        if (agent.currentNode === id) {
            bg = K_GRAPH[id].color; // Active = Subject Color Background
            // Visual pulse effect logic could go here
        }

        updates.push({
            id: id,
            label: `${K_GRAPH[id].label}\n${Math.round(m)}%`,
            color: { background: bg, border: borderColor },
            borderWidth: borderWidth
        });
    });
    visData.nodes.update(updates);
}

function logToConsole(agentName, result) {
    let consoleEl = document.getElementById('console-log');
    let line = document.createElement('div');
    line.className = 'log-line ' + (agentName === 'Greedy' ? 'greedy' : 'bio');
    let time = new Date().toLocaleTimeString().split(' ')[0];

    let content = `[${time}] ${agentName}: ${result.msg}`;
    if (result.switch) content += " 🔄"; // Icon for switch

    if (consoleEl.childElementCount > 20) consoleEl.lastChild.remove();
}

// --- CHARTS ---
let chartFlow; // chartEnergy already declared at top

function initCharts() {
    // 1. Energy Chart
    const ctxE = document.getElementById('energyChart').getContext('2d');
    if (chartEnergy) chartEnergy.destroy();
    chartEnergy = new Chart(ctxE, {
        type: 'line',
        data: {
            labels: Array(100).fill(0).map((_, i) => i),
            datasets: [
                { label: 'Greedy E', data: [], borderColor: '#ef4444', borderWidth: 2, tension: 0.3 },
                { label: 'Bio-PKT E', data: [], borderColor: '#10b981', borderWidth: 2, tension: 0.3 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: { x: { display: false }, y: { min: 0, max: 100, grid: { color: '#334155' } } },
            plugins: { legend: { labels: { color: '#cbd5e1' } } }
        }
    });

    // 2. Flow Map Scatter Chart (Now with Trajectories)
    const ctxF = document.getElementById('flowChart').getContext('2d');
    if (chartFlow) chartFlow.destroy();

    // Define Quadrant Boxes
    const boxAnnotations = {
        box1: { type: 'box', xMin: 0, xMax: 50, yMin: 1.5, yMax: 3.5, backgroundColor: 'rgba(239, 68, 68, 0.2)', borderWidth: 0, label: { content: 'ANXIETY 😨', display: true, color: '#f87171', font: { size: 14, weight: 'bold' } } },
        box2: { type: 'box', xMin: 50, xMax: 100, yMin: 1.5, yMax: 3.5, backgroundColor: 'rgba(16, 185, 129, 0.2)', borderWidth: 0, label: { content: 'FLOW 🤩', display: true, color: '#34d399', font: { size: 14, weight: 'bold' } } },
        box3: { type: 'box', xMin: 0, xMax: 50, yMin: 0, yMax: 1.5, backgroundColor: 'rgba(56, 189, 248, 0.2)', borderWidth: 0, label: { content: 'RECOVERY 😌', display: true, color: '#7dd3fc', font: { size: 14, weight: 'bold' } } },
        box4: { type: 'box', xMin: 50, xMax: 100, yMin: 0, yMax: 1.5, backgroundColor: 'rgba(251, 191, 36, 0.2)', borderWidth: 0, label: { content: 'BOREDOM 🥱', display: true, color: '#fcd34d', font: { size: 14, weight: 'bold' } } }
    };

    chartFlow = new Chart(ctxF, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Greedy Trail',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: '#ef4444',
                    borderWidth: 2,
                    showLine: true, // Connect the dots to form a trail
                    tension: 0.4,   // Smooth curves (Cognitive Inertia)
                    pointRadius: 4
                },
                {
                    label: 'Bio-PKT Trail',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: '#10b981',
                    borderWidth: 2,
                    showLine: true,
                    tension: 0.4,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 0 }, // No internal animation, just step updates
            scales: {
                x: { min: 0, max: 100, title: { display: true, text: 'Energy (Resources)', color: '#94a3b8' }, grid: { color: '#334155' } },
                y: { min: 0, max: 3.5, title: { display: true, text: 'Difficulty (Challenge)', color: '#94a3b8' }, grid: { color: '#334155' } }
            },
            plugins: {
                legend: { labels: { color: '#e2e8f0' } },
                annotation: { annotations: boxAnnotations }
            }
        }
    });
}

function updateCharts() {
    if (chartEnergy) {
        chartEnergy.data.datasets[0].data = greedyAgent.logEnergy;
        chartEnergy.data.datasets[1].data = bioAgent.logEnergy;
        chartEnergy.update('none');
    }
    if (chartFlow) {
        // Current Agent Positions: {x: Energy, y: Difficulty}
        let gY = greedyAgent.currentNode ? K_GRAPH[greedyAgent.currentNode].level : 0;
        let bY = bioAgent.currentNode ? K_GRAPH[bioAgent.currentNode].level : 0;

        // Jitter to separate identical points
        if (Math.abs(greedyAgent.energy - bioAgent.energy) < 2 && gY === bY) {
            gY += 0.1;
        }

        // --- TRAIL LOGIC (COGNITIVE INERTIA) ---
        // Push new point
        let gData = chartFlow.data.datasets[0].data;
        let bData = chartFlow.data.datasets[1].data;

        gData.push({ x: greedyAgent.energy, y: gY });
        bData.push({ x: bioAgent.energy, y: bY });

        // Limit Trail Length (e.g., last 15 steps)
        const TRAIL_LENGTH = 15;
        if (gData.length > TRAIL_LENGTH) gData.shift();
        if (bData.length > TRAIL_LENGTH) bData.shift();

        chartFlow.update('none');
    }
}

// --- MAIN LOOP ---
function runLiveSimulation() {
    if (simulationInterval) clearInterval(simulationInterval);

    greedyAgent = new GraphAgent("Greedy", "GREEDY");
    bioAgent = new GraphAgent("Bio-PKT", "BIO");

    greedyData = initVisNetwork('network-greedy');
    bioData = initVisNetwork('network-bio');
    initCharts();

    document.getElementById('console-log').innerHTML = '';

    simulationInterval = setInterval(() => {
        let resG = greedyAgent.step();
        let resB = bioAgent.step();

        greedyAgent.logHistory();
        bioAgent.logHistory();

        updateAgentVis(greedyAgent, greedyData);
        updateAgentVis(bioAgent, bioData);
        updateCharts();

        // Update UI Stats & Emotions
        updateUI(greedyAgent, 'Greedy');
        updateUI(bioAgent, 'Bio');

        // Log significant events
        if (Math.random() > 0.7 || resG.switch || resB.switch || resG.action === 'REST') {
            logToConsole('Greedy', resG);
            logToConsole('Bio-PKT', resB);
        }

        // Stop Condition
        if (bioAgent.getAverageMastery() >= 100) clearInterval(simulationInterval);

    }, SIM_SPEED);
}

function updateUI(agent, prefix) {
    document.getElementById(`score${prefix}`).innerText = agent.getAverageMastery();
    document.getElementById(`statusText${prefix}`).innerText = agent.statusMsg;
    document.getElementById(`emo${prefix}`).innerText = agent.emoji;
    document.getElementById(`label${prefix}`).innerText = agent.emotion;

    // Overlay Text
    document.getElementById(`overlay-${prefix.toLowerCase()}`).innerText = `E: ${Math.round(agent.energy)}%`;
}

function updateSpeed(val) {
    SIM_SPEED = 510 - val;
    document.getElementById('valSpeed').innerText = SIM_SPEED + "ms";
    if (simulationInterval) { clearInterval(simulationInterval); runLiveSimulation(); }
}

function switchTab(tab) {
    document.getElementById('tab-graph').style.display = tab === 'graph' ? 'flex' : 'none';
    document.getElementById('tab-flow').style.display = tab === 'flow' ? 'flex' : 'none';
    document.getElementById('tab-energy').style.display = tab === 'energy' ? 'block' : 'none';

    // Resize chart if switching to flow
    if (tab === 'flow' && chartFlow) {
        chartFlow.resize();
    }
}

window.onload = runLiveSimulation;
