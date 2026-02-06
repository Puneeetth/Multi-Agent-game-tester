/**
 * Multi-Agent Game Tester - Frontend Application
 */

const API_BASE = '';  // Same origin

// State
let state = {
    sessionId: null,
    gameAnalysis: null,
    testCases: [],
    rankedTests: [],
    executionResults: [],
    report: null,
    currentStep: null
};

// DOM Elements
const elements = {
    gameUrl: document.getElementById('gameUrl'),
    analyzeBtn: document.getElementById('analyzeBtn'),
    generateBtn: document.getElementById('generateBtn'),
    rankBtn: document.getElementById('rankBtn'),
    executeBtn: document.getElementById('executeBtn'),
    downloadReportBtn: document.getElementById('downloadReportBtn'),
    
    systemStatus: document.getElementById('systemStatus'),
    progressSection: document.getElementById('progressSection'),
    progressFill: document.getElementById('progressFill'),
    progressMessage: document.getElementById('progressMessage'),
    
    analysisCard: document.getElementById('analysisCard'),
    gameAnalysis: document.getElementById('gameAnalysis'),
    testsCard: document.getElementById('testsCard'),
    testCount: document.getElementById('testCount'),
    testsList: document.getElementById('testsList'),
    
    reportSection: document.getElementById('reportSection'),
    summaryGrid: document.getElementById('summaryGrid'),
    resultsTable: document.getElementById('resultsTable'),
    triageNotes: document.getElementById('triageNotes'),
    recommendations: document.getElementById('recommendations'),
    
    artifactsSection: document.getElementById('artifactsSection'),
    artifactsList: document.getElementById('artifactsList')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    elements.analyzeBtn.addEventListener('click', analyzeGame);
    elements.generateBtn.addEventListener('click', generateTests);
    elements.rankBtn.addEventListener('click', rankTests);
    elements.executeBtn.addEventListener('click', executeTests);
    elements.downloadReportBtn.addEventListener('click', downloadReport);
});

// API Helpers
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'API call failed');
    }
    
    return response.json();
}

// Update Progress
function updateProgress(step, message, percent) {
    elements.progressSection.style.display = 'block';
    elements.progressMessage.textContent = message;
    elements.progressFill.style.width = `${percent}%`;
    
    // Update step indicators
    const steps = ['analyze', 'generate', 'rank', 'execute', 'report'];
    const stepIndex = steps.indexOf(step);
    
    document.querySelectorAll('.progress-step').forEach((el, idx) => {
        el.classList.remove('active', 'complete');
        if (idx < stepIndex) {
            el.classList.add('complete');
        } else if (idx === stepIndex) {
            el.classList.add('active');
        }
    });
    
    state.currentStep = step;
}

// Set System Status
function setStatus(status, text) {
    elements.systemStatus.className = `status-badge ${status}`;
    elements.systemStatus.querySelector('span:last-child').textContent = text;
}

// Analyze Game
async function analyzeGame() {
    const url = elements.gameUrl.value.trim();
    
    if (!url) {
        alert('Please enter a game URL');
        return;
    }
    
    try {
        setStatus('busy', 'Analyzing...');
        updateProgress('analyze', 'Analyzing game mechanics...', 10);
        
        elements.analyzeBtn.disabled = true;
        elements.analyzeBtn.innerHTML = '<span class="loading"></span> Analyzing...';
        
        const result = await apiCall('/api/analyze-game', 'POST', { url });
        
        state.sessionId = result.session_id;
        
        // Fetch full session data
        const session = await apiCall(`/api/session/${state.sessionId}`);
        state.gameAnalysis = session.game_analysis;
        
        // Display analysis
        displayGameAnalysis(state.gameAnalysis);
        
        updateProgress('analyze', 'Game analyzed successfully!', 20);
        setStatus('', 'Ready');
        
        // Enable next step
        elements.generateBtn.disabled = false;
        
    } catch (error) {
        console.error('Analysis error:', error);
        setStatus('error', 'Error');
        alert(`Analysis failed: ${error.message}`);
    } finally {
        elements.analyzeBtn.disabled = false;
        elements.analyzeBtn.innerHTML = '<span class="btn-icon">🔍</span> Analyze Game';
    }
}

// Display Game Analysis
function displayGameAnalysis(analysis) {
    elements.analysisCard.style.display = 'block';
    
    const mechanics = analysis.mechanics || [];
    
    elements.gameAnalysis.innerHTML = `
        <div class="analysis-item">
            <span class="label">Game Type</span>
            <span class="value">${analysis.game_type || 'Unknown'}</span>
        </div>
        <div class="analysis-item">
            <span class="label">URL</span>
            <span class="value">${analysis.url || 'N/A'}</span>
        </div>
        <div class="analysis-item">
            <span class="label">Elements</span>
            <span class="value">${analysis.element_count || 0} interactive elements found</span>
        </div>
        <div class="analysis-item">
            <span class="label">Mechanics</span>
            <span class="value">${mechanics.length > 0 ? mechanics.join(', ') : 'Detecting...'}</span>
        </div>
        <div class="analysis-item">
            <span class="label">UI</span>
            <span class="value">${(analysis.ui_description || 'N/A').substring(0, 150)}...</span>
        </div>
    `;
    
    elements.testsCard.style.display = 'block';
}

// Generate Tests
async function generateTests() {
    if (!state.sessionId) {
        alert('Please analyze a game first');
        return;
    }
    
    try {
        setStatus('busy', 'Generating...');
        updateProgress('generate', 'Generating 20+ test cases...', 30);
        
        elements.generateBtn.disabled = true;
        elements.generateBtn.innerHTML = '<span class="loading"></span> Generating...';
        
        const result = await apiCall('/api/generate-tests', 'POST', {
            session_id: state.sessionId
        });
        
        state.testCases = result.test_cases;
        displayTestCases(state.testCases, false);
        
        updateProgress('generate', `Generated ${state.testCases.length} test cases!`, 50);
        setStatus('', 'Ready');
        
        // Enable next step
        elements.rankBtn.disabled = false;
        
    } catch (error) {
        console.error('Generation error:', error);
        setStatus('error', 'Error');
        alert(`Test generation failed: ${error.message}`);
    } finally {
        elements.generateBtn.disabled = false;
        elements.generateBtn.innerHTML = 'Generate Tests';
    }
}

// Display Test Cases
function displayTestCases(tests, ranked = false) {
    elements.testCount.textContent = tests.length;
    
    elements.testsList.innerHTML = tests.map(test => `
        <div class="test-item ${ranked ? 'ranked' : ''}">
            <div class="test-header">
                <span class="test-name">#${test.id} - ${test.name}</span>
                <div class="test-meta">
                    <span class="test-tag ${test.priority}">${test.priority}</span>
                    <span class="test-tag">${test.category}</span>
                </div>
            </div>
            <p class="test-description">${test.description || 'No description'}</p>
            ${ranked && test.overall_score !== undefined ? `
                <p class="test-score">Score: ${test.overall_score.toFixed(2)} | ${test.ranking_reason || ''}</p>
            ` : ''}
        </div>
    `).join('');
}

// Rank Tests
async function rankTests() {
    if (!state.testCases.length) {
        alert('Please generate tests first');
        return;
    }
    
    try {
        setStatus('busy', 'Ranking...');
        updateProgress('rank', 'Ranking and selecting top 10...', 60);
        
        elements.rankBtn.disabled = true;
        elements.rankBtn.innerHTML = '<span class="loading"></span> Ranking...';
        
        const result = await apiCall('/api/rank-tests', 'POST', {
            session_id: state.sessionId
        });
        
        state.rankedTests = result.ranked_tests;
        displayTestCases(state.rankedTests, true);
        
        updateProgress('rank', `Selected top ${state.rankedTests.length} tests!`, 70);
        setStatus('', 'Ready');
        
        // Enable next step
        elements.executeBtn.disabled = false;
        
    } catch (error) {
        console.error('Ranking error:', error);
        setStatus('error', 'Error');
        alert(`Test ranking failed: ${error.message}`);
    } finally {
        elements.rankBtn.disabled = false;
        elements.rankBtn.innerHTML = 'Rank & Select Top 10';
    }
}

// Execute Tests
async function executeTests() {
    if (!state.rankedTests.length) {
        alert('Please rank tests first');
        return;
    }
    
    try {
        setStatus('busy', 'Executing...');
        updateProgress('execute', 'Executing tests with validation...', 75);
        
        elements.executeBtn.disabled = true;
        elements.executeBtn.innerHTML = '<span class="loading"></span> Executing...';
        
        const result = await apiCall('/api/execute-tests', 'POST', {
            session_id: state.sessionId
        });
        
        state.executionResults = result.results;
        
        updateProgress('execute', 'Tests executed! Generating report...', 90);
        
        // Get report
        await getReport();
        
    } catch (error) {
        console.error('Execution error:', error);
        setStatus('error', 'Error');
        alert(`Test execution failed: ${error.message}`);
    } finally {
        elements.executeBtn.disabled = false;
        elements.executeBtn.innerHTML = 'Execute Tests';
    }
}

// Get Report
async function getReport() {
    try {
        updateProgress('report', 'Generating comprehensive report...', 95);
        
        const report = await apiCall(`/api/report/${state.sessionId}`);
        state.report = report;
        
        displayReport(report);
        
        // Get artifacts
        const artifacts = await apiCall(`/api/artifacts/${state.sessionId}`);
        displayArtifacts(artifacts.artifacts);
        
        updateProgress('report', 'Complete!', 100);
        setStatus('', 'Complete');
        
        // Mark all steps complete
        document.querySelectorAll('.progress-step').forEach(el => {
            el.classList.remove('active');
            el.classList.add('complete');
        });
        
    } catch (error) {
        console.error('Report error:', error);
        setStatus('error', 'Error');
    }
}

// Display Report
function displayReport(report) {
    elements.reportSection.style.display = 'block';
    
    const summary = report.summary;
    
    // Summary Grid
    elements.summaryGrid.innerHTML = `
        <div class="summary-card">
            <div class="value">${summary.total_tests}</div>
            <div class="label">Total Tests</div>
        </div>
        <div class="summary-card success">
            <div class="value">${summary.passed}</div>
            <div class="label">Passed</div>
        </div>
        <div class="summary-card error">
            <div class="value">${summary.failed}</div>
            <div class="label">Failed</div>
        </div>
        <div class="summary-card warning">
            <div class="value">${summary.flaky}</div>
            <div class="label">Flaky</div>
        </div>
        <div class="summary-card info">
            <div class="value">${summary.pass_rate}%</div>
            <div class="label">Pass Rate</div>
        </div>
        <div class="summary-card ${getStatusClass(summary.overall_status)}">
            <div class="value">${summary.overall_status}</div>
            <div class="label">Status</div>
        </div>
    `;
    
    // Results Table
    const tbody = elements.resultsTable.querySelector('tbody');
    tbody.innerHTML = report.test_results.map(result => `
        <tr>
            <td>${result.test_name}</td>
            <td>
                <span class="verdict-badge ${(result.verdict?.result || 'unknown').toLowerCase()}">
                    ${result.verdict?.result || 'UNKNOWN'}
                </span>
            </td>
            <td>${result.verdict?.confidence || 0}%</td>
            <td>${result.reproducibility}%</td>
            <td>${result.run_count}</td>
        </tr>
    `).join('');
    
    // Triage Notes
    if (report.triage_notes && report.triage_notes.length > 0) {
        elements.triageNotes.innerHTML = `
            <h3>🔧 Triage Notes</h3>
            ${report.triage_notes.map(note => `
                <div class="triage-item ${note.severity.toLowerCase()}">
                    <div class="triage-header">
                        <span class="triage-test">${note.test_name}</span>
                        <span class="triage-severity ${note.severity.toLowerCase()}">${note.severity}</span>
                    </div>
                    <p class="triage-action">${note.recommended_action}</p>
                </div>
            `).join('')}
        `;
    }
    
    // Recommendations
    if (report.recommendations && report.recommendations.length > 0) {
        elements.recommendations.innerHTML = `
            <h3>💡 Recommendations</h3>
            <ul>
                ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        `;
    }
}

// Display Artifacts
function displayArtifacts(artifacts) {
    if (!artifacts || artifacts.length === 0) {
        return;
    }
    
    elements.artifactsSection.style.display = 'block';
    
    elements.artifactsList.innerHTML = artifacts.map(artifact => `
        <div class="artifact-item" onclick="viewArtifact('${artifact.path}')">
            <div class="artifact-icon">${getArtifactIcon(artifact.type)}</div>
            <div class="artifact-name">${artifact.name}</div>
        </div>
    `).join('');
}

// View Artifact
function viewArtifact(path) {
    window.open(`${API_BASE}/api/artifacts/${path}`, '_blank');
}

// Download Report
function downloadReport() {
    if (!state.report) {
        alert('No report available');
        return;
    }
    
    const blob = new Blob([JSON.stringify(state.report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test_report_${state.sessionId}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Helper Functions
function getStatusClass(status) {
    const classes = {
        'HEALTHY': 'success',
        'MODERATE': 'warning',
        'CONCERNING': 'warning',
        'CRITICAL': 'error'
    };
    return classes[status] || 'info';
}

function getArtifactIcon(type) {
    const icons = {
        'png': '📸',
        'html': '📄',
        'json': '📋',
        'default': '📁'
    };
    return icons[type] || icons.default;
}
