// background.js (module)
// Poll-control extension that syncs tab-groups and responds to local server commands.
// Key: stores groups under chrome.storage.local.tab_groups

const CONTROL_SERVER = "http://127.0.0.1:5050"; // control server address
const POLL_INTERVAL_MS = 1500;
let lastCmdId = null;

// Utility wrappers
const tabsQuery = (q) => new Promise(r => chrome.tabs.query(q, r));
const tabsCreate = (p) => new Promise(r => chrome.tabs.create(p, r));
const tabsRemove = (ids) => new Promise(r => chrome.tabs.remove(ids, () => r(true)));
const tabsGroup = (p) => new Promise(r => chrome.tabs.group(p, r));
const tabGroupsUpdate = (id, p) => new Promise(r => chrome.tabGroups.update(id, p, r));
const tabGroupsGet = (id) => new Promise(res => chrome.tabGroups.get(id, g => {
  if (chrome.runtime.lastError) return res(null);
  res(g);
}));
const storageGet = (k) => new Promise(r => chrome.storage.local.get(k, r));
const storageSet = (o) => new Promise(r => chrome.storage.local.set(o, () => r(true)));

async function buildGroupMapFromTabs() {
  const tabs = await tabsQuery({});
  const groups = {};
  const gidToTitle = {};
  // find group ids
  const gIds = new Set();
  tabs.forEach(t => { if (typeof t.groupId === "number" && t.groupId >= 0) gIds.add(t.groupId); });
  for (const gid of Array.from(gIds)) {
    const g = await tabGroupsGet(gid);
    gidToTitle[gid] = (g && g.title) ? g.title : String(gid);
  }
  for (const t of tabs) {
    if (typeof t.groupId === "number" && t.groupId >= 0) {
      const title = gidToTitle[t.groupId] || String(t.groupId);
      groups[title] = groups[title] || [];
      if (t.url) groups[title].push(t.url);
    }
  }
  return groups;
}

async function syncGroupsToStorage() {
  try {
    const groups = await buildGroupMapFromTabs();
    await storageSet({ tab_groups: groups });
    // console.log("Synced groups:", Object.keys(groups));
  } catch (e) {
    console.warn("syncGroupsToStorage error", e);
  }
}

async function closeOtherGroups(keepGroupId) {
  try {
    const tabs = await tabsQuery({});
    const toClose = [];
    for (const t of tabs) {
      if (typeof t.groupId === "number" && t.groupId >= 0 && t.groupId !== keepGroupId) {
        toClose.push(t.id);
      }
    }
    if (toClose.length) await tabsRemove(toClose);
  } catch (e) {
    console.warn("closeOtherGroups error", e);
  }
}

async function openGroupByName(groupName) {
  try {
    const st = await storageGet(["tab_groups"]);
    const groups = st.tab_groups || {};
    const savedUrls = groups[groupName] || [];

    // 1. Create a new window with a dummy tab
    const newWin = await chrome.windows.create({ url: "about:blank", focused: true });
    const newWindowId = newWin.id;

    const openedTabIds = [];

    // 2. Open all saved URLs inside the new window
    for (const url of savedUrls) {
      const t = await tabsCreate({ url, active: false, windowId: newWindowId });
      openedTabIds.push(t.id);
    }

    // Remove the placeholder 'about:blank' tab
    const placeholder = newWin.tabs[0];
    if (placeholder && placeholder.url === "about:blank") {
      await tabsRemove(placeholder.id);
    }

    // 3. Group them inside the new window
    const groupId = await tabsGroup({ tabIds: openedTabIds });
    await tabGroupsUpdate(groupId, { title: groupName });

    // Focus the first tab
    if (openedTabIds.length) {
      chrome.tabs.update(openedTabIds[0], { active: true });
    }

    return { ok: true };

  } catch (e) {
    console.warn("openGroupByName error", e);
    return { ok: false, error: String(e) };
  }
}


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

// Poll control server for pending command
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
        if (cmd.action === "open_group") {
          const name = cmd.payload?.name;
          if (name) {
            const ok = await openGroupByName(name);
            // ack
            await fetch(CONTROL_SERVER + "/ack", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({ id: cmd.id, result: ok })
            });
          }
        } else if (cmd.action === "save_group") {
          const name = cmd.payload?.name;
          if (name) {
            const ok = await saveCurrentWindowAsGroup(name);
            await fetch(CONTROL_SERVER + "/ack", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({ id: cmd.id, result: ok })
            });
          }
        } else {
          // unknown: ack so it won't loop
          await fetch(CONTROL_SERVER + "/ack", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ id: cmd.id, result: { ok: false, error: "unknown action" } })
          });
        }
      }
    }
  } catch (e) {
    // server might be down - ignore
    // console.warn("poll error", e);
  } finally {
    busy = false;
  }
}

// initial sync and periodic tasks
//syncGroupsToStorage();
//setInterval(syncGroupsToStorage, 5000);  // keep storage updated
setInterval(pollLoop, POLL_INTERVAL_MS); // poll control server
