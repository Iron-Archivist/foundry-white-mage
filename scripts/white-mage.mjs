// White Mage: link "spend White Mana" costs to the actor's White Mana feature.
// Features are authored with consumption target "white-mana"; dnd5e needs the real item id.
const POOL = "white-mana";

function pool(actor) {
  return actor?.items.find(i => i.type === "feat" && i.system.identifier === POOL);
}

/** Rewrite placeholder/stale White Mana targets on one item. Returns update data or null. */
function fixItem(item, poolId) {
  const updates = {};
  for (const activity of item.system.activities ?? []) {
    const targets = activity.consumption.targets.map(t => t.toObject?.() ?? { ...t });
    let changed = false;
    for (const t of targets) {
      if (t.type !== "itemUses" || !t.target) continue;
      const pointsAt = item.actor.items.get(t.target);
      if ((t.target === POOL || !pointsAt) && t.target !== poolId) { t.target = poolId; changed = true; }
    }
    if (changed) updates[`system.activities.${activity.id}.consumption.targets`] = targets;
  }
  return Object.keys(updates).length ? updates : null;
}

async function relink(actor) {
  if (!actor?.isOwner) return;
  const p = pool(actor);
  if (!p) return;
  const updates = [];
  // White Mana starts empty: mark it fully spent the first time it is seen.
  if (!p.getFlag("white-mage", "init")) updates.push({ _id: p.id, "system.uses.spent": p.system.uses.max || 0, "flags.white-mage.init": true });
  for (const item of actor.items) {
    if (item === p || !item.getFlag("dnd5e", "sourceId")?.startsWith("Compendium.white-mage.")) continue;
    const u = fixItem(item, p.id);
    if (u) updates.push({ _id: item.id, ...u });
  }
  if (updates.length) await actor.updateEmbeddedDocuments("Item", updates);
}


const pending = new Map();
function schedule(actor) {
  if (!actor?.isOwner) return;
  clearTimeout(pending.get(actor.id));
  pending.set(actor.id, setTimeout(() => { pending.delete(actor.id); relink(actor); }, 250));
}
Hooks.on("createItem", (item, _o, userId) => { if (userId === game.userId) schedule(item.parent); });

// Clamp "Gain White Mana" so the pool can't exceed its maximum (dnd5e rejects spent < 0).
Hooks.on("dnd5e.preActivityConsumption", (activity, usageConfig) => {
  const item = activity.item;
  for (const t of activity.consumption.targets) {
    if (t.type !== "itemUses" || Number(t.value) >= 0) continue;
    const target = t.target ? item.actor?.items.get(t.target) : item;
    if (target && target.system.uses.spent <= 0) {
      ui.notifications.info(`${target.name} is already full.`);
      return false;
    }
  }
});

Hooks.once("ready", () => {
  for (const actor of game.actors) if (actor.isOwner && pool(actor)) relink(actor);
});
