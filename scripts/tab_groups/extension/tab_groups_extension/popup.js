const SERVER = "http://127.0.0.1:5050";

const groupList = document.getElementById("groupList");
const statusBox = document.getElementById("status");

// Load saved groups from chrome storage
async function loadGroups() {
  chrome.storage.local.get(["tab_groups"], res => {
    groupList.innerHTML = "";
    const groups = res.tab_groups || {};

    for (const name of Object.keys(groups)) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      groupList.appendChild(opt);
    }

    if (!Object.keys(groups).length) {
      const opt = document.createElement("option");
      opt.textContent = "(no saved groups yet)";
      groupList.appendChild(opt);
    }
  });
}

loadGroups();


async function sendCommand(action, name) {
  try {
    const res = await fetch(SERVER + "/set_command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        payload: { name }
      })
    });

    const j = await res.json();
    statusBox.textContent = "Sent command: " + JSON.stringify(j);
  } catch (e) {
    statusBox.textContent = "Server offline / error sending command.";
  }
}

// OPEN group
document.getElementById("openBtn").onclick = () => {
  const name = groupList.value;
  if (!name || name.includes("no saved")) return;

  sendCommand("open_group", name);
};

// SAVE group
document.getElementById("saveBtn").onclick = () => {
  const name = document.getElementById("taskName").value.trim();
  if (!name) {
    statusBox.textContent = "Enter a name!";
    return;
  }
  sendCommand("save_group", name);
};
