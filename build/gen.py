#!/usr/bin/env python3
"""Generate White Mage dnd5e (5.3.x) documents as JSON for packing."""
import hashlib, json, sys, re

SRD = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
MOD = "white-mage"
PACK = f"Compendium.{MOD}.white-mage-items.Item."
SRC = {"custom": "White Mage (Final Fantasy homebrew) by ArchiverButcher", "book": "", "page": "", "license": "", "rules": "2014"}
WM = "white-mana"  # placeholder consumption target, resolved by scripts/white-mage.mjs

def ID(s):
    h = hashlib.sha1(s.encode()).hexdigest()
    a = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16); r = ""
    for _ in range(16): r += a[n % 62]; n //= 62
    return r

def html(t):
    out = []
    for para in [p.strip() for p in t.strip().split("\n\n") if p.strip()]:
        para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", para)
        para = re.sub(r"\*(.+?)\*", r"<em>\1</em>", para)
        if para.startswith("- "):
            out.append("<ul>" + "".join(f"<li>{l[2:]}</li>" for l in para.split("\n")) + "</ul>")
        else:
            out.append(f"<p>{para}</p>")
    return "".join(out)

def srd_spell(name):
    alias = {"Rary's Telepathic Bond": "Telepathic Bond", "Otiluke's Resilient Sphere": "Resilient Sphere",
             "Ressurection": "Resurrection", "True Ressurection": "True Resurrection"}
    e = SRD.get("spells|" + alias.get(name, name))
    return f"Compendium.dnd5e.spells.Item.{e['id']}" if e else None

# ---------- activity helpers ----------
def act(key, typ, name, *, activation="action", cost=None, own=None, extra=None, rng=None, dur=None, target=None, img=""):
    targets = []
    if own: targets.append({"type": "itemUses", "target": "", "value": str(own), "scaling": {"mode": "", "formula": ""}})
    if cost: targets.append({"type": "itemUses", "target": WM, "value": str(cost), "scaling": {"mode": "", "formula": ""}})
    a = {"_id": ID(key), "type": typ, "name": name, "img": img,
         "activation": {"type": activation, "value": 1 if activation in ("action", "bonus", "reaction") else None, "condition": "", "override": False},
         "consumption": {"targets": targets, "scaling": {"allowed": False, "max": ""}, "spellSlot": True},
         "description": {"chatFlavor": ""},
         "duration": dur or {"concentration": False, "value": "", "units": "inst", "special": "", "override": False},
         "effects": [], "range": rng or {"units": "self", "value": "", "special": "", "override": False},
         "target": target or {"template": {"count": "", "contiguous": False, "type": "", "size": "", "width": "", "height": "", "units": "ft"},
                              "affects": {"count": "", "type": "", "choice": False, "special": ""}, "prompt": True, "override": False},
         "uses": {"spent": 0, "recovery": [], "max": ""}, "sort": 0}
    if extra: a.update(extra)
    return a

def rng(ft): return {"units": "ft", "value": str(ft), "special": "", "override": False}
def tgt(count="1", type_="creature", tmpl=None, size=""):
    return {"template": {"count": "", "contiguous": False, "type": tmpl or "", "size": str(size), "width": "", "height": "", "units": "ft"},
            "affects": {"count": str(count), "type": type_, "choice": False, "special": ""}, "prompt": True, "override": False}
def conc(v, u): return {"concentration": True, "value": str(v), "units": u, "special": "", "override": False}
def dur(v, u): return {"concentration": False, "value": str(v), "units": u, "special": "", "override": False}
def roll(formula, name): return {"roll": {"formula": formula, "name": name, "prompt": False, "visible": True}}
def dmg(n, d, types, bonus="", on_save="half", custom=None):
    return {"number": n, "denomination": d, "bonus": bonus, "types": types,
            "custom": {"enabled": bool(custom), "formula": custom or ""}, "scaling": {"mode": "", "number": None, "formula": ""}}
def heal(formula, kind="healing"):
    return {"healing": {"number": None, "denomination": None, "bonus": "", "types": [kind],
                        "custom": {"enabled": True, "formula": formula}, "scaling": {"mode": "", "number": None, "formula": ""}}}
def save(ab, parts=(), on_save="half"):
    return {"save": {"ability": [ab], "dc": {"calculation": "spellcasting", "formula": ""}},
            "damage": {"onSave": on_save, "parts": list(parts)}}

docs = []
def feat(name, req, text, acts=(), uses=None, ident=None, img="icons/magic/holy/prayer-hands-glowing-yellow.webp", effects=()):
    _id = ID("feat:" + name)
    d = {"_id": _id, "name": name, "type": "feat", "img": img,
         "system": {"description": {"value": html(text), "chat": ""}, "source": SRC,
                    "uses": uses or {"max": "", "recovery": [], "spent": 0},
                    "type": {"value": "class", "subtype": ""}, "requirements": req, "properties": [],
                    "activities": {a["_id"]: a for a in acts}, "enchant": {}, "prerequisites": {"level": None},
                    "identifier": ident or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")},
         "effects": [e["_id"] for e in effects], "flags": {}, "folder": None, "sort": 0, "ownership": {"default": 0}}
    docs.append(("items", d))
    for e in effects: docs.append((f"items.effects", e | {"_parent": _id}))
    return PACK + _id

def effect(key, name, changes, img, dur_s=60):
    return {"_id": ID(key), "name": name, "img": img, "type": "base", "system": {}, "changes": changes,
            "disabled": False, "duration": {"seconds": dur_s, "startTime": None, "combat": None, "rounds": None, "turns": None, "startRound": None, "startTurn": None},
            "description": "", "origin": None, "tint": "#ffffff", "transfer": False, "statuses": [], "sort": 0, "flags": {}}

LR_LOSE = [{"period": "lr", "type": "loseAll"}]
CLS = "@classes.white-mage.levels"
NOTE_WM = "\n\n*Foundry: uses that spend White Mana draw from your <strong>White Mana</strong> feature automatically.*"

# ================= CORE CLASS FEATURES =================
f_wm = feat("White Mana", "White Mage 1", """
Having tapped into the primordial essence of the world that surrounds you, you have gained access to a pool of magic that is otherwise unavailable to anyone else. This energy manifests in the form of *White Mana*, which manifests as a resource that you use.

This mana can be used to enhance spells that you cast, or white mana features that you learn to utilize throughout your journey. At any given time, you can only have a reserve of *White Mana* equal to your Proficiency Bonus. After you finish a long rest, you lose all *White Mana* you have currently. When *White Mana* is used, it manifests as a dice that you can add to rolls in addition to the beneficial enhancements, the dice size being a d6.

**When a White Mana is referred to as "being added/subtracted" or "being rolled" in the context of an ability or feature, you are rolling a d6.**

In order to gain *White Mana*, you must cast a **healing spell** of the 1st level or higher that heals at least one creature other than you. When you aid a creature other than you with an otherwise beneficial effect or status spell (such as Haste), this will also grant you *White Mana*. You gain one *White Mana* when you do either, even if you use a *White Mana* to enhance the spell being cast.

**Healing Spells.** Refers strictly to spells that in any way grant hit points (normal or temporary) to a creature, or multiple creatures in the case of spells such as *Mass Cure Wounds* or *Healing Spirit*.

*Foundry: the uses on this feature are your current White Mana (max = proficiency bonus). It starts empty and empties on a long rest. Use <strong>Gain White Mana</strong> after a qualifying spell. Features that spend White Mana deduct it from here automatically. Order of the Lily: these are your petals.*
""", acts=[
    act("wm:gain", "utility", "Gain White Mana", activation="special", extra={"consumption": {"targets": [{"type": "itemUses", "target": "", "value": "-1", "scaling": {"mode": "", "formula": ""}}], "scaling": {"allowed": False, "max": ""}, "spellSlot": True}}),
    act("wm:spend", "utility", "Spend White Mana (d6)", activation="special", own=1, extra=roll("1d6", "White Mana")),
], uses={"max": "@prof", "recovery": LR_LOSE, "spent": 0}, ident="white-mana", img="icons/magic/light/orb-lightbulb-gray.webp")

f_benison = feat("Benison", "White Mage 1", """
When you cast a healing spell that **targets only 1 creature**, you can choose to spend *1 White Mana* to add to the hit points granted. If the creature's current hit points reach its *maximum hit points* with the healing, any leftover hit points granted becomes temporary hit points. These temporary hit points last until the start of your next turn.""" + NOTE_WM,
    acts=[act("benison", "heal", "Benison", activation="special", cost=1, rng=rng(""), target=tgt(), extra=heal("1d6"))],
    img="icons/magic/life/heart-cross-green.webp")

f_orison = feat("Orison", "White Mage 3", """
Beginning at the 3rd level, you continue improving your connection with the world at large, letting it flow through you. As part of a long rest, you can perform a ritual, spending 10 minutes of that long rest in prayer and communion. After this ritual is completed, you gain a number of *White Mana* equal to half of your Wisdom modifier. This *White Mana* does **not** count towards the normal reserve of *White Mana* you accumulate, but also disappears when you take a long rest. If you deplete Orison's *White Mana*, it does not get replenished until you perform the ritual again as part of another long rest.

*Foundry: this feature's uses are your Orison White Mana. They refill on a long rest (assumed: you performed the ritual), and at 11th level the maximum becomes your full Wisdom modifier (Enhanced Orison). Spend them with the activity here instead of from White Mana.*""",
    acts=[act("orison:spend", "utility", "Spend Orison Mana (d6)", activation="special", own=1, extra=roll("1d6", "White Mana"))],
    uses={"max": f"max(0, floor(@abilities.wis.mod / (2 - min(1, floor({CLS} / 11)))))", "recovery": [{"period": "lr", "type": "recoverAll"}], "spent": 0},
    img="icons/magic/holy/prayer-hands-glowing-yellow-white.webp")

f_renum = feat("Renumeration", "White Mage 5", """
By the 5th level, you cherish the world for what it is, and you have a deep respect that only continues to grow for it. The balance that is achieved with active influence and passive observation.

When you spend a white mana on any feature or ability, whether on its own or to enhance a spell, you are able to cast a cantrip of your choice as a bonus action on this turn, or if you are using a reaction ability, on your next turn.

Additionally, you take the cantrip *Glare* which does not count towards your cantrips known. If you already know *Glare*, take another cantrip from the white mage spell list.""", img="icons/magic/light/beam-rays-yellow.webp")

f_solace = feat("Afflatus Solace", "White Mage 7", """
Starting at the 7th level, when you cast a spell that can heal a creature, you can choose to spend *1 White Mana*, adding it to the healing spell. You grant half of the total hit points to the target creature, and you can choose a creature within 30 feet of you that you can see to benefit from the other half. You can choose which creature gets the lower amount if the hit points are distributed unevenly.

If you cast a spell that can heal multiple creatures, you can only choose to split the healing for one of those creatures to be given to another creature that is not being healed, and the two affected creatures must be within 30 feet of each other.

**Order of the Lily (through the Lily):** You split the hit points, and then give each creature additional hit points equal to your White Mana dice roll.""" + NOTE_WM,
    acts=[act("solace", "heal", "Afflatus Solace", activation="special", cost=1, rng=rng(30), target=tgt(), extra=heal("1d6"))],
    img="icons/magic/life/heart-glowing-red.webp")

f_invig = feat("Afflatus Invigoration", "White Mage 11", """
When you reach level 11, with the intimate connection you have developed and nurtured with the divine essence of the world, you have built a stable, durable foundation that you stand on now.

You gain advantage on Constitution Saving throws made for your concentration checks of holding spells that grant you *White Mana* (Healing spells and spells that aid your allies with status effects or otherwise, such as Haste).

**Enhanced Orison.** When you perform the ritual, you now gain a number of *White Mana* equal to your Wisdom modifier, instead of half. *(Applied automatically to Orison.)*""", img="icons/magic/defensive/shield-barrier-glowing-blue.webp")

f_liturgy = feat("Afflatus Liturgy", "White Mage 17", """
At level 17, you've reached rubicon in your embrace of the energy that surrounds everyone, having culminated and transcended your cultivation to a simple but effective faith in the machinations of the world.

As a bonus action you clasp your hands together, letting the divine essence of the world and nature subsume you, even if only for a moment. The next healing spell you cast before the end of your next turn ignores concentration requirements and will persist even if you become unconscious. If the spell does not have a concentration requirement, you instead cast the spell without spending a spell slot, assuming it is no higher than 6th level.

You spend *5 White Mana* when you use this ability, and you can only do this once per long rest. You do not regain *White Mana* with the spell being cast.

**Order of the Lily (through the Lily):** You spend 3 *petals* instead of 5.

*Foundry: at 20th level (Devout of the White) this recovers on a short rest. Restore its use manually after a short rest. Lily casters: use the Lily activity (3 petals).*""",
    acts=[act("liturgy", "utility", "Afflatus Liturgy", activation="bonus", own=1, cost=5, dur=dur(1, "turn")),
          act("liturgy:lily", "utility", "Afflatus Liturgy (Lily, 3 petals)", activation="bonus", own=1, cost=3, dur=dur(1, "turn"))],
    uses={"max": "1", "recovery": [{"period": "lr", "type": "recoverAll"}], "spent": 0}, img="icons/magic/holy/barrier-shield-winged-blue.webp")

f_devout = feat("Devout of the White", "White Mage 20", """
Upon reaching level 20, when you cast a healing spell and you use a white mana feature for that spell, you add a number of *White Mana* to be rolled for healing equal to the spell level of the spell that's being cast instead of just 1 *White Mana* dice. Additionally, when you cast a spell, you now regain *White Mana* equal to half of the spell level that it was cast at, rounded down, in addition to the *1 White Mana* you regain. If you roll initiative and you have no *White Mana*, you immediately gain *1 White Mana*.

Afflatus Liturgy can now be used once per short rest.""",
    acts=[act("devout:roll", "heal", "Devout Healing (spell-level d6)", activation="special", rng=rng(""), target=tgt(),
              extra=heal("(@item.level)d6") | {"consumption": {"targets": [], "scaling": {"allowed": True, "max": "9"}, "spellSlot": True}})],
    img="icons/magic/light/explosion-star-glow-silhouette.webp")

# ================= SPELLS (homebrew, from the document) =================
def spell(name, level, school, text, props, acts, act_type="action", rng_=None, duration=None, target=None, materials="", img="", effects=()):
    _id = ID("spell:" + name)
    d = {"_id": _id, "name": name, "type": "spell", "img": img,
         "system": {"description": {"value": html(text), "chat": ""}, "source": SRC,
                    "activation": {"type": act_type, "condition": "", "value": 1},
                    "duration": duration or {"value": "", "units": "inst"},
                    "target": target or {"affects": {"type": "creature", "count": "1", "choice": False, "special": ""}, "template": {"units": "", "contiguous": False, "type": ""}},
                    "range": rng_ or {"value": "", "units": "self", "special": ""},
                    "uses": {"max": "", "recovery": [], "spent": 0}, "level": level, "school": school,
                    "materials": {"value": materials, "consumed": False, "cost": 0, "supply": 0},
                    "preparation": {"mode": "prepared", "prepared": False}, "properties": props,
                    "activities": {a["_id"]: a for a in acts}, "identifier": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")},
         "effects": [e["_id"] for e in effects], "flags": {}, "folder": None, "sort": 0, "ownership": {"default": 0}}
    docs.append(("items", d))
    for e in effects: docs.append(("items.effects", e | {"_parent": _id}))
    return PACK + _id

def spell_act(key, typ, name, extra):
    a = act(key, typ, name, extra=extra); a["activation"]["override"] = False
    a["range"] = {"override": False}; a["duration"] = {"override": False, "units": "inst", "concentration": False}
    a["target"] = {"prompt": True, "template": {"contiguous": False, "units": "ft"}, "affects": {"choice": False}, "override": False}
    return a

def attack(parts):
    return {"attack": {"ability": "", "bonus": "", "critical": {"threshold": None}, "flat": False, "type": {"value": "ranged", "classification": "spell"}},
            "damage": {"critical": {"bonus": ""}, "includeBase": True, "parts": parts}}

cantrip_scale = lambda n, d, t: {**dmg(n, d, t), "scaling": {"mode": "whole", "number": 1, "formula": ""}}

s_glare = spell("Glare", 0, "evo", """
You emit a bolt of holy energy that crackles through the air towards a target that you can see in range. Make a ranged spell attack. On a hit, you deal 1d8 radiant damage. If the target is undead, you deal 1d10 instead.

**At Higher Levels.** This spell's damage increases by 1d8 when you reach 5th level (2d8), 11th level (3d8), and 17th level (4d8).""",
    ["vocal", "somatic"], [spell_act("glare", "attack", "Glare", attack([cantrip_scale(1, 8, ["radiant"])])),
                           spell_act("glare:undead", "attack", "Glare (Undead)", attack([cantrip_scale(1, 10, ["radiant"])]))],
    rng_={"value": "90", "units": "ft", "special": ""}, img="icons/magic/light/projectile-beam-yellow.webp")

s_aero = spell("Aero", 0, "con", """
You target a creature that you can see within range, spilling out a whorl of turbulent air towards them. Make a ranged spell attack against the creature. On a hit, they take 1d4 force damage. At the start of their turn, they must make a Dexterity Saving Throw against your Spell Save DC. They must succeed, or they take 1d4 force damage. On a success, they take no damage. The creature must continue making Dexterity Saving Throws on each of their turns for as long as you concentrate on this spell. If you missed the initial attack, the spell has no effect.""",
    ["somatic", "concentration"],
    [spell_act("aero", "attack", "Aero", attack([dmg(1, 4, ["force"])])),
     spell_act("aero:save", "save", "Aero (start of turn)", save("dex", [dmg(1, 4, ["force"])], on_save="none"))],
    rng_={"value": "60", "units": "ft", "special": ""}, duration={"value": "1", "units": "minute"}, img="icons/magic/air/wind-tornado-funnel-blue.webp")

eff_stone = effect("eff:stone", "Stone's Endurance", [{"key": "system.attributes.ac.bonus", "mode": 2, "value": "+2", "priority": None}], "icons/magic/nature/root-vine-entwined-thorns.webp")
a_stone = spell_act("stone", "utility", "Stone's Endurance", {"effects": [{"_id": eff_stone["_id"]}]})
s_stone = spell("Stone's Endurance", 1, "abj", """
Faint mirages of vines and twigs appear and surround up to 3 creatures of your choice within range excluding you, granting them a +2 bonus to AC for the duration.""",
    ["vocal", "somatic", "material", "concentration"], [a_stone], rng_={"value": "30", "units": "ft", "special": ""},
    duration={"value": "1", "units": "minute"}, target={"affects": {"type": "ally", "count": "3", "choice": True, "special": ""}, "template": {"units": "", "contiguous": False, "type": ""}},
    materials="A twig with green leaves", img="icons/magic/nature/root-vine-entwined-thorns.webp", effects=[eff_stone])

# ================= SUBCLASSES =================
def spells_grant(level, names, title):
    uuids = [u for u in (srd_spell(n) for n in names) if u]
    if not uuids: return None
    return {"_id": ID(f"sg:{title}:{level}"), "type": "ItemGrant", "level": level, "title": title, "hint": "",
            "configuration": {"items": [{"uuid": u, "optional": False} for u in uuids], "optional": False,
                              "spell": {"ability": [], "preparation": "always", "uses": {"max": "", "per": "", "requireSlot": False}}}, "value": {}}

def grant(level, uuids, title="Features"):
    return {"_id": ID(f"g:{title}:{level}:{uuids[0]}"), "type": "ItemGrant", "level": level, "title": title, "hint": "",
            "configuration": {"items": [{"uuid": u, "optional": False} for u in uuids], "optional": False,
                              "spell": {"ability": [], "preparation": "", "uses": {"max": "", "per": ""}}}, "value": {}}

def subclass(name, text, spell_table, feats, img):
    title = name.replace("Order of the ", "").replace("Order of ", "") + " Spells"
    adv = [a for a in (spells_grant(lvl, sp, title) for lvl, sp in spell_table) if a]
    adv += [grant(lvl, [u]) for lvl, u in feats]
    rows = "".join(f"<tr><td>{lvl}</td><td>{', '.join(sp)}</td></tr>" for lvl, sp in spell_table)
    missing = sorted({s for _, sp in spell_table for s in sp if not srd_spell(s)})
    note = (f"<p><em>Foundry: SRD spells are added automatically as always prepared. Not in the SRD, add them from your own sources: {', '.join(missing)}.</em></p>" if missing else "")
    desc = html(text) + f"<h3>{title}</h3><table><thead><tr><th>White Mage Level</th><th>Spells</th></tr></thead><tbody>{rows}</tbody></table><p>You gain access to these spells at the listed levels, and they do not count towards your number of spells you have prepared.</p>" + note
    _id = ID("sub:" + name)
    docs.append(("items", {"_id": _id, "name": name, "type": "subclass", "img": img,
        "system": {"description": {"value": desc, "chat": ""}, "source": SRC,
                   "identifier": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"), "classIdentifier": "white-mage",
                   "advancement": adv, "spellcasting": {"progression": "none", "ability": "", "preparation": {}}},
        "effects": [], "flags": {}, "folder": None, "sort": 0, "ownership": {"default": 0}}))
    return PACK + _id

# --- Turmoil
t1 = feat("Afflatus Impairment", "Order of Turmoil 2", """
Starting at the 2nd level, when a creature within 60 feet of you is forced to make a Saving throw against a check that is being imposed on it, you can use your reaction to spend *1 White Mana*. Subtract the creature's roll with it, potentially turning a success into a failure. You must do this before the Saving throw is announced to be a success or failure.

You can only perform this reaction when it is another creature other than yourself imposing the Saving throw check.""" + NOTE_WM,
    acts=[act("t1", "utility", "Afflatus Impairment", activation="reaction", cost=1, rng=rng(60), target=tgt(), extra=roll("1d6", "Subtract from save"))],
    img="icons/magic/control/debuff-energy-hold-levitate-pink.webp")
t2 = feat("Enervate", "Order of Turmoil 6", """
At the 6th level, as an action, you spend *1 White Mana* to target a creature within 60 feet of you that you can see. The target creature makes a Strength Saving throw against your Spell Save DC. On a failure, the target creature gets *marked* by your white magic, becoming weaker and less enthused for combat, and whenever they make an attack until the start of your next turn, you subtract from the roll they make for their damage.

On a success, they instead take 1d6 radiant damage.""" + NOTE_WM,
    acts=[act("t2", "save", "Enervate", cost=1, rng=rng(60), target=tgt(), dur=dur(1, "round"), extra=save("str")),
          act("t2:dmg", "damage", "Enervate: radiant on success", activation="special", rng=rng(60), target=tgt(), extra={"damage": {"critical": {"allow": False}, "parts": [dmg(1, 6, ["radiant"])]}}),
          act("t2:red", "utility", "Enervate: reduce damage", activation="special", extra=roll("1d6", "Damage reduction"))],
    img="icons/magic/control/debuff-chains-shackle-movement-red.webp")
t3 = feat("Mask of Death", "Order of Turmoil 10", """
Upon reaching level 10, as an action, you can spend *3 White Mana*, donning an ethereal visage that exudes fearsomeness and causes even the most stalwart of souls to tremble. All creatures of your choice within 30 feet of you that can see you, must make a Wisdom Saving throw against your Spell Save DC. On a failure, a creature is *frightened* of you. A creature can repeat the Saving throw at the end of their turn, and once they break free, they cannot be frightened again unless a new visage is summoned. The mask lasts for 1 minute or until it's dispelled as a bonus action. While a creature is *frightened* of you in this way and another creature attacks them, the *frightened* creature takes 1d6 psychic damage that you add to the attack.""" + NOTE_WM,
    acts=[act("t3", "save", "Mask of Death", cost=3, dur=dur(1, "minute"), target=tgt("", "enemy", "radius", 30), extra=save("wis")),
          act("t3:dmg", "damage", "Mask of Death: psychic", activation="special", target=tgt(), extra={"damage": {"critical": {"allow": False}, "parts": [dmg(1, 6, ["psychic"])]}})],
    img="icons/magic/death/skull-horned-worn-fire-blue.webp")
t4 = feat("Spirits of the Abyss", "Order of Turmoil 14", """
At level 14, as an action, a cacophony of ethereal spirits are summoned and surround you, swarming in a 30-foot circle focused on you and move with you. **This lasts for 1 minute or until it's dispelled as a bonus action, and requires concentration**. This can only be done once per short rest.

Any creature that is considered hostile towards you must make a Strength Saving throw against your Spell Save DC when they enter this field. On a failure, for as long as the creature stays within the field, whenever they attempt to hit a creature other than you, you subtract 1d6 from their attack roll, potentially causing a hit to miss instead.

When you move or when a creature leaves the field but enters it again, the Saving throw is repeated, regardless of if the creature failed or succeeded before.""",
    acts=[act("t4", "save", "Spirits of the Abyss", own=1, dur=conc(1, "minute"), target=tgt("", "enemy", "radius", 30), extra=save("str")),
          act("t4:sub", "utility", "Subtract from attack", activation="special", extra=roll("1d6", "Subtract from attack"))],
    uses={"max": "1", "recovery": [{"period": "sr", "type": "recoverAll"}], "spent": 0}, img="icons/magic/unholy/silhouette-evil-horned-giant.webp")
sub_turmoil = subclass("Order of Turmoil", """
White Mages that have achieved an attunement with the wrath of the world, with an aim to destabilize enemies where they were once sure-footed and instill confusion and fear where there was once an ironclad heart and will.""",
    [(2, ["Bane", "Cause Fear"]), (5, ["Bestow Curse", "Hypnotic Pattern"]), (9, ["Elemental Bane", "Polymorph"]), (11, ["Enervation", "Synaptic Static"])],
    [(2, t1), (6, t2), (10, t3), (14, t4)], "icons/magic/unholy/orb-glowing-purple.webp")

# --- Serenity
eff_bless = effect("eff:afblessing", "Afflatus Blessing", [
    {"key": f"system.bonuses.{k}.attack", "mode": 2, "value": "+1d6", "priority": None} for k in ("mwak", "rwak", "msak", "rsak")] +
    [{"key": "system.bonuses.abilities.save", "mode": 2, "value": "+1d6", "priority": None}], "icons/magic/holy/angel-wings-gray.webp")
s1 = feat("Temperance", "Order of Serenity 2", """
Upon reaching level 2, when a creature within 90 feet of you that you can see is forced to make a saving throw, you can use your reaction to spend *1 White Mana*, adding to the creature's saving throw. This can be done after the creature rolls for their saving throw but must be done before the outcome of the roll is announced.""" + NOTE_WM,
    acts=[act("s1", "utility", "Temperance", activation="reaction", cost=1, rng=rng(90), target=tgt(), extra=roll("1d6", "Add to save"))],
    img="icons/magic/defensive/shield-barrier-flaming-diamond-blue-yellow.webp")
s2 = feat("Steady Wind", "Order of Serenity 6", """
At level 6, as an action, you can spend *1 White Mana*, adding the roll + your White Mage level as temporary hit points to a creature of your choice that you can see within 60 feet of you. If the temporary hit points are depleted before your next turn, the target creature can use their reaction to disengage and move up to half of their movement speed in any direction they wish.""" + NOTE_WM,
    acts=[act("s2", "heal", "Steady Wind", cost=1, rng=rng(60), target=tgt(), extra=heal(f"1d6 + {CLS}", "temphp"))],
    img="icons/magic/air/wind-swirl-gray-blue.webp")
s3 = feat("Guiding Hand", "Order of Serenity 10", """
Reaching level 10, as an action, you can spend *3 White Mana* and choose a number of creatures, but not yourself, within 30 feet of you equal to your Wisdom modifier. These creatures gain temporary hit points equal to the number you roll (3d6). While these temporary hit points persist, when a creature makes an attack roll, they add your proficiency bonus to the attack roll. The temporary hit points last for 1 minute.""" + NOTE_WM,
    acts=[act("s3", "heal", "Guiding Hand", cost=3, rng=rng(30), dur=dur(1, "minute"), target=tgt("@abilities.wis.mod", "ally"), extra=heal("3d6", "temphp"))],
    img="icons/magic/life/cross-beam-green.webp")
a_bless = act("s4", "utility", "Afflatus Blessing", own=1, rng=rng(30), dur=conc(1, "minute"), target=tgt("@abilities.wis.mod", "ally"), extra={"effects": [{"_id": eff_bless["_id"]}]})
s4 = feat("Afflatus Blessing", "Order of Serenity 14", """
At level 14, as an action, you can grant a blessing to a number of creatures, but not yourself, within 30 feet of you equal to your Wisdom Modifier. This can be done once per short rest.

**This blessing lasts for 1 minute and requires concentration, or until you dispel it as a bonus action.** While a creature has this blessing, they add your White Mana dice for their attack rolls and saving throws.

*Foundry: applying the effect adds +1d6 to the target's attack rolls and saving throws.*""",
    acts=[a_bless], uses={"max": "1", "recovery": [{"period": "sr", "type": "recoverAll"}], "spent": 0},
    img="icons/magic/holy/angel-wings-gray.webp", effects=[eff_bless])
sub_serenity = subclass("Order of Serenity", """
The most common White Mage that anyone can find. Their magic is deep in the well spring of nurture and succor. There is nothing but empathy and compassion for life and the vibrance that it brings.""",
    [(2, ["Bless", "Cure Wounds"]), (5, ["Aura of Vitality", "Beacon of Hope"]), (8, ["Aura of Purity", "Freedom of Movement"]), (11, ["Greater Restoration", "Skill Empowerment"])],
    [(2, s1), (6, s2), (10, s3), (14, s4)], "icons/magic/life/heart-cross-strong-flame-green.webp")

# --- Sacrifice
c1 = feat("Soul Bargain", "Order of Sacrifice 2", """
At level 2, when you use a healing spell on a creature, you can choose to empower it with *1 White Mana*. When you do so, you choose a willing creature within 60 feet of you, or yourself, to bolster the healing power of the spell. In addition to the number that you rolled on the White Mana dice, the creature can choose to give up a number of hit points equal to their Constitution modifier + their total level to directly give to the creature being healed.

If the creature gives hit points equal to or greater than the White Mana roll, the creature giving up hit points is then able to add a d6 to an attack roll within the next minute. When you choose yourself to sacrifice hit points, you must give up hit points equal to double the White Mana dice roll (up to 12 potentially) in order to add a d6 on one of your attack rolls.""" + NOTE_WM,
    acts=[act("c1", "heal", "Soul Bargain", activation="special", cost=1, rng=rng(60), target=tgt(), extra=heal("1d6"))],
    img="icons/magic/life/heart-hand-gold-green.webp")
c2 = feat("Revenant Touch", "Order of Sacrifice 6", """
Upon reaching level 6, when you use a spell on a creature, you can choose to empower it with *1 White Mana*. You subtract your White Mana dice roll from your hit points as a sacrifice. If this is a healing spell, the creature you are targeting gains temporary hit points equal to 2d6 + your Proficiency bonus in addition to the healing.

If this is a spell that deals damage, you instead add your Proficiency bonus to your attack roll, again if you already do, and to your damage if it hits.""" + NOTE_WM,
    acts=[act("c2", "damage", "Revenant Touch: sacrifice (self)", activation="special", cost=1, target=tgt("1", "self"), extra={"damage": {"critical": {"allow": False}, "parts": [dmg(1, 6, ["necrotic"])]}}),
          act("c2:thp", "heal", "Revenant Touch: temp HP", activation="special", target=tgt(), extra=heal("2d6 + @prof", "temphp"))],
    img="icons/magic/unholy/hand-light-pink.webp")
c3 = feat("Reaper's Ward", "Order of Sacrifice 10", """
At level 10, as a reaction to a creature within 90 feet of you that you can see being brought to 0 hit points, you can spend *3 White Mana*, taking 3d6 unmitigated damage to yourself in order to allow the target creature to make a Constitution Saving throw, with the Save DC being 10 or half the damage taken, whichever is greater.

On a success, the creature regains hit points equal to the damage you had taken. On a failure, the creature falls unconscious as normal and are at 0 hit points.

If the damage being dealt to the creature is equal to or greater than half of the total hit points the target creature has, it automatically fails the Saving throw.""" + NOTE_WM,
    acts=[act("c3", "damage", "Reaper's Ward: sacrifice (self)", activation="reaction", cost=3, rng=rng(90), target=tgt("1", "self"), extra={"damage": {"critical": {"allow": False}, "parts": [dmg(3, 6, ["necrotic"])]}})],
    img="icons/magic/death/hand-undead-skeleton-fire-green.webp")
c4 = feat("Weight of Sacrifice", "Order of Sacrifice 14", """
At level 14, as an action, you can completely drain your lifeforce in exchange for great power. All of your hit points except 1 becomes temporary hit points, and until either 1 minute passes, or you deplete all of your temporary hit points, your maximum hit points is set to 1 and you cannot benefit from healing or gain additional temporary hit points. When a minute passes, any remaining temporary hit points that you have transforms back into your normal hit points, and you regain your normal maximum hit points. This can be done once per short rest.

While you are in this state, you can use your temporary hit points to sacrifice as hit points for the purposes of your White Mana abilities. While you sacrifice hit points as normal for the features that require you to, your healing spells and abilities are treated as guaranteed critical hits.

*Foundry: adjust hit points and temporary hit points by hand.*""",
    acts=[act("c4", "utility", "Weight of Sacrifice", own=1, dur=dur(1, "minute"))],
    uses={"max": "1", "recovery": [{"period": "sr", "type": "recoverAll"}], "spent": 0}, img="icons/magic/unholy/strike-body-life-soul-purple.webp")
sub_sacrifice = subclass("Order of Sacrifice", """
These are White Mages that have grasped a deeper understanding of the world. Embracing the truth that balance comes with a price. And the greater the stakes, the greater the cost. However, they willingly press further, knowing that the greater good far outweighs the risks that may be presented in any fight.""",
    [(2, ["Hellish Rebuke", "Heroism"]), (5, ["Feign Death", "Life Transference"]), (8, ["Aura of Life", "Death Ward"]), (11, ["Contagion", "Rary's Telepathic Bond"])],
    [(2, c1), (6, c2), (10, c3), (14, c4)], "icons/magic/unholy/hand-claw-glow-orange.webp")

# --- Lily
l0 = feat("Petals of the Lily", "Order of the Lily 2", """
Your White Mana is transformed into a Lily. A vibrant, ethereal lily that is of any appearance, shape, and color of your choosing. They are intangible to everyone including you and are a manifestation of your communion with the most ancient of spirits. It occupies a 5-foot space, which cannot be stood in by other creatures, but can be walked through by both hostile and ally creatures. The Lily lasts until you finish a long rest, or when you dispel it with a bonus action.

Instead of gaining White Mana, you have a Lily and along with it, *petals* that function the same as *White Mana*. As a bonus action, you can place down a Lily for free once per short rest and spend *1 petal* to do so every time you summon or move the Lily after the first time. You must be within 30 feet of your Lily at all times, or else it disappears, however when you cast a spell or use a white mana feature, you can choose to have it be cast from the Lily instead of yourself. If you fall unconscious, the Lily disappears.

When you use the Lily for your white mana features, you gain further increased benefits, including with the main class features:

- **Lily Benison:** When a creature gains the hit points, they gain +1 to their AC until your next turn.
- **Afflatus Solace:** You split the hit points, and then give each creature additional hit points equal to your White Mana dice roll.
- **Afflatus Liturgy:** You spend 3 *petals* instead of 5.

*Foundry: petals are the uses on your White Mana feature.*""",
    acts=[act("l0:free", "utility", "Place Lily (free)", activation="bonus", own=1, rng=rng(30), dur=dur("", "perm"), target=tgt("", "space")),
          act("l0:move", "utility", "Summon / Move Lily (1 petal)", activation="bonus", cost=1, rng=rng(30), dur=dur("", "perm"), target=tgt("", "space"))],
    uses={"max": "1", "recovery": [{"period": "sr", "type": "recoverAll"}], "spent": 0}, img="icons/magic/nature/lotus-glow-pink.webp")
eff_lilyac = effect("eff:lilyac", "Lily Benison", [{"key": "system.attributes.ac.bonus", "mode": 2, "value": "+1", "priority": None}], "icons/magic/nature/lotus-glow-pink.webp", 6)
l1 = feat("Lily's Embrace", "Order of the Lily 2", """
Starting at 2nd level, when you use a healing spell through the Lily, you can spend *1 petal* to add your Proficiency bonus in addition to the White Mana dice for healing, as well as increase the range of the spell by 30 feet (including touch spells).

If it is a damaging spell, you spend a *petal* to add your Proficiency bonus to the damage if the spell hits.""" + NOTE_WM,
    acts=[act("l1", "heal", "Lily's Embrace (healing)", activation="special", cost=1, rng=rng(""), target=tgt(), extra=heal("1d6 + @prof")),
          act("l1:dmg", "damage", "Lily's Embrace (damage)", activation="special", cost=1, target=tgt(), extra={"damage": {"critical": {"allow": False}, "parts": [dmg(None, None, [], custom="@prof")]}}),
          act("l1:ac", "utility", "Lily Benison (+1 AC)", activation="special", target=tgt(), dur=dur(1, "round"), extra={"effects": [{"_id": eff_lilyac["_id"]}]})],
    img="icons/magic/nature/plant-sprout-hand-flower-pink.webp", effects=[eff_lilyac])
l2 = feat("Shield of the Lily", "Order of the Lily 6", """
Upon reaching level 6, as a reaction to a creature being attacked within 30 feet of the Lily or you, you can spend a *petal* to grant the attacked creature a bonus 1d6 to their AC for that attack.

If the attack fails to hit, the attacked creature can use their reaction to make an attack of opportunity as the creature gets staggered. If the attack does hit, the attacked creature can use their reaction to take the disengage action, giving them 15 feet of movement immediately.""" + NOTE_WM,
    acts=[act("l2", "utility", "Shield of the Lily", activation="reaction", cost=1, rng=rng(30), target=tgt(), extra=roll("1d6", "AC bonus"))],
    img="icons/magic/defensive/shield-barrier-flaming-pentagon-purple-orange.webp")
l3 = feat("Liturgy of the Lily", "Order of the Lily 10", """
At level 10, as a bonus action, you can spend a *petal* to activate the Lily, making it pulsate with soothing magic. All creatures that you choose within 30 feet of it regains 1d6 hit points + your Proficiency bonus. If the creature's current hit points reach its maximum hit points with the granted hit points, any remaining hit points being granted becomes temporary hit points.""" + NOTE_WM,
    acts=[act("l3", "heal", "Liturgy of the Lily", activation="bonus", cost=1, target=tgt("", "ally", "radius", 30), extra=heal("1d6 + @prof")),
          act("l3:free", "heal", "Liturgy of the Lily (free, from Misery)", activation="reaction", target=tgt("", "ally", "radius", 30), extra=heal("1d6 + @prof"))],
    img="icons/magic/nature/lotus-glow-pink.webp")
l4 = feat("Afflatus Misery", "Order of the Lily 14", """
Starting at level 14, once you have used three *petals* through the Lily, the Lily now blooms.

As an action once the Lily is in bloom, you can have the Lily launch an orb of divine essence up to 60 feet away from its current position. Any creature in a 15-foot sphere of the orb on impact must then make a Dexterity Saving throw against your Spell Save DC. On a failure, a creature takes 4d8 radiant damage, or half damage on a success.

If the Lily deals at least 30 damage, you can use your reaction to use *Liturgy of the Lily* without cost as long as it's through the Lily (you do not gain a *petal*).

After the Lily launches the orb, it loses its bloom status, and it takes another *three petals* to bring it back into bloom.

*Foundry: the uses here count petals spent through the Lily since the last orb. Use "Petal spent" to count one. The orb is usable once all 3 are counted.*""",
    acts=[act("l4:count", "utility", "Petal spent through the Lily", activation="special",
              extra={"consumption": {"targets": [{"type": "itemUses", "target": "", "value": "-1", "scaling": {"mode": "", "formula": ""}}], "scaling": {"allowed": False, "max": ""}, "spellSlot": True}}),
          act("l4", "save", "Afflatus Misery", own=3, rng=rng(60), target=tgt("", "creature", "sphere", 15), extra=save("dex", [dmg(4, 8, ["radiant"])]))],
    uses={"max": "3", "recovery": [{"period": "lr", "type": "loseAll"}], "spent": 3}, img="icons/magic/light/orb-beams-green.webp")
sub_lily = subclass("Order of the Lily", """
White Mages that have fully consigned themselves to the wheel of fate, they are exceptional healers and greatly empower their allies. They've fused their destinies with the world, and as such have been granted the ability to manifest its divine will in a way no one else can.""",
    [(2, ["Cure Wounds", "Sanctuary"]), (5, ["Haste", "Summon Fey"]), (8, ["Conjure Woodland Beings", "Otiluke's Resilient Sphere"]), (11, ["Circle of Power", "Wrath of Nature"])],
    [(2, l0), (2, l1), (6, l2), (10, l3), (14, l4)], "icons/magic/nature/lotus-glow-pink.webp")
# merge level-2 Lily grants into one
lily = next(d for p, d in docs if d["_id"] == sub_lily.split(".")[-1])
g2 = [a for a in lily["system"]["advancement"] if a["type"] == "ItemGrant" and a["level"] == 2 and a["configuration"]["spell"]["preparation"] == ""]
g2[0]["configuration"]["items"] += g2[1]["configuration"]["items"]; lily["system"]["advancement"].remove(g2[1])

# ================= CLASS =================
CLASS_DESC = html("""
*A caravan sluggishly wheels its way across a cobblestone road through a turgid swamp... the boy in robes not only mends the wounds of the warriors, but also empowers them to be even more ruthless.*

**Nature's Divinity.** White Mages share an ironclad faith not in any of these deities, but instead the world itself. They draw their power from the ambient magic of the world, ancient spirits, and the ancient laws that every mortal, and even deities to an extent, must abide by. Their reverence and faith goes towards the balance that is struck between life and death, good and evil, law and chaos.

**White Magic.** No one is immortal, and just so, no ardor lasts forever. The power of the universal law and the thrumming heart of the world is what White Mages draw their power from. There are no official establishments, and more often than not White Mages are found interspersed within religious organizations, mercenary groups, and even industries.

**Quick Build.** Make Wisdom your highest ability score, followed by Constitution or Charisma. Take the Acolyte background. Take Glare or Aero, and Prestidigitation or Message for your cantrips, along with the 1st-level spells Cure Wounds and Heroism or Bless. Consider Order of Serenity at 2nd level.

**Multiclassing.** Wisdom 15 is required to multiclass into or out of the class. Proficiencies gained: simple weapons.

**Spellcasting.** You prepare a number of white mage spells equal to your Wisdom modifier + your white mage level from the white mage spell list. Wisdom is your spellcasting ability. You can cast a white mage spell as a ritual if it has the ritual tag and you have it prepared. You can use an arcane focus (an imbued natural object) as a spellcasting focus for your white mage spells.

**White Magic Order.** At 2nd level choose an Order: Turmoil, Serenity, Sacrifice, or the Lily. You gain features at 2nd, 6th, 10th, and 14th level.

*Homebrew by ArchiverButcher (Final Fantasy job conversion).*""")

def it(name): return f"Compendium.dnd5e.items.Item.{SRD['items|' + name]['id']}"
lvl_grants = {1: [f_wm, f_benison], 3: [f_orison], 5: [f_renum], 7: [f_solace], 11: [f_invig], 17: [f_liturgy], 20: [f_devout]}
adv = [
    {"_id": ID("a:hp"), "type": "HitPoints", "configuration": {}, "value": {}, "title": "Hit Points", "icon": "systems/dnd5e/icons/svg/hit-points.svg"},
    {"_id": ID("a:weap"), "type": "Trait", "level": 1, "title": "", "classRestriction": "", "configuration": {"mode": "default", "allowReplacements": False, "grants": ["weapon:sim"], "choices": []}, "value": {"chosen": []}},
    {"_id": ID("a:saves"), "type": "Trait", "level": 1, "title": "", "classRestriction": "primary", "configuration": {"mode": "default", "allowReplacements": False, "grants": ["saves:wis", "saves:cha"], "choices": []}, "value": {"chosen": []}},
    {"_id": ID("a:skills"), "type": "Trait", "level": 1, "title": "", "classRestriction": "primary", "configuration": {"mode": "default", "allowReplacements": False, "grants": [],
        "choices": [{"count": 2, "pool": ["skills:ani", "skills:his", "skills:ins", "skills:med", "skills:nat", "skills:prc", "skills:rel"]}]}, "value": {"chosen": []}},
    {"_id": ID("a:cantrips"), "type": "ScaleValue", "title": "Cantrips Known", "configuration": {"identifier": "cantrips-known", "type": "number", "distance": {"units": ""},
        "scale": {"1": {"value": 2}, "4": {"value": 3}, "11": {"value": 4}}}, "value": {}},
    {"_id": ID("a:wmdie"), "type": "ScaleValue", "title": "White Mana Die", "configuration": {"identifier": "white-mana-die", "type": "dice", "distance": {"units": ""},
        "scale": {"1": {"number": 1, "faces": 6, "modifiers": []}}}, "value": {}},
    {"_id": ID("a:sub"), "type": "Subclass", "level": 2, "title": "White Magic Order", "configuration": {}, "value": {}},
]
for lvl, items in lvl_grants.items(): adv.append(grant(lvl, items))
adv.append({"_id": ID("a:glare"), "type": "ItemGrant", "level": 5, "title": "Renumeration: Glare", "hint": "",
            "configuration": {"items": [{"uuid": s_glare, "optional": True}], "optional": True,
                              "spell": {"ability": ["wis"], "preparation": "always", "uses": {"max": "", "per": "", "requireSlot": False}}}, "value": {}})
for l in (4, 8, 12, 16, 19):
    adv.append({"_id": ID(f"a:asi{l}"), "type": "AbilityScoreImprovement", "level": l, "title": "Ability Score Improvement",
                "configuration": {"points": 2, "fixed": {k: 0 for k in ("str", "dex", "con", "int", "wis", "cha")}, "cap": 2, "locked": []}, "value": {}})

def eq(key, typ, k=None, group="", count=None, sort=0):
    return {"_id": ID("eq:" + key), "type": typ, "key": k, "group": group, "count": count, "sort": sort, "requiresProficiency": False}
g1, g2_, g3 = ID("eq:g1"), ID("eq:g2"), ID("eq:g3")
start = [eq("g1", "AND", sort=1), eq("dagger", "linked", it("Dagger"), g1, sort=2), eq("staff", "linked", it("Quarterstaff"), g1, sort=3),
         eq("g2", "OR", sort=4), eq("pouch", "linked", it("Component Pouch"), g2_, sort=5), eq("focus", "focus", "arcane", g2_, sort=6),
         eq("g3", "OR", sort=7), eq("schol", "linked", it("Scholar's Pack"), g3, sort=8), eq("expl", "linked", it("Explorer's Pack"), g3, sort=9)]
for e in start:
    if e["key"] is None: e.pop("key")

CLASS_ID = ID("class:white-mage")
docs.append(("items", {"_id": CLASS_ID, "name": "White Mage", "type": "class", "img": "icons/magic/holy/prayer-hands-glowing-yellow-white.webp",
    "system": {"description": {"value": CLASS_DESC, "chat": ""}, "source": SRC, "identifier": "white-mage", "levels": 1, "hitDice": "d6", "hitDiceUsed": 0,
               "advancement": adv, "spellcasting": {"progression": "full", "ability": "wis", "preparation": {"formula": f"@abilities.wis.mod + {CLS}"}},
               "startingEquipment": start, "wealth": "", "primaryAbility": {"value": ["wis"], "all": True}, "properties": []},
    "effects": [], "flags": {}, "folder": None, "sort": 0, "ownership": {"default": 0}}))

# ================= SPELL LIST (journal) =================
LIST = {0: "Aero|Blade Ward|Control Flames|Dancing Lights|Friends|Glare|Guidance|Light|Mending|Message|Minor Illusion|Mold Earth|Prestidigitation|Resistance|Shape Water|Spare the Dying",
 1: "Absorb Elements|Alarm|Animal Friendship|Bane|Bless|Cause Fear|Charm Person|Command|Create or Destroy Water|Cure Wounds|Detect Evil and Good|Detect Magic|Ensnaring Strike|Expeditious Retreat|Feather Fall|Fog Cloud|Goodberry|Healing Word|Heroism|Protection from Evil and Good|Sanctuary|Shield|Snare|Stone's Endurance",
 2: "Aid|Air Bubble|Barkskin|Blindness/Deafness|Blur|Calm Emotions|Darkness|Earthbind|Enhance Ability|Enlarge/Reduce|Gentle Repose|Healing Spirit|Hold Person|Lesser Restoration|Misty Step|Prayer of Healing|Silence|Summon Beast|Warding Bond",
 3: "Ashardalon's Stride|Aura of Vitality|Beacon of Hope|Counterspell|Create Food and Water|Dispel Magic|Erupting Earth|Fear|Haste|Life Transference|Major Image|Mass Healing Word|Plant Growth|Revivify|Slow|Summon Fey|Tiny Servant|Water Breathing|Water Walk|Wind Wall",
 4: "Aura of Life|Aura of Purity|Banishment|Conjure Woodland Beings|Control Water|Death Ward|Dimension Door|Elemental Bane|Guardian of Nature|Hallucinatory Terrain|Locate Creature|Otiluke's Resilient Sphere|Stoneskin|Summon Elemental|Watery Sphere",
 5: "Commune with Nature|Contact Other Plane|Control Winds|Dawn|Dispel Evil and Good|Dream|Enervation|Far Step|Greater Restoration|Hold Monster|Mass Cure Wounds|Scrying|Skill Empowerment|Teleportation Circle",
 6: "Arcane Gate|Contingency|Druid Grove|Find the Path|Guards and Wards|Heal|Heroes' Feast|Move Earth|Transport via Plants|Wind Walk|Word of Recall",
 7: "Crown of Stars|Etherealness|Forcecage|Plane Shift|Project Image|Regenerate|Ressurection|Teleport",
 8: "Antimagic Field|Control Weather|Earthquake|Holy Aura|Maze|Power Word: Stun|Telepathy",
 9: "Foresight|Gate|Mass Heal|Power Word: Heal|Time Stop|True Ressurection"}
custom = {"Glare": s_glare, "Aero": s_aero, "Stone's Endurance": s_stone}
linked, unlinked = [], []
for lvl, names in LIST.items():
    for n in names.split("|"):
        u = custom.get(n) or srd_spell(n)
        if u: linked.append(u)
        else: unlinked.append({"_id": ID("ul:" + n), "identifier": re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-"), "name": n, "system": {"level": lvl, "school": ""}, "source": {"book": "", "page": "", "custom": "", "uuid": ""}})
J, P = ID("journal:wm"), ID("page:wm-spells")
docs.append(("journal", {"_id": J, "name": "White Mage", "pages": [P], "folder": None, "sort": 0, "ownership": {"default": 0}, "flags": {}, "categories": []}))
docs.append(("journal.pages", {"_id": P, "_parent": J, "name": "White Mage Spell List", "type": "spells", "title": {"show": True, "level": 1},
    "system": {"type": "class", "identifier": "white-mage", "grouping": "level", "description": {"value": "<p>Spells available to the White Mage. Spells not in the SRD are listed without a link; drag in your own copies.</p>"},
               "spells": linked, "unlinkedSpells": unlinked},
    "text": {"format": 1}, "sort": 0, "ownership": {"default": -1}, "flags": {}}))

json.dump({"docs": docs, "spellListUuid": f"Compendium.{MOD}.white-mage-journal.JournalEntry.{J}.JournalEntryPage.{P}",
           "linked": len(linked), "unlinked": [u["name"] for u in unlinked]}, open(OUT, "w"))
print("docs", len(docs), "linked", len(linked), "unlinked", len(unlinked))
