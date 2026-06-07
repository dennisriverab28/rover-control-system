// === Send Movement Commands ===
async function sendCommand(cmd) {
    try {
        await fetch('/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd }),
            keepalive: true
        });
        const statusText = document.getElementById("status");
        statusText.innerText = "Sent: " + cmd;
        statusText.style.color = (cmd === "stop" || cmd === "S") ? "#ff4444" : "#00ff88";
    } catch (err) {
        console.error("Error sending command:", err);
    }
}

// === Bind Movement Buttons ===
window.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        const cmd = btn.dataset.cmd;

        // Mouse
        btn.addEventListener('mousedown', () => sendCommand(cmd));
        btn.addEventListener('mouseup', () => sendCommand('stop'));
        btn.addEventListener('mouseleave', () => sendCommand('stop'));

        // Touch
        btn.addEventListener('touchstart', e => {
            e.preventDefault();
            sendCommand(cmd);
        });
        btn.addEventListener('touchend', e => {
            e.preventDefault();
            sendCommand('stop');
        });
    });

    // Keyboard
    document.addEventListener('keydown', e => {
        const map = { ArrowUp:'forward', ArrowDown:'backward', ArrowLeft:'left', ArrowRight:'right' };
        if (map[e.key]) sendCommand(map[e.key]);
    });
    document.addEventListener('keyup', e => {
        if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)) sendCommand('stop');
    });

    // System Buttons
    document.getElementById('statusBtn').addEventListener('click', getStatus);
});

// === Get System Status ===
async function getStatus() {
    const list = document.getElementById('statusList');
    list.innerHTML = "<li>Loading...</li>";
    try {
        const res = await fetch('/status');
        const data = await res.json();
        list.innerHTML = "";
        for (const [key, value] of Object.entries(data)) {
            const li = document.createElement("li");
            li.textContent = `${key}: ${value}`;
            list.appendChild(li);
        }
    } catch (err) {
        list.innerHTML = `<li style="color:#ff4444">Error fetching status</li>`;
    }
}

// === Reboot Pi ===
async function rebootPi() {
    if (confirm("Reboot Raspberry Pi?")) {
        await fetch('/reboot', { method: 'POST' });
        alert("Rebooting... connection will drop briefly.");
    }
}

// === Shutdown Pi ===
async function shutdownSystem() {
    if (confirm("⚠️ Shutdown Raspberry Pi?")) {
        await fetch('/shutdown', { method: 'POST' });
        alert("Shutting down. You will lose connection shortly.");
    }
}
// === GPS Ping ===
async function pingLocation() {
    const gpsBox = document.getElementById('gpsData');
    gpsBox.textContent = "Pinging...";
    try {
        const res = await fetch('/ping');
        const data = await res.json();
        const g = data.gps_data;
        gpsBox.textContent =
`Fix: ${g.fix}
Lat: ${g.latitude}
Lon: ${g.longitude}
Alt: ${g.altitude}
Satellites: ${g.satellites}`;
    } catch (err) {
        gpsBox.textContent = "Error: Unable to fetch GPS data.";
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const pingBtn = document.getElementById('pingBtn');
    if (pingBtn) pingBtn.addEventListener('click', pingLocation);
});
