/**
 * Mafia Game Manager - Frontend Controller
 * 
 * STRICT PRIVACY CONTRACT:
 * - This client script never handles or receives role information.
 * - All game statistics and summaries contain COUNTS ONLY.
 */

// Global state
let state = {
    players: [],            // List of {id, name, email, in_game}
    mafiaCount: 1,          // 1 or 2 set freely by host
    detectiveEnabled: true, // ON / OFF
    mafiaKnowEachOther: true,
    activeGameResults: []
};

// DOM Elements
const elements = {
    // Form
    addPlayerForm: document.getElementById('addPlayerForm'),
    playerName: document.getElementById('playerName'),
    playerEmail: document.getElementById('playerEmail'),
    btnAddPlayer: document.getElementById('btnAddPlayer'),

    // Settings
    mafiaCountInput: document.getElementById('mafiaCount'),
    toggleDetective: document.getElementById('toggleDetective'),
    toggleMafiaKnow: document.getElementById('toggleMafiaKnow'),
    btnAssignAndSend: document.getElementById('btnAssignAndSend'),
    btnNewGame: document.getElementById('btnNewGame'),

    // Live Summary
    activePlayerCountBadge: document.getElementById('activePlayerCountBadge'),
    liveSummaryText: document.getElementById('liveSummaryText'),
    validationWarning: document.getElementById('validationWarning'),
    validationWarningText: document.getElementById('validationWarningText'),

    // Roster Table & Filters
    playersTableBody: document.getElementById('playersTableBody'),
    emptyRow: document.getElementById('emptyRow'),
    totalRosterBadge: document.getElementById('totalRosterBadge'),
    rosterSearch: document.getElementById('rosterSearch'),
    activeInGameCount: document.getElementById('activeInGameCount'),
    inactiveCount: document.getElementById('inactiveCount'),
    btnSelectAll: document.getElementById('btnSelectAll'),
    btnDeselectAll: document.getElementById('btnDeselectAll'),

    // SMTP & Alerts
    smtpStatusBadge: document.getElementById('smtpStatusBadge'),
    smtpStatusText: document.getElementById('smtpStatusText'),
    alertBanner: document.getElementById('alertBanner'),
    alertMessage: document.getElementById('alertMessage'),
    alertClose: document.getElementById('alertClose'),

    // Modals
    confirmModal: document.getElementById('confirmModal'),
    confirmActiveCount: document.getElementById('confirmActiveCount'),
    confirmBreakdownText: document.getElementById('confirmBreakdownText'),
    confirmMafiaKnow: document.getElementById('confirmMafiaKnow'),
    btnConfirmSend: document.getElementById('btnConfirmSend'),

    deliveryModal: document.getElementById('deliveryModal'),
    deliveryStatusBanner: document.getElementById('deliveryStatusBanner'),
    deliverySpinner: document.getElementById('deliverySpinner'),
    deliveryBannerHeading: document.getElementById('deliveryBannerHeading'),
    deliveryBannerSubtext: document.getElementById('deliveryBannerSubtext'),
    deliveryTableBody: document.getElementById('deliveryTableBody'),
    btnRetryFailed: document.getElementById('btnRetryFailed'),

    // Timer Elements
    headerTimerText: document.getElementById('headerTimerText'),
    btnHeaderTimer: document.getElementById('btnHeaderTimer'),
    timerDisplay: document.getElementById('timerDisplay'),
    timerStatusPill: document.getElementById('timerStatusPill'),
    timerProgressBar: document.getElementById('timerProgressBar'),
    btnTimerStartPause: document.getElementById('btnTimerStartPause'),
    timerPlayIcon: document.getElementById('timerPlayIcon'),
    timerPlayText: document.getElementById('timerPlayText'),
    btnTimerReset: document.getElementById('btnTimerReset'),
    btnTimerSub10: document.getElementById('btnTimerSub10'),
    btnTimerAdd30: document.getElementById('btnTimerAdd30'),
    btnTimerAdd60: document.getElementById('btnTimerAdd60'),
    btnTimerSound: document.getElementById('btnTimerSound'),
    btnTimerExpand: document.getElementById('btnTimerExpand'),
    timerCustomInput: document.getElementById('timerCustomInput'),
    btnSetCustomTimer: document.getElementById('btnSetCustomTimer'),

    // Focus Timer Modal Elements
    focusTimerModal: document.getElementById('focusTimerModal'),
    focusTimerDisplay: document.getElementById('focusTimerDisplay'),
    focusTimerStatusPill: document.getElementById('focusTimerStatusPill'),
    focusTimerProgressBar: document.getElementById('focusTimerProgressBar'),
    btnFocusTimerStartPause: document.getElementById('btnFocusTimerStartPause'),
    focusTimerPlayIcon: document.getElementById('focusTimerPlayIcon'),
    focusTimerPlayText: document.getElementById('focusTimerPlayText'),
    btnFocusTimerReset: document.getElementById('btnFocusTimerReset'),
    btnFocusTimerSub10: document.getElementById('btnFocusTimerSub10'),
    btnFocusTimerAdd30: document.getElementById('btnFocusTimerAdd30'),

    toastContainer: document.getElementById('toastContainer')
};

// ==========================================================================
// Initialization
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    initTimer();
    loadPlayers();
    checkSmtpStatus();
});

function initEventListeners() {
    // Form submission
    elements.addPlayerForm.addEventListener('submit', handleAddPlayer);

    // Settings adjustments
    elements.mafiaCountInput.addEventListener('input', handleSettingsChange);
    elements.toggleDetective.addEventListener('change', handleSettingsChange);
    elements.toggleMafiaKnow.addEventListener('change', (e) => {
        state.mafiaKnowEachOther = e.target.checked;
    });

    // Roster buttons
    elements.btnSelectAll.addEventListener('click', () => toggleAllPlayers(true));
    elements.btnDeselectAll.addEventListener('click', () => toggleAllPlayers(false));
    elements.rosterSearch.addEventListener('input', filterRosterRows);

    // Game Actions
    elements.btnAssignAndSend.addEventListener('click', openConfirmModal);
    elements.btnConfirmSend.addEventListener('click', triggerAssignAndSend);
    elements.btnRetryFailed.addEventListener('click', triggerRetryFailed);
    elements.btnNewGame.addEventListener('click', handleNewGame);

    // Modal close buttons (data-close attribute)
    document.querySelectorAll('[data-close]').forEach(btn => {
        btn.addEventListener('click', () => {
            const modalId = btn.getAttribute('data-close');
            closeModal(modalId);
        });
    });

    // Alert Banner close
    elements.alertClose.addEventListener('click', () => {
        elements.alertBanner.classList.add('hidden');
    });
}

// ==========================================================================
// API Operations
// ==========================================================================

async function loadPlayers() {
    try {
        const res = await fetch('/api/players');
        const data = await res.json();
        if (data.success) {
            state.players = data.players;
            renderRosterTable();
            updateLiveSummary();
        }
    } catch (err) {
        showToast('Failed to load player roster.', 'error');
    }
}

async function handleAddPlayer(e) {
    e.preventDefault();
    const name = elements.playerName.value.trim();
    const email = elements.playerEmail.value.trim();

    if (!name || !email) {
        showToast('Please enter both name and email.', 'error');
        return;
    }

    elements.btnAddPlayer.disabled = true;

    try {
        const res = await fetch('/api/players', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email })
        });
        const data = await res.json();

        if (data.success) {
            state.players.push(data.player);
            // Sort roster alphabetically
            state.players.sort((a, b) => a.name.localeCompare(b.name));
            renderRosterTable();
            updateLiveSummary();
            elements.playerName.value = '';
            elements.playerEmail.value = '';
            elements.playerName.focus();
            showToast(`Added ${name} to roster!`, 'success');
        } else {
            showToast(data.error || 'Failed to add player.', 'error');
        }
    } catch (err) {
        showToast('Network error while adding player.', 'error');
    } finally {
        elements.btnAddPlayer.disabled = false;
    }
}

async function handleTogglePlayer(playerId, inGame) {
    try {
        const res = await fetch(`/api/players/${playerId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ in_game: inGame })
        });
        const data = await res.json();
        if (data.success) {
            const player = state.players.find(p => p.id === playerId);
            if (player) player.in_game = inGame;
            updateRosterStats();
            updateLiveSummary();
        } else {
            showToast(data.error || 'Failed to update player.', 'error');
            loadPlayers(); // Revert UI
        }
    } catch (err) {
        showToast('Failed to update player status.', 'error');
        loadPlayers();
    }
}

async function toggleAllPlayers(inGame) {
    try {
        const res = await fetch('/api/players/toggle-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ in_game: inGame })
        });
        const data = await res.json();
        if (data.success) {
            state.players.forEach(p => p.in_game = inGame);
            renderRosterTable();
            updateLiveSummary();
            showToast(inGame ? 'Included all players.' : 'Skipped all players.', 'info');
        }
    } catch (err) {
        showToast('Failed to toggle all players.', 'error');
    }
}

async function handleDeletePlayer(playerId, playerName) {
    if (!confirm(`Remove "${playerName}" from the saved roster?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/players/${playerId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            state.players = state.players.filter(p => p.id !== playerId);
            renderRosterTable();
            updateLiveSummary();
            showToast(`Removed ${playerName}.`, 'info');
        } else {
            showToast(data.error || 'Failed to delete player.', 'error');
        }
    } catch (err) {
        showToast('Failed to delete player.', 'error');
    }
}

async function checkSmtpStatus() {
    try {
        const res = await fetch('/api/smtp/status');
        const data = await res.json();

        elements.smtpStatusBadge.classList.remove('checking', 'connected', 'disconnected');

        if (data.configured) {
            elements.smtpStatusBadge.classList.add('connected');
            elements.smtpStatusText.textContent = `SMTP Ready (${data.sender_email})`;
            elements.alertBanner.classList.add('hidden');
        } else {
            elements.smtpStatusBadge.classList.add('disconnected');
            elements.smtpStatusText.textContent = 'SMTP Unconfigured';
            elements.alertMessage.textContent = 'Gmail credentials missing in .env! Open .env and set your GMAIL_ADDRESS and GMAIL_APP_PASSWORD before assigning roles.';
            elements.alertBanner.classList.remove('hidden');
        }
    } catch (err) {
        elements.smtpStatusBadge.classList.add('disconnected');
        elements.smtpStatusText.textContent = 'SMTP Status Unknown';
    }
}

// ==========================================================================
// Roster UI Rendering & Filtering
// ==========================================================================

function renderRosterTable() {
    elements.playersTableBody.innerHTML = '';

    if (state.players.length === 0) {
        elements.playersTableBody.appendChild(elements.emptyRow);
        elements.totalRosterBadge.textContent = '0 Total';
        updateRosterStats();
        return;
    }

    elements.totalRosterBadge.textContent = `${state.players.length} Total`;

    state.players.forEach(player => {
        const tr = document.createElement('tr');
        tr.dataset.playerId = player.id;
        tr.dataset.name = player.name.toLowerCase();
        tr.dataset.email = player.email.toLowerCase();

        // Name
        const tdName = document.createElement('td');
        tdName.className = 'player-name-cell';
        tdName.textContent = player.name;

        // Email
        const tdEmail = document.createElement('td');
        tdEmail.className = 'player-email-cell';
        tdEmail.textContent = player.email;

        // Toggle Switch
        const tdToggle = document.createElement('td');
        tdToggle.className = 'text-center';
        
        const labelSwitch = document.createElement('label');
        labelSwitch.className = 'switch';
        
        const inputCheck = document.createElement('input');
        inputCheck.type = 'checkbox';
        inputCheck.checked = player.in_game;
        inputCheck.addEventListener('change', (e) => {
            handleTogglePlayer(player.id, e.target.checked);
        });

        const spanSlider = document.createElement('span');
        spanSlider.className = 'slider';

        labelSwitch.appendChild(inputCheck);
        labelSwitch.appendChild(spanSlider);
        tdToggle.appendChild(labelSwitch);

        // Delete button
        const tdAction = document.createElement('td');
        tdAction.className = 'text-right';
        const btnDelete = document.createElement('button');
        btnDelete.className = 'btn btn-danger-outline';
        btnDelete.innerHTML = '🗑️ Delete';
        btnDelete.title = `Delete ${player.name}`;
        btnDelete.addEventListener('click', () => handleDeletePlayer(player.id, player.name));
        tdAction.appendChild(btnDelete);

        tr.appendChild(tdName);
        tr.appendChild(tdEmail);
        tr.appendChild(tdToggle);
        tr.appendChild(tdAction);

        elements.playersTableBody.appendChild(tr);
    });

    updateRosterStats();
}

function updateRosterStats() {
    const active = state.players.filter(p => p.in_game).length;
    const inactive = state.players.length - active;
    elements.activeInGameCount.textContent = active;
    elements.inactiveCount.textContent = inactive;
}

function filterRosterRows() {
    const term = elements.rosterSearch.value.trim().toLowerCase();
    const rows = elements.playersTableBody.querySelectorAll('tr[data-player-id]');
    
    rows.forEach(row => {
        const name = row.dataset.name || '';
        const email = row.dataset.email || '';
        if (name.includes(term) || email.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// ==========================================================================
// Settings & Live Calculations (Counts Only)
// ==========================================================================

function handleSettingsChange() {
    let mafiaVal = parseInt(elements.mafiaCountInput.value, 10);
    if (isNaN(mafiaVal) || mafiaVal < 1) {
        mafiaVal = 1;
    }
    state.mafiaCount = mafiaVal;
    state.detectiveEnabled = elements.toggleDetective.checked;
    updateLiveSummary();
}

function updateLiveSummary() {
    const activePlayers = state.players.filter(p => p.in_game);
    const totalActive = activePlayers.length;

    elements.activePlayerCountBadge.textContent = `${totalActive} Player${totalActive === 1 ? '' : 's'}`;

    const mafia = state.mafiaCount;
    const doctor = 1; // Always 1
    const detective = state.detectiveEnabled ? 1 : 0;
    const specialTotal = mafia + doctor + detective;
    const citizens = totalActive - specialTotal;

    // Render Pills
    elements.liveSummaryText.innerHTML = `
        <span class="role-pill pill-mafia">${mafia} Mafia</span>
        <span class="role-pill pill-doctor">${doctor} Doctor</span>
        ${detective > 0 ? `<span class="role-pill pill-detective">1 Detective</span>` : ''}
        <span class="role-pill pill-citizen">${Math.max(0, citizens)} Citizen${citizens === 1 ? '' : 's'}</span>
    `;

    // Validation checks
    let errorMessage = null;

    if (totalActive < 4) {
        errorMessage = `At least 4 active players are required (currently ${totalActive}).`;
    } else if (specialTotal > totalActive) {
        errorMessage = `Special roles (${specialTotal}) exceed active players (${totalActive}).`;
    }

    if (errorMessage) {
        elements.validationWarningText.textContent = errorMessage;
        elements.validationWarning.classList.remove('hidden');
        elements.btnAssignAndSend.disabled = true;
    } else {
        elements.validationWarning.classList.add('hidden');
        elements.btnAssignAndSend.disabled = false;
    }
}

// ==========================================================================
// Game Assignment & Email Dispatch
// ==========================================================================

function openConfirmModal() {
    const activeCount = state.players.filter(p => p.in_game).length;
    const mafia = state.mafiaCount;
    const doctor = 1;
    const detective = state.detectiveEnabled ? 1 : 0;
    const citizens = activeCount - (mafia + doctor + detective);

    elements.confirmActiveCount.textContent = `${activeCount} players`;
    elements.confirmBreakdownText.textContent = `${mafia} Mafia, ${doctor} Doctor, ${detective} Detective, ${citizens} Citizen(s)`;
    elements.confirmMafiaKnow.textContent = elements.toggleMafiaKnow.checked ? 'Enabled' : 'Disabled';

    openModal('confirmModal');
}

async function triggerAssignAndSend() {
    closeModal('confirmModal');
    openDeliveryModalInProgress();

    try {
        const res = await fetch('/api/game/assign-and-send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mafia_count: state.mafiaCount,
                detective_enabled: state.detectiveEnabled,
                mafia_know_each_other: elements.toggleMafiaKnow.checked
            })
        });

        const data = await res.json();

        if (!data.success && data.error) {
            renderDeliveryFailure(data.error);
            return;
        }

        renderDeliveryResults(data.results, data.summary);

    } catch (err) {
        renderDeliveryFailure('Network or server connection failed while sending emails.');
    }
}

async function triggerRetryFailed() {
    elements.btnRetryFailed.disabled = true;
    elements.deliveryStatusBanner.className = 'delivery-banner in-progress';
    elements.deliverySpinner.classList.remove('hidden');
    elements.deliveryBannerHeading.textContent = 'Retrying Failed Deliveries...';
    elements.deliveryBannerSubtext.textContent = 'Contacting Gmail SMTP to retry failed recipients.';

    try {
        const res = await fetch('/api/game/retry-failed', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            renderDeliveryResults(data.results, data.summary);
        } else {
            showToast(data.error || 'Retry failed.', 'error');
        }
    } catch (err) {
        showToast('Network error while retrying.', 'error');
    } finally {
        elements.btnRetryFailed.disabled = false;
    }
}

async function handleNewGame() {
    if (!confirm('Start a New Game? This will reset the previous role assignment from server memory. Your saved player roster will remain intact.')) {
        return;
    }

    try {
        const res = await fetch('/api/game/reset', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            closeModal('deliveryModal');
            showToast('New game ready. Previous assignment wiped.', 'success');
        }
    } catch (err) {
        showToast('Failed to reset game.', 'error');
    }
}

// ==========================================================================
// Delivery Modal Rendering (STRICT: NO ROLES DISPLAYED)
// ==========================================================================

function openDeliveryModalInProgress() {
    elements.deliveryTableBody.innerHTML = '';
    elements.deliveryStatusBanner.className = 'delivery-banner in-progress';
    elements.deliverySpinner.classList.remove('hidden');
    elements.deliveryBannerHeading.textContent = 'Sending Secret Role Emails...';
    elements.deliveryBannerSubtext.textContent = 'Delivering individual emails via Gmail SMTP with no delay.';
    elements.btnRetryFailed.classList.add('hidden');
    openModal('deliveryModal');
}

function renderDeliveryFailure(errorMessage) {
    elements.deliverySpinner.classList.add('hidden');
    elements.deliveryStatusBanner.className = 'delivery-banner has-errors';
    elements.deliveryBannerHeading.textContent = 'Email Dispatch Failed';
    elements.deliveryBannerSubtext.textContent = errorMessage;
}

function renderDeliveryResults(results, summary) {
    elements.deliverySpinner.classList.add('hidden');
    elements.deliveryTableBody.innerHTML = '';

    const hasFailures = summary.failed > 0;

    if (hasFailures) {
        elements.deliveryStatusBanner.className = 'delivery-banner has-errors';
        elements.deliveryBannerHeading.textContent = `Completed with ${summary.failed} Failed Delivery(s)`;
        elements.deliveryBannerSubtext.textContent = `${summary.sent} of ${summary.total} emails sent successfully. Check the errors below and retry.`;
        elements.btnRetryFailed.classList.remove('hidden');
    } else {
        elements.deliveryStatusBanner.className = 'delivery-banner success';
        elements.deliveryBannerHeading.textContent = 'All Role Emails Sent Successfully!';
        elements.deliveryBannerSubtext.textContent = `All ${summary.sent} players have received their secret roles.`;
        elements.btnRetryFailed.classList.add('hidden');
    }

    // Populate delivery table: ONLY Name, Email, Status badge, Details
    // STRICT: Never includes role!
    results.forEach(item => {
        const tr = document.createElement('tr');

        // Player Name
        const tdName = document.createElement('td');
        tdName.className = 'player-name-cell';
        tdName.textContent = item.name;

        // Player Email
        const tdEmail = document.createElement('td');
        tdEmail.className = 'player-email-cell';
        tdEmail.textContent = item.email;

        // Status Badge
        const tdStatus = document.createElement('td');
        tdStatus.className = 'text-center';
        const badge = document.createElement('span');
        badge.className = `badge ${item.status === 'sent' ? 'badge-sent' : 'badge-failed'}`;
        badge.textContent = item.status === 'sent' ? '✓ Sent' : '✗ Failed';
        tdStatus.appendChild(badge);

        // Error / Details
        const tdDetails = document.createElement('td');
        tdDetails.style.fontSize = '12px';
        if (item.status === 'sent') {
            tdDetails.style.color = '#6ee7b7';
            tdDetails.textContent = 'Delivered to recipient';
        } else {
            tdDetails.style.color = '#fca5a5';
            tdDetails.textContent = item.error || 'Delivery failed';
        }

        tr.appendChild(tdName);
        tr.appendChild(tdEmail);
        tr.appendChild(tdStatus);
        tr.appendChild(tdDetails);

        elements.deliveryTableBody.appendChild(tr);
    });
}

// ==========================================================================
// Modal & Toast Helpers
// ==========================================================================

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(8px)';
        setTimeout(() => toast.remove(), 250);
    }, 3500);
}

// ==========================================================================
// Discussion Timer / Stopwatch Implementation
// ==========================================================================

const DEFAULT_TIMER_SECONDS = 100; // Authoritative default (100 sec)

const timerState = {
    totalSeconds: DEFAULT_TIMER_SECONDS,      // Default 100 seconds as requested
    remainingSeconds: DEFAULT_TIMER_SECONDS,  // Counts down to 0
    isRunning: false,
    soundEnabled: true,
    intervalId: null
};

function initTimer() {
    // Start / Pause buttons
    elements.btnTimerStartPause.addEventListener('click', toggleTimer);
    elements.btnFocusTimerStartPause.addEventListener('click', toggleTimer);

    // Reset buttons
    elements.btnTimerReset.addEventListener('click', resetTimer);
    elements.btnFocusTimerReset.addEventListener('click', resetTimer);

    // Quick Adjusters
    elements.btnTimerSub10.addEventListener('click', () => adjustTimerSeconds(-10));
    elements.btnTimerAdd30.addEventListener('click', () => adjustTimerSeconds(30));
    elements.btnTimerAdd60.addEventListener('click', () => adjustTimerSeconds(60));
    elements.btnFocusTimerSub10.addEventListener('click', () => adjustTimerSeconds(-10));
    elements.btnFocusTimerAdd30.addEventListener('click', () => adjustTimerSeconds(30));

    // Preset buttons
    document.querySelectorAll('.btn-preset').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const sec = parseInt(e.target.dataset.seconds, 10);
            if (!isNaN(sec) && sec > 0) {
                setTimerTotalDuration(sec);
            }
        });
    });

    // Custom input Set button
    elements.btnSetCustomTimer.addEventListener('click', () => {
        const sec = parseInt(elements.timerCustomInput.value, 10);
        if (!isNaN(sec) && sec >= 5 && sec <= 999) {
            setTimerTotalDuration(sec);
            showToast(`Discussion timer set to ${sec} seconds.`, 'info');
        } else {
            showToast('Please enter a duration between 5 and 999 seconds.', 'error');
        }
    });

    // Header shortcut to open Focus timer
    elements.btnHeaderTimer.addEventListener('click', () => {
        openModal('focusTimerModal');
    });

    // Expand button on timer card
    elements.btnTimerExpand.addEventListener('click', () => {
        openModal('focusTimerModal');
    });

    // Sound toggle button
    elements.btnTimerSound.addEventListener('click', toggleTimerSound);

    // Keyboard shortcuts (Space to toggle, R to reset when focus modal is open)
    document.addEventListener('keydown', (e) => {
        if (!elements.focusTimerModal.classList.contains('hidden')) {
            if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
                e.preventDefault();
                toggleTimer();
            } else if ((e.key === 'r' || e.key === 'R') && e.target.tagName !== 'INPUT') {
                e.preventDefault();
                resetTimer();
            }
        }
    });

    // Initial render
    updateTimerDisplay();
}

function toggleTimer() {
    if (timerState.isRunning) {
        pauseTimer();
    } else {
        startTimer();
    }
}

function startTimer() {
    if (timerState.remainingSeconds <= 0) {
        timerState.remainingSeconds = timerState.totalSeconds;
    }

    timerState.isRunning = true;
    updateTimerControlsUI();

    if (timerState.intervalId) {
        clearInterval(timerState.intervalId);
    }

    timerState.intervalId = setInterval(() => {
        if (timerState.remainingSeconds > 0) {
            timerState.remainingSeconds--;
            updateTimerDisplay();

            if (timerState.remainingSeconds === 0) {
                handleTimerFinished();
            }
        }
    }, 1000);

    updateTimerDisplay();
}

function pauseTimer() {
    timerState.isRunning = false;
    if (timerState.intervalId) {
        clearInterval(timerState.intervalId);
        timerState.intervalId = null;
    }
    updateTimerControlsUI();
    updateTimerDisplay();
}

function resetTimer() {
    pauseTimer();
    // Strictly reset back to default 100 seconds
    timerState.totalSeconds = DEFAULT_TIMER_SECONDS;
    timerState.remainingSeconds = DEFAULT_TIMER_SECONDS;

    if (elements.timerCustomInput) {
        elements.timerCustomInput.value = DEFAULT_TIMER_SECONDS;
    }

    // Set 100s preset button active
    document.querySelectorAll('.btn-preset').forEach(btn => {
        const btnSec = parseInt(btn.dataset.seconds, 10);
        if (btnSec === DEFAULT_TIMER_SECONDS) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    updateTimerDisplay();
}

function adjustTimerSeconds(delta) {
    timerState.remainingSeconds = Math.max(0, timerState.remainingSeconds + delta);
    if (timerState.remainingSeconds > timerState.totalSeconds) {
        timerState.totalSeconds = timerState.remainingSeconds;
    }
    updateTimerDisplay();
}

function setTimerTotalDuration(seconds) {
    pauseTimer();
    timerState.totalSeconds = seconds;
    timerState.remainingSeconds = seconds;
    elements.timerCustomInput.value = seconds;

    // Update active preset button highlight
    document.querySelectorAll('.btn-preset').forEach(btn => {
        const btnSec = parseInt(btn.dataset.seconds, 10);
        if (btnSec === seconds) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    updateTimerDisplay();
}

function handleTimerFinished() {
    pauseTimer();
    updateTimerDisplay();

    if (timerState.soundEnabled) {
        playTimerAlertSound();
    }

    showToast("⏰ Time's up! Discussion phase has concluded. Proceed to voting!", 'warning');
}

function toggleTimerSound() {
    timerState.soundEnabled = !timerState.soundEnabled;
    elements.btnTimerSound.textContent = timerState.soundEnabled ? '🔊' : '🔇';
    elements.btnTimerSound.title = timerState.soundEnabled ? 'Sound alert enabled' : 'Sound alert muted';
    showToast(timerState.soundEnabled ? 'Timer sound enabled.' : 'Timer sound muted.', 'info');
}

function formatTime(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function updateTimerDisplay() {
    const timeFormatted = formatTime(timerState.remainingSeconds);
    const pct = timerState.totalSeconds > 0 
        ? Math.max(0, Math.min(100, (timerState.remainingSeconds / timerState.totalSeconds) * 100))
        : 0;

    // Display Texts
    elements.timerDisplay.textContent = timeFormatted;
    elements.headerTimerText.textContent = timeFormatted;
    elements.focusTimerDisplay.textContent = timeFormatted;

    // Progress Bars
    elements.timerProgressBar.style.width = `${pct}%`;
    elements.focusTimerProgressBar.style.width = `${pct}%`;

    // Warning and Danger styles
    const isFinished = timerState.remainingSeconds === 0;
    const isDanger = timerState.remainingSeconds > 0 && timerState.remainingSeconds <= 10;
    const isWarning = timerState.remainingSeconds > 10 && timerState.remainingSeconds <= 30;

    // Progress bar classes
    elements.timerProgressBar.classList.remove('warning', 'danger');
    elements.focusTimerProgressBar.classList.remove('warning', 'danger');
    elements.focusTimerDisplay.classList.remove('warning', 'danger');

    if (isDanger) {
        elements.timerProgressBar.classList.add('danger');
        elements.focusTimerProgressBar.classList.add('danger');
        elements.focusTimerDisplay.classList.add('danger');
    } else if (isWarning) {
        elements.timerProgressBar.classList.add('warning');
        elements.focusTimerProgressBar.classList.add('warning');
        elements.focusTimerDisplay.classList.add('warning');
    }

    // Status Pill
    const pillClass = isFinished 
        ? 'finished' 
        : (timerState.isRunning ? 'running' : (timerState.remainingSeconds < timerState.totalSeconds ? 'paused' : 'ready'));

    const pillText = isFinished
        ? "Time's Up!"
        : (timerState.isRunning ? "Discussing..." : (timerState.remainingSeconds < timerState.totalSeconds ? "Paused" : "Ready"));

    [elements.timerStatusPill, elements.focusTimerStatusPill].forEach(pill => {
        pill.className = `timer-status-pill ${pillClass}`;
        pill.textContent = pillText;
    });

    updateTimerControlsUI();
}

function updateTimerControlsUI() {
    const playIcon = timerState.isRunning ? '⏸' : '▶';
    const playText = timerState.isRunning ? 'Pause' : (timerState.remainingSeconds < timerState.totalSeconds && timerState.remainingSeconds > 0 ? 'Resume' : 'Start');

    elements.timerPlayIcon.textContent = playIcon;
    elements.timerPlayText.textContent = playText;
    elements.focusTimerPlayIcon.textContent = playIcon;
    elements.focusTimerPlayText.textContent = playText;
}

/**
 * Play a synthesized dual-tone chime using Web Audio API (completely offline)
 */
function playTimerAlertSound() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();

        const playChime = (freq, startTime, duration) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);

            gain.gain.setValueAtTime(0.25, ctx.currentTime + startTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startTime + duration);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(ctx.currentTime + startTime);
            osc.stop(ctx.currentTime + startTime + duration);
        };

        // Pleasant three-note alert: F5 -> A5 -> C6
        playChime(698.46, 0.0, 0.35);  // F5
        playChime(880.00, 0.2, 0.40);  // A5
        playChime(1046.50, 0.45, 0.70); // C6

    } catch (err) {
        console.warn('Audio alert could not be played:', err);
    }
}
