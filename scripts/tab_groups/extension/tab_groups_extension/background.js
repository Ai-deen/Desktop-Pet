// background.js — FINAL WITH PC AUTOSAVE + RESTORE
const CONTROL_SERVER = "http://127.0.0.1:5050";
const POLL_INTERVAL_MS = 1500;
let lastCmdId = null;

// Utilities
const tabsQuery = (q) => new Promise(r => chrome.tabs.query(q, r));
const tabsCreate = (p) => new Promise(r => chrome.tabs.create(p, r));
const tabsRemove = (ids) => new Promise(r => chrome.tabs.remove(ids, () => r(true)));
const tabsGroup = (p) => new Promise(r => chrome.tabs.group(p, r));
const tabGroupsUpdate = (id, p) => new Promise(r => chrome.tabGroups.update(id, p, r));
const storageGet = (k) => new Promise(r => chrome.storage.local.get(k, r));
const storageSet = (o) => new Promise(r => chrome.storage.local.set(o, () => r(true)));


// ---------------------------------------------------------
// OPEN CHROME GROUP SAVED LOCALLY
// ---------------------------------------------------------
async function openGroupByName(groupName) {
  try {
    const st = await storageGet(["tab_groups"]);
    const groups = st.tab_groups || {};
    const savedUrls = groups[groupName] || [];

    const newWin = await chrome.windows.create({
      url: "about:blank",
      focused: true
    });

    const newWindowId = newWin.id;
    const openedTabIds = [];

    for (const url of savedUrls) {
      const t = await tabsCreate({
        url,
        active: false,
        windowId: newWindowId
      });
      openedTabIds.push(t.id);
    }

    const placeholder = newWin.tabs[0];
    if (placeholder && placeholder.url === "about:blank") {
      await tabsRemove(placeholder.id);
    }

    if (openedTabIds.length > 0) {
      const groupId = await tabsGroup({ tabIds: openedTabIds });
      await tabGroupsUpdate(groupId, { title: groupName });
      chrome.tabs.update(openedTabIds[0], { active: true });
    }

    return { ok: true };
  } catch (e) {
    console.warn("openGroupByName error", e);
    return { ok: false, error: String(e) };
  }
}


// ---------------------------------------------------------
// PC → OPEN LINKS SENT BY CONTROL SERVER
// ---------------------------------------------------------
async function openLinksFromPC(groupName, urls) {
  try {
    const newWin = await chrome.windows.create({
      url: "about:blank",
      focused: true
    });

    const opened = [];

    for (const u of urls) {
      const t = await tabsCreate({ url: u, active: false, windowId: newWin.id });
      opened.push(t.id);
    }

    const placeholder = newWin.tabs[0];
    if (placeholder.url === "about:blank") {
      await tabsRemove(placeholder.id);
    }

    if (opened.length > 0) {
      const groupId = await tabsGroup({ tabIds: opened });
      await tabGroupsUpdate(groupId, { title: groupName });
    }

    return { ok: true };
  } catch (e) {
    console.warn("openLinksFromPC error", e);
    return { ok: false, error: String(e) };
  }
}


// ---------------------------------------------------------
// AUTO-SAVE TABS → SEND TO PC
// ---------------------------------------------------------
async function autoSaveToPC(groupName) {
  try {
    const tabs = await tabsQuery({});
    const urls = tabs.map(t => t.url).filter(Boolean);

    await fetch(`${CONTROL_SERVER}/save_urls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        group_name: groupName,
        urls: urls
      })
    });

    return { ok: true };
  } catch (e) {
    console.warn("autoSaveToPC error", e);
    return { ok: false, error: String(e) };
  }
}


// ---------------------------------------------------------
// SAVE CURRENT WINDOW LOCALLY
// ---------------------------------------------------------
async function saveCurrentWindowAsGroup(taskName) {
  try {
    const tabs = await tabsQuery({ currentWindow: true });
    const urls = tabs.map(t => t.url).filter(Boolean);

    const st = await storageGet(["tab_groups"]);
    const groups = st.tab_groups || {};
    groups[taskName] = urls;

    await storageSet({ tab_groups: groups });

    return { ok: true };
  } catch (e) {
    console.warn("saveCurrentWindowAsGroup error", e);
    return { ok: false, error: String(e) };
  }
}


// ---------------------------------------------------------
// UPDATE GROUP LOCALLY
// ---------------------------------------------------------
async function updateGroup(groupName) {
  try {
    const tabs = await tabsQuery({ currentWindow: true });
    const urls = tabs.map(t => t.url).filter(Boolean);

    const st = await storageGet(["tab_groups"]);
    const groups = st.tab_groups || {};
    groups[groupName] = urls;

    await storageSet({ tab_groups: groups });

    return { ok: true };
  } catch (e) {
    console.warn("updateGroup error", e);
    return { ok: false, error: String(e) };
  }
}


// ---------------------------------------------------------
// COMMAND POLLING LOOP
// ---------------------------------------------------------
let busy = false;

async function pollLoop() {
  if (busy) return;
  busy = true;

  try {
    const res = await fetch(CONTROL_SERVER + "/command", { cache: "no-cache" });
    const j = await res.json();

    if (j && j.pending) {
      const cmd = j.pending;

      if (cmd.id !== lastCmdId) {
        lastCmdId = cmd.id;
        const action = cmd.action;
        const name = cmd.payload?.name;
        const urls = cmd.payload?.urls;

        let result = { ok: false };

        if (action === "open_group" && name) {
          result = await openGroupByName(name);
        }
        else if (action === "save_group" && name) {
          result = await saveCurrentWindowAsGroup(name);
        }
        else if (action === "update_group" && name) {
          result = await updateGroup(name);
        }
        else if (action === "auto_save" && name) {
          result = await autoSaveToPC(name);
        }
        else if (action === "open_saved_from_pc" && name && urls) {
          result = await openLinksFromPC(name, urls);
        }

        // ACK
        await fetch(CONTROL_SERVER + "/ack", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: cmd.id, result })
        });
      }
    }
  } catch (e) {
    // ignore server down errors
  } finally {
    busy = false;
  }
}

setInterval(pollLoop, POLL_INTERVAL_MS);
console.log("Background worker loaded!");
