# System Module — Cities Without Number (compatible)

This file is loaded alongside `SKILL.md` at session start. It defines the mechanical rules, character structure and dice conventions for cyberpunk play compatible with *Cities Without Number*, written from the Cities Without Number SRD (Sine Nomine Publishing), which is dedicated to the public domain under CC0 1.0. Everything here is specific to this system — generic GM principles are in `SKILL.md`.

Source: the Cities Without Number SRD, CC0 1.0. See NOTICE.

**On naming.** The directory and the `**System Module:**` value are `cwn`; the display label is "Compatible with Cities Without Number". This module is not an official product and is not affiliated with, endorsed by or licensed by Sine Nomine Publishing. It carries the SRD's rules only: the default setting, its named corporations, places and people are not in the SRD and are not here, and neither is the SRD's optional magic chapter. Build the city yourself.

---

## Rolling

Three different dice resolve almost everything, and they are not interchangeable:

| Roll | Dice | Succeeds when |
|------|------|---------------|
| Skill check | **2d6** + skill level + attribute modifier | total ≥ difficulty |
| Saving throw | **d20** | roll ≥ save target (a natural 1 always fails, a natural 20 always succeeds) |
| Attack | **d20** + attack bonus + attribute modifier + combat skill | total ≥ the target's Ranged or Melee AC |
| Initiative | **1d8** + DEX modifier | higher acts first; PCs win ties |
| Damage | weapon die + attribute modifier | — |
| Trauma Die | the weapon's Trauma Die | roll ≥ the target's Trauma Target |

**Name the die in every call.** When the table uses player-rolled dice (the `players` roll mode in `SKILL.md`, or the phone roller on the display), say which dice to roll every time — "roll 2d6 + Dex/Sneak", "roll a d20 Evasion save, you need 13", "roll 1d8 initiative". The phone roller defaults to a d20, so a skill check called as "roll Sneak" comes back on the wrong die, and a 2d6 check rolled on a d20 is a different game. Under GM-rolls mode, roll the named dice with `dice.py` and narrate from the result.

`dice.py 2d6+1 --dc 8` resolves a skill check; `dice.py d20 --vs save --dc 14 -c <campaign>` resolves a save with the natural 1 / natural 20 rule. Attacks have no natural-number rule in this system: a natural 20 that misses AC misses.

There is no advantage or disadvantage. Circumstances move a skill check by −2 to +2 at most; attack modifiers are listed under Combat. Some Foci and cyber let a character roll **3d6 and drop the lowest** (`dice.py 3d6kh2`) or **4d6 and drop the two lowest** (`dice.py 4d6kh2`) on certain checks.

Example inline combat narration:
`Vex fires the heavy pistol: d20+2 = 17 vs Ranged AC 13 — hit. 1d8+1 = 6; Trauma Die 1d6 = 6 vs TT 6 — Traumatic Hit, x3 = 18 damage.`
`The ganger swings his machete and misses Rook (Melee AC 12), but its Shock 2/AC 13 lands anyway: 2 damage.`

---

## Attributes

Six attributes, scored 3–18: **Strength, Dexterity, Constitution** (physical) and **Intelligence, Wisdom, Charisma** (mental). DEX drives initiative and both ACs; CON sets maximum System Strain; WIS caps cyber Alienation where that optional rule is used.

**The modifier curve is NOT the d20 one.** Most characters sit at +0:

| Score | 3 | 4–7 | 8–13 | 14–17 | 18 |
|-------|---|-----|------|-------|----|
| Modifier | −2 | −1 | +0 | +1 | +2 |

Bonuses from Foci and cyber cannot push a modifier above +2 or below −2 unless the source says so. A modifier applies to skill checks, attack rolls, damage rolls, Shock and the matching saving throw targets.

NPCs normally have no attributes; treat them as average when it matters.

---

## Skills

Skill levels run **level-0 to level-4**. Level-0 is ordinary professional competence; level-1 is clearly better than most; level-4 is one of the best in the world.

**Skill check:** roll **2d6 + skill level + attribute modifier** against a difficulty. The GM names the skill and attribute ("Dex/Sneak", "Int/Program"); if several fit, the player picks the best. A combination that is only marginally relevant takes −1 or −2.

- **Untrained:** a character without even level-0 in the skill takes **−1**. Some technical skills cannot be attempted untrained at all.
- **Aid:** a helper rolls their own relevant check against the same difficulty; success gives the roller **+1**. Multiple helpers still give +1 total.
- **Opposed:** both sides roll; higher wins; **PCs win ties**.
- **NPCs** roll 2d6 + their listed skill bonus at things they should be good at, +0 otherwise, −1 at things they would be bad at.

| Difficulty | Meaning |
|-----------|---------|
| 6 | Simple for a professional; anything easier needs no roll |
| 8 | A real challenge that a competent professional usually beats |
| 10 | Expert work, and even experts might fail |
| 12 | Only a master is reliable |
| 14+ | A master will probably fail |

Situational modifiers stay within −2 to +2 in total (gear mods, cyber and aid are separate). Call for a check only when failure changes the scene; on a failure the attempt fails, goes wrong, or succeeds at a cost the GM names.

| Skill | Use it for | | Skill | Use it for |
|-------|-----------|-|-------|-----------|
| Administer | bureaucracy, law, organisations | | Perform | music, acting, oratory |
| Connect | finding people, black markets, languages | | Program | computers, hacking, comms, decryption |
| Drive | vehicles and drones, basic repairs | | Punch | unarmed combat |
| Exert | running, climbing, lifting, throwing | | Shoot | ranged weapons |
| Fix | building and repairing devices | | Sneak | stealth, disguise, locks, sleight of hand |
| Heal | medicine, stabilising, cyber surgery | | Stab | melee weapons (and thrown) |
| Know | academic and scientific knowledge | | Survive | street smarts or wilderness living |
| Lead | getting people to follow | | Talk | persuasion, charm, deception |
| Notice | searching, spotting ambushes, reading people | | Trade | buying, selling, running a business |
| | | | Work | one chosen profession |

---

## Saving Throws

Roll **d20 ≥ the save target**. A natural 1 always fails; a natural 20 always succeeds. A save may carry a bonus or penalty (poisons run +4 to −4).

| Save | Resists | Target |
|------|---------|--------|
| Physical | poison, disease, exhaustion, bodily harm | 16 − level − best of STR/CON modifier |
| Evasion | explosions, traps, sudden peril | 16 − level − best of DEX/INT modifier |
| Mental | cyber hacks, drugs on the mind, psychological shock | 16 − level − best of WIS/CHA modifier |
| Luck | pure chance — artillery, collapse, a random victim | 16 − level |

So a level-1 character starts at **15** before modifiers, and every level lowers every save by 1. NPCs have one save for everything: **15 − half their hit dice, rounded down**.

---

## Character Creation

Work through these in order; the order matters (the 14 substitution has to happen before Edges, and the Underdog Rule reads the final modifiers).

1. **Attributes.** Roll 3d6 in order for each. Before choosing Edges you may replace one rolled score with a 14. *Or* assign the array 14, 12, 11, 10, 9, 7 as you like — the array gets no 14 substitution.
2. **Background.** Take its **free skill at level-0**. Then either **roll three times**, split between the background's Growth (d6) and Learning (d8) tables however you like, **or pick two** entries from Learning (the same one twice raises it to level-1; "Any Skill" cannot be picked, only rolled). "Any Combat" is Shoot, Stab or Punch. A rolled "+2 Physical" may go on one physical attribute or split +1/+1 across two; "+2 Mental" likewise; "+1 Any Stat" goes anywhere. No attribute exceeds 18. A new background may borrow the closest table with GM approval.
3. **Edges.** Pick **two** (list below). A character whose attribute modifiers total **−1 or less** at the end of creation may take a **bonus Edge** under the Underdog Rule — but then can never buy attribute increases with skill points, and cannot take Prodigy.
4. **Foci.** Pick **one** Focus, **plus one more for each time the Focused Edge was taken** (Focused may be taken more than once). A Focus picked once gives its level 1; picking the same Focus again gives level 2 on top. A Focus that grants a bonus skill counts as an ordinary skill pick here.
5. **Free skill.** Pick any one non-magical skill: level-0, or level-1 if already level-0.
   **Skill picks stack:** the first time a skill is picked or granted it is level-0, the second time level-1; a third or later pick becomes any other skill not already at level-1. **No skill starts above level-1.**
6. **Hit points:** 1d6 + CON modifier, minimum 1 (Hard To Kill: +2 to the roll).
7. **Attack bonus:** +0 (On Target: +1). **Saves:** 15 minus the best relevant modifier, Luck 15.
8. **Contacts:** two acquaintances or one friend — capable mid-level people (a street doc, an arms dealer, a club owner), each with a name, a job and a sentence on how you know them. Acquaintances deal honestly and do small favours; friends take real risks for you. Contacts do not come on missions.
9. **Languages:** the city's common tongue plus your native one; Know or Connect at level-0 adds one more each, level-1 two each.
10. **Gear:** $500 of equipment plus one item costing up to $1,000, and one month of a middle-class lifestyle paid.
11. **Name and goal:** a goal that explains why this person takes dangerous jobs and runs with this crew. Justifying the party is the player's job, not the GM's.

### Backgrounds

Growth (d6) is nearly uniform: 1 is +1 Any Stat; 2–4 are the attribute bonuses shown; 5 is the skill shown; 6 is Any Skill. Learning is d8, in order.

| Background | Free skill | Growth 2–4, 5 | Learning (d8) |
|-----------|-----------|---------------|---------------|
| Bum | Survive | +2P, +2P, +2M; Survive | Any Combat, Survive, Connect, Sneak, Notice, Talk, Fix, Trade |
| Bureaucrat | Administer | +2M, +2M, +2M; Administer | Administer, Know, Talk, Program, Lead, Trade, Notice, Any Skill |
| Clergy | Lead | +2M, +2M, +2M; Connect | Lead, Talk, Connect, Perform, Know, Heal, Notice, Any Skill |
| Coder | Program | +2M, +2M, +2M; Program | Program, Administer, Fix, Talk, Connect, Know, Notice, Any Skill |
| Corp Security | Any Combat | +2P, +2P, +2P; Any Combat | Any Combat, Administer, Connect, Notice, Exert, Heal, Sneak, Lead |
| Corper | Work | +1 Any, +2P, +2M; Any Skill | Work, Talk, Connect, Any Combat, Notice, Sneak, Fix, Any Skill |
| Criminal | Sneak | +1 Any, +2P, +2M; Sneak | Any Combat, Sneak, Notice, Connect, Talk, Survive, Exert, Lead |
| Doctor | Heal | +2P, +2M, +2M; Heal | Heal, Notice, Know, Talk, Administer, Connect, Fix, Any Skill |
| Drone Jockey | Drive | +2P, +2P, +2M; Drive | Drive, Fix, Shoot, Notice, Sneak, Exert, Program, Any Skill |
| Ganger | Any Combat | +2P, +2P, +2M; Any Combat | Any Combat, Connect, Survive, Notice, Sneak, Talk, Fix, Any Skill |
| Laborer | Exert | +2P, +2P, +2P; Exert | Exert, Work, Sneak, Trade, Survive, Fix, Any Combat, Any Skill |
| Law Enforcement | Administer | +2P, +2P, +2M; Administer | Administer, Any Combat, Notice, Sneak, Talk, Connect, Heal, Any Skill |
| Manager | Administer | +2M, +2M, +2M; Administer | Administer, Talk, Trade, Connect, Notice, Lead, Program, Any Skill |
| Outlander | Survive | +2M, +2P, +2P; Survive | Survive, Drive, Fix, Trade, Sneak, Connect, Any Combat, Any Skill |
| Performer | Perform | +1 Any, +2M, +2P; Perform | Perform, Lead, Connect, Talk, Trade, Sneak, Any Combat, Any Skill |
| Soldier | Any Combat | +2M, +2P, +2P; Any Combat | Any Combat, Exert, Lead, Notice, Survive, Heal, Administer, Any Skill |
| Spy | Sneak | +1 Any, +2M, +2P; Sneak | Sneak, Notice, Talk, Connect, Program, Exert, Any Combat, Any Skill |
| Streetwalker | Talk | +1 Any, +2P, +2M; Talk | Talk, Perform, Connect, Trade, Sneak, Notice, Heal, Any Skill |
| Technician | Fix | +2P, +2M, +2M; Fix | Fix, Program, Exert, Trade, Notice, Connect, Drive, Any Skill |
| Trader | Trade | +2M, +2M, +2P; Trade | Trade, Notice, Connect, Fix, Talk, Administer, Any Combat, Any Skill |

(Corper's Growth 5 is also Any Skill.)

### Edges

An Edge is taken once unless it says otherwise. Two at creation; a **third at level 5**, retroactive to level 1.

| Edge | In short |
|------|----------|
| Educated | A bonus skill; +1 skill point every level-up |
| Face | Connect as a bonus skill; once a game week, conjure a temporary acquaintance Contact |
| Focused | One extra Focus pick at creation; may be taken more than once |
| Ghost | Sneak as a bonus skill; Fighting Withdrawal is On Turn; once a scene reroll a failed sneaking check; once a day move 10 m unseen |
| Hacker | Program as a bonus skill; may start with a Cranial Jack, a scrap deck and eight program elements; a **bonus Main Action each round for hacking only** |
| Hard To Kill | Hit points roll 1d6+2 per level; base Trauma Target 7 instead of 6 |
| Killing Blow | A combat skill; +1 damage per two levels (rounded up) on every source of HP damage, Shock included; +1 to Trauma Die rolls |
| Masterful Expertise | Once a scene, Instant: reroll a failed non-combat skill check |
| On Target | A combat skill; base attack bonus equals full level instead of half |
| Operator's Fortune | Once a session, Instant, when something bad befalls you this round: 1d6 — 1 no help, 2–5 averted, 6 it lands on an enemy instead |
| Prodigy | One attribute other than CON becomes 18 with a +3 modifier; not with the Underdog Rule |
| Veteran's Luck | Once a scene, Instant: an attack that hit you misses, or your attack that missed hits |
| Voice of the People | Both levels of Pop Idol and an extra friend Contact tied to your art |
| Wired | Start with up to $200,000 of cyber, installed and maintained for two months; secondhand cyber rolls for defects |

### Foci

Each has two levels unless marked (1). Most grant a bonus skill at level 1.

| Focus | Level 1 in short | Level 2 in short |
|-------|------------------|------------------|
| Ace Driver | Drive; vehicles from a level budget; reroll a failed driving check once a scene | Fix; +1 vehicle Speed; one free personal mod per vehicle |
| Alert | Notice; cannot be surprised or executed; the group rolls initiative twice, takes the better | Always act first in the round unless another Alert is present |
| All Natural (1) | Any skill; +1 to an attribute modifier (again at 3/5/7/10, to +3); no major injuries; no cyber beyond zero-strain cosmetics | — |
| Armsmaster | Stab; Ready a melee/thrown weapon as Instant; add Stab level to damage and Shock | Melee Shock treats targets as AC 10; +1 to hit melee and thrown |
| Assassin | Sneak; conceal a knife or pistol past anything short of a strip search; point-blank shots from surprise cannot miss | Move and Execution Attack in the same round |
| Authority | Lead; once a day a non-hostile NPC obeys a reasonable request on Cha/Lead vs their Morale | Followers gain Lead skill to Morale and hit, +1 to checks |
| Close Combatant | Any combat skill; pistols in melee without penalty; ignore melee Shock | Your melee Shock treats targets as AC 10; Fighting Withdrawal is On Turn |
| Cyberdoc | Fix and Heal; a cyberdoc kit; implant at Heal-0; +2 to implant surgery; your maintenance cuts a patient's strain by 1 | Strain cut is 2; installs never fail; one free mod per patient |
| Deadeye | Shoot; Ready a ranged weapon as Instant; rifles in melee at −4; add Shoot level to ranged damage | Reload On Turn; any ranged weapon in melee; once a scene auto-hit an object |
| Diplomat | Talk; every common city language; reroll 1s on negotiation checks | Once a session shift an NPC's reaction one step friendlier |
| Drone Pilot | Drive and Fix; a Remote Control Unit; drones from a level budget, rebuilt in a week | Assume Command On Turn once a round; a bonus drone Main Action once a scene; your drones +2 to hit |
| Expert Programmer | Program; level+2 extra program elements; once a day rewrite one Subject on the fly | Elements take half Memory; your deck gets CPU equal to your Program level |
| Healer | Heal; stabilise as On Turn; Heal checks roll 3d6 drop lowest | Healing drugs and devices heal double; ten minutes heals the group 1d6+Heal with no strain, once a day each |
| Henchkeeper | Lead; recruit loyal non-combat henchmen, one per three levels | Henchmen fight, treated as basic corp security |
| Many Faces (1) | Sneak; one solid false identity per three levels | — |
| Pop Idol | Perform; once a week mobilise about a hundred fans for a mild favour or donations | A hundred fans per level, deniable fan leaders, more money, +1 CHA modifier |
| Roamer | Survive and Drive; every regional language; never lost; vehicles from a level budget | Reroll a failed travel or vehicle check once a scene |
| Safe Haven | Sneak; a week's work finds a safe house and an on-call medic; one house per level | Locals protect your houses; houses with workshops or clinics |
| Shocking Assault | Punch or Stab; your weapon's Shock treats targets as AC 10 | +2 Shock on melee and unarmed attacks |
| Sniper's Eye | Shoot; ranged Execution Attack checks roll 3d6 drop lowest | Never miss a ranged Execution Attack; target saves at −4 and takes double damage even on a success |
| Specialist | A non-combat skill; checks in it roll 3d6 drop lowest; may be taken for several skills | 4d6 drop the two lowest |
| Tinker | Fix; double Maintenance score; mods cost half | Fix counts one level higher for mods; advanced mods need one fewer component |
| Unarmed Combatant | Punch; unarmed damage scales 1d6 → 1d12+1 with Punch level; Shock at Punch-1+; lethal blows Trauma 1d6/x2 | A missed punch still deals 1d6; Trauma Die 1d8 |
| Unique Gift (1) | A distinctive ability or experimental cyber, agreed with the GM, worth about a Focus | — |
| Unregistered (1) | No database record of you exists, and none will stay | — |
| Whirlwind Assault | Stab or Punch; once a scene apply your Shock to every foe in melee | Killing a foe grants an immediate extra attack, once a round |

At levels 2, 5, 7 and 10 a character adds a level to a Focus or takes a new one. Taken by advancement rather than at creation, a Focus's bonus skill is worth **three skill points** toward that skill instead of a pick — enough for level-0 to level-1, or level-1 to level-2, regardless of character level; points short of the next level stay as credit, and points that would push past level-4 go to another skill.

---

## Combat

### Sequence and initiative

The SRD's default is **side initiative**: each side rolls **1d8 + its best DEX modifier** (NPCs usually add nothing); sides act highest first and **PCs win ties**; within its turn a side acts in any order it agrees. Initiative is rolled once and the order repeats every round. Rounds are about six seconds.

**Individual initiative** is the SRD's optional rule: each combatant rolls **1d8 + their own DEX modifier**, PCs winning ties. `combat.py init '<JSON>' -c <campaign>` rolls this form — give each combatant `"dex_mod"` and `"type": "pc"` or `"npc"`. For side initiative, roll one 1d8 per side with `dice.py 1d8+<best mod>`.

- **Surprise:** a side caught completely unaware gives its enemies a free round first (often an opposed Dex/Sneak vs Wis/Notice). A side expecting trouble cannot be surprised.
- A combatant with an automatic-initiative power acts first regardless; several such roll among themselves.
- NPCs that take losses may check **Morale** (below). **PCs never check Morale.**

### Actions

Each round: **one Main action**, **one Move action** (or trade the Main for a second Move), any plausible **On Turn** actions, and **Instant** actions — usable even off-turn and after dice are rolled — where a power grants them.

| Action | Type | Effect |
|--------|------|--------|
| Melee or ranged attack | Main | Roll to hit; one-handed guns and thrown at −4 with an enemy in melee; rifles cannot fire in melee |
| Snap Attack | Instant | Spend an unused Main to attack at −4, even off-turn |
| Swarm Attack | Main | Up to four allies set up one attack: +2 hit/+1 damage per other assailant (max +6/+3); its Shock always applies |
| Charge | Main + Move | Double move in a line (3 m minimum), then attack at +2; −2 to your ACs until round end |
| Screen an Ally | Move | Attackers on your ward must beat you in an opposed combat-skill check |
| Total Defense | Instant | Spend an unused Main: +2 to both ACs and immune to Shock until your next turn |
| Run | Move | 10 m; leaving an adjacent melee foe provokes a free attack |
| Fighting Withdrawal | Main | Disengage without the free attack |
| Use a Skill / Ready or Stow / Reload | Main | First aid, triggering a hack, drawing a Stowed item, a fresh magazine |
| Go Prone | On Turn | −2 to ranged attacks against you, +2 to melee attacks against you, half speed |
| Hold an Action | Move | Act later in the round as an Instant; a held action resolves first |

### Attacks

**d20 + base attack bonus + the weapon's attribute modifier + combat skill level** (Shoot, Stab or Punch) against the target's **Ranged AC or Melee AC** — characters have both, set by armour and always adjusted by DEX. No combat skill at all: **−2**. Base attack bonus is **half level, rounded down** (On Target: full level). NPC attack bonus is usually their hit dice plus a little for training.

| Situation | Mod |
|-----------|-----|
| Shooting a distant prone target | −2 |
| Attacking an adjacent prone target | +2 |
| Melee attacking while prone | −4 |
| Beyond the gun's normal range | −2 |
| Target half behind cover / almost fully covered | −2 / −4 |
| Thrown or one-handed gun while in melee | −4 |
| Target unseen, position known | −4 |
| Dual-wielding (needs level-1 in both skills; +2 damage in reach of both) | −1 |

**There is no critical hit and no automatic hit or miss on an attack.** The big hit is the Trauma Die.

### Damage, Trauma and Shock

- **Hit:** weapon damage die + attribute modifier. Armour with **Damage Soak** absorbs damage first; soak is used up for the fight and refreshes afterwards.
- **Trauma Die:** on a hit with a lethal attack, roll the weapon's Trauma Die. If it **meets or beats the target's Trauma Target** — **6** for an unarmoured human, raised by armour, cyber and Hard To Kill — it is a **Traumatic Hit**, and the whole damage is **multiplied by the weapon's Trauma Rating** (x2, x3, x4). A Traumatic Hit also exposes the target to a Major Injury if they drop to 0 HP later in the same scene. Roll it with the damage. Non-lethal attacks never roll it, and Shock cannot cause it.
- **Shock** (melee weapons, written "Shock 2/AC 13"): on a **miss** against a target whose Melee AC is at or below the listed AC, the target takes that damage anyway. Only the attribute modifier and bonuses that explicitly say so add to Shock. A hit never deals less than the Shock would have. A riot shield ignores the first Shock each round; Total Defense ignores all of it. "Shock 5/–" applies at any AC.
- **Execution Attack:** against a wholly unsuspecting target after a minute of setup. Ranged: a Dex/Shoot check (6 within 2 m, 8 at normal range, 10 at long range) that ignores AC. Melee: an automatic hit. The target makes a Physical save at a penalty equal to the attacker's combat skill or drops to 0 HP and Mortally Wounded; either way the hit counts as Traumatic.
- **Shove / grapple:** a hit (unarmed and two hands free to grapple) that deals no damage and forces an opposed Str/Exert or Str/Punch check.

`combat.py attack --atk <bonus> --ac <AC> --dmg 1d8+1 -c <campaign>` resolves the roll; add `--trauma 1d6/x3 --tt <target>` to roll the Trauma Die on a hit, and `--shock 2/13` to apply Shock on a miss. `--crit` marks the hit as Traumatic, for an Execution Attack.

| Sample weapon | Dmg | Trauma | Shock | Notes |
|---------------|-----|--------|-------|-------|
| Unarmed | 1d2 + Punch | 1d6/x1 | — | Punch adds to unarmed damage only |
| Knife | 1d4 | 1d6/x3 | 1/AC 15 | Str or Dex; throwable |
| Sword | 1d8 | 1d8/x2 | 2/AC 13 | Str or Dex |
| Light pistol | 1d6 | 1d8/x2 | — | 15-round mag |
| Heavy pistol | 1d8 | 1d6/x3 | — | 8-round mag |
| Shotgun | 3d4 | 1d10/x3 | — | 10/30 m |
| Rifle | 1d10+2 | 1d8/x3 | — | 200/400 m |
| Combat rifle | 1d12 | 1d8/x3 | — | burst fire: three rounds for +2 hit and damage |

| Sample armour | Ranged AC | Melee AC | Soak | Trauma Target | Notes |
|---------------|-----------|----------|------|---------------|-------|
| Ordinary clothing | 10 | 10 | 0 | +0 | |
| Street leathers | 13 | 12 | 3 | +0 | subtle |
| Armored clothing | 16 | 14 | 5 | +1 | subtle |
| Light armored suit | 16 | 13 | 5 | +2 | obvious; needs a Contact |
| Heavy armored suit | 20 | 18 | 15 | +3 | obvious; −1 to Sneak and Exert |

### NPCs, Morale and reactions

An NPC stat line carries HD (hit points), both ACs, Trauma Target, a skill bonus, one save, attack bonuses, Shock, Move and Morale (2–12). Unnamed NPCs die at 0 HP.

- **Morale:** after first blood, losing more than half the group, looking likely to lose, or a shocking reverse, roll 2d6 against their Morale; a roll above it breaks them (the SRD's Morale section reads "equal or higher" — pick one for your table and keep it). ±1 or 2 for drama at most.
- **Reaction roll** on meeting someone: 2d6 + the spokesperson's CHA modifier — 2 or less as hostile as is plausible, 3–5 unfriendly, 6–8 neutral, 9–11 friendly, 12+ as helpful as is plausible.

---

## Health and Damage

- Single HP pool. **Max HP:** 1d6 + CON modifier per level, each die minimum 1; at each level-up reroll the whole pool and keep it if higher, otherwise max HP rises by 1.
- **0 HP from a lethal attack: Mortally Wounded.** Helpless, and dead at the end of the **sixth round** unless stabilised. Damage that could not plausibly be survived kills outright.
- **Stabilising:** a Main action, Dex/Heal or Int/Heal against **8 + full rounds since they fell** (+2 without a medkit). One medic tries per round; others may aid; retry every round. A trauma patch stabilises on difficulty 6 (+1 per round down) and is useless after six rounds.
- A stabilised character wakes after ten minutes at **1 HP and Frail**. **Frail:** dropping to 0 HP again while Frail is death; no natural healing. Frailty ends after a week of bed rest with care from someone with Heal-0 and a medkit, or a single hour's attempt by a physician (Dex/Int/Heal vs 10). Without care, a Physical save after a week: failure means death within the next week, success means recovery after another month.
- **Non-lethal 0 HP:** unconscious ten minutes, then 1 HP; not Frail.

### Major Injuries

Brought to 0 HP by lethal damage in a scene in which they took a **Traumatic Hit**, a character makes a **Physical save**. Pass: Mortally Wounded as usual. Fail: Mortally Wounded **and** roll d12:

| d12 | Major Injury |
|-----|-------------|
| 1 | Instant death |
| 2 | Internal damage: dead in an hour without a clinic; in a coma until Prosthetic Cyber; Body and Nerve cyber critically damaged |
| 3 | Brain damage: coma until Prosthetic Cyber; Head and Nerve cyber critically damaged |
| 4 | Eye damage: blind until cybereyes (existing cybereyes are damaged) |
| 5 | Gut wound: without a clinic within the hour, −1 CON modifier until Prosthetic Cyber |
| 6–7 | Right / left leg ruined: crawling at best (limb cyber there is damaged) |
| 8–9 | Right / left arm ruined: one working hand (limb cyber there is damaged) |
| 10 | System damage: the most strain-expensive implant is critically damaged |
| 11–12 | Just a flesh wound |

Damaged cyber is useless until repaired: a day per system, 20% of its cost, someone with Fix-0 and Heal-0 and at least a cyberdoc kit. Cloned replacement tissue is possible with top-end medical contacts and at least $100,000.

---

## System Strain

Strain is the body's running cost for unnatural healing and cyber. **Maximum System Strain equals the CON score**, adjusted by lifestyle (below). Strain can never exceed the maximum.

- **Permanent strain:** an installed implant adds its strain rating permanently (it may be fractional). Cyber that would put permanent strain over the maximum cannot be installed. Removing the implant removes its permanent strain.
- **Temporary strain:** each first-aid application adds 1; many drugs and cyber activations add some. If an addition would exceed the maximum, the cyber does not activate and the drug does nothing (its downsides still apply). Forced over the maximum by something unavoidable, the character is knocked out for at least an hour.
- **Recovery:** 1 point of accumulated strain per night of eight warm, fed, uninterrupted hours. Never below the permanent level.

Track it as `system_strain: {current, max}` on the display; current includes the permanent part.

---

## Rests and Recovery

- **Each night** of good rest and food: regain **HP equal to level** (NPCs: their hit dice) and shed **1 System Strain**. Frail characters regain no HP this way.
- **First aid:** one minute with a medkit heals **1d6 + Heal skill** (1d6−1 untrained) and adds **1 System Strain**; five minutes covers the whole team. It cannot cure Frail.
- **Poison and disease:** usually a Physical save. A medic with a medkit within a minute adds twice their Heal level to the save (+1 at Heal-0).
- Map to `calendar.py rest long` for the night; there is no short-rest mechanic, so use `calendar.py advance` for the minutes of first aid.
- A hacker's **Access** refreshes once a day with an hour of reprogramming.

---

## Cyberware

**Installing:** a surgeon with **Heal-1** or better (street docs run +2 to +5). Cost, recovery time and difficulty scale with the implant's strain:

| Strain | Surgery cost | Recovery | Difficulty |
|--------|-------------|----------|-----------|
| 0 | $100 | 1 hour | 7 |
| 0.1–0.5 | $500 | 1 day | 8 |
| 0.6–1 | $2,500 | 4 days | 10 |
| 1.1–3 | $12,500 | 2 weeks | 11 |
| 3.1+ | $50,000 | 1 month | 12 |

The doc rolls Int/Heal or Dex/Heal, −1 to +2 for tools and −1 to +2 for the room, +1 for new cyber. Fail by 3 or more: the surgery fails, strain is maxed and the patient drops to 1 HP. Fail by 1–2: it works but with a random implant complication (unreliable, inefficient, loud, fussy, bad connection, blatant, debilitating and so on). Success: installed, permanent strain added.

- **Maintenance:** 5% of base cost a month and hours of work equal to the strain (15 minutes minimum) by someone with Fix-0 or Heal-0. A month without it brings a complication until serviced.
- **Concealment:** Medical (scan or exam only), Touch (felt, not seen), Sight (visible).
- **Removal** at the install difficulty; permanent strain goes with the implant.
- **Skillplugs** give level-0 or level-1 in mental skills through a plug jack (physical skills need a better jack); a natural 2 on a plugged skill check, or a natural 1 on a plugged attack, fails outright and locks the jack for the scene.

| Sample system | Cost | Location | Concealment | Strain | Does |
|---------------|------|----------|-------------|--------|------|
| Cranial Jack | $1K | Head | Touch | 0.25 | Plugs into decks and jack-lined gear |
| Skillplug Jack I | $10K | Head | Touch | 0.25 | Runs mental skillplugs |
| Gunlink | $25K | Sensory | Touch | 1 | Ignore range and 2 points of cover; reroll a missed shot once a scene |
| Remote Control Unit | $10K | Nerve | Touch | 2 | Command drones neurally |
| Dermal Armor I | $40K | Skin | Medical | 1 | Built-in armour |
| Enhanced Reflexes I | $100K | Nerve | Medical | 2 | Once a scene, a bonus non-hacking Main action |

### Alienation and chrome syndromes (optional)

By default, cyber has no mechanical psychological cost. A table that wants one uses **Alienation**:

- Installing an implant adds **permanent Alienation equal to its strain, rounded up** (+2 more for Nerve cyber). If Alienation ever **exceeds WIS**, the character suffers cyber-induced psychosis and becomes an NPC driven by their syndromes.
- When accepting new cyber a character may take **chrome syndromes**, each of which **raises the Alienation maximum** but imposes a behaviour. Acting against a syndrome forces an **Alienation check**: d20 ≤ current Alienation adds a point; going over the maximum then calls for a Mental save — pass and take a new syndrome, fail and break.
- A week of therapy (a cyberpsychologist at about $2,000, or a PC with Talk-1 and Heal-1) removes 1 point, never below the permanent level. A psychosis victim must be subdued, stripped of non-essential cyber and treated below WIS, then make a Mental save.

| Syndrome | +Max | Effect |
|----------|------|--------|
| Brutal | +4 | No non-lethal combat |
| Candid | +3 | Answer every question with at least a sentence of truth |
| Cold | +4 | Cannot feel love; lose your closest Contact |
| Distant | +3 | −1 on social checks |
| Exultant | +3 | A natural 12 on a skill check fails |
| Fearless | +4 | −20% max HP |
| Hypervigilant | +3 | +1 permanent System Strain |
| Murderous | +6 | Must kill weekly |
| Ravenous | +4 | A sensory vice that must be fed |
| Savage | +5 | Cannot flee once hurt |
| Secretive | +3 | Cannot answer truthfully beyond the trivial |
| Stressed | +5 | −1 to your lowest attribute modifier |

---

## Drugs

Using a drug is a Main action; some need a minimum Heal level to administer. Only the highest bonus of several drugs applies. A drug whose strain would exceed the maximum gives its drawbacks without its benefit.

| Chem | Cost | Effect |
|------|------|--------|
| Lurch | $25 | Heals 1d10 + Heal on a conscious, stabilised patient; +1 strain; each extra dose that day needs one more Heal level |
| Trauma Patch | $50 | Stabilises a Mortally Wounded target on difficulty 6 (+1 per round down) |
| Avalanche | $100 | +10 effective HP for an hour; −1 on any Major Injury roll |
| Boneshaker | $10 | +2 hit, damage, Shock and Morale for a scene; attacks against you +2 Trauma Die; +2 strain after |
| Olympus | $100 | +2 to hit and a Morale reroll for a scene; +1 strain after |
| Window | $200 | Trade a Move action for a cyberspace-only Main action; +1 strain each time |
| Panacea | $200 | Doubles first-aid healing (minimum 6) |

---

## Hacking

**The loop.** Most valuable networks are wired and isolated, so a hacker usually has to get physically close: attach the deck's field cable to a device (Jack In, a Move action) or connect wirelessly within **30 m line of sight at −2**. A VR crown instead of a cranial jack is another −1. The avatar appears in that device's **node**; nodes link by connections, some hidden (Wis/Program to find), some behind **barriers** (Unlock first). Moving a node is a Move action.

**Running a program** is a Main action: pair a **Verb** with a **Subject** stored in the deck's Memory ("Glitch Camera", "Unlock Barrier", "Sabotage Cyber"), pay its **Access** (usually 1), and roll **Int/Program vs the network's security** (Cyber and Drone targets: 7 + a third of the target's level or HD, rounded up; an unpiloted drone is 8). Failure wastes the Access; **every two failed checks count as one Alert the Network**, and two alerts trigger the network's intruder response. A running program holds one CPU slot until ended. Cyber, Drone and Transmission programs fire straight at a target in range without jacking in. Hacking someone's cyber always alerts them.

**Cyberspace combat** happens between avatars and **Demons** (guardian programs with HP, a skill bonus and a short list of command lines) in the same node. Initiative as normal; actions spent in cyberspace are the same actions as in meatspace — the **Hacker Edge's bonus Main action** is what lets a hacker do both. **Stun** inflicts non-lethal damage on real HP (0 HP: unconscious ten minutes); **Kill** can deal lethal damage and Traumatic Hits. A deck's Shielding absorbs Stun/Kill damage first. Watchdogs are human hackers on the network's side, coordinating with physical security.

| Hacker stat | Source |
|------------|--------|
| **Access** | INT modifier + Program skill + the deck's Bonus Access; refreshes once a day with an hour's work |
| **Memory** | The deck's; each Verb, Subject or stolen file takes 1 |
| **CPU** | Programs running at once |
| **Shielding** | Absorbs Stun/Kill damage; refreshes after 15 calm minutes |

| Security | Difficulty |
|----------|-----------|
| Private home | 7 |
| Small business, minor gang, minor government office | 8 |
| Corp branch, major gang, important government site | 9 |
| Corp high-security network | 10 |
| Black site | 12 |

+1 if alerted, +1 for a vital device, ±1–2 for unusually poor or good tech, −1 to −3 for inside information.

Common **Verbs**: Activate, Analyze, Blind, Deactivate, Decrypt, Defend, Delude, Erase, Frisk, Glitch, Hijack, Kill, Lock, Paralyze, Replace, Sabotage, Sense, Stun, Terminate, Unlock. Common **Subjects**: Avatar, Barrier, Camera, Cyber, Datafile, Door, Drone, Machine, Program, Sensor, Transmission, Turret. A hacker with Program-1+ can write and maintain two elements per Program level; a Subject written for one exact device model gives +2. A scrap deck (Bonus Access 1, Memory 8, Shielding 5, CPU 2) is the Hacker Edge's starting deck.

Display: push `access: {current, max}`; the sidebar's Access bar appears only for characters that have it.

---

## Drones and Vehicles

**Drones.** Unpack (Main), then bring online and assume command (Main + Move). Command with the drone's **control board** (one drone, −2 to its rolls unless jacked in) or a **Remote Control Unit** (1 + Drive skill drones, a bonus drone-only Move action each round, upgraded to a Main action for 1 strain). **At least Drive-0** is needed. The pilot spends their own Move to move a drone and their own Main to fire it; the attack uses the pilot's attack bonus + the better of Drive or Program + Int or Dex (other mounted guns fire at +2). Skill checks through a drone are capped at the pilot's Drive level. Safe range 1 km; beyond it, any hack or jamming attempt against the drone succeeds automatically. One hour per battery charge. A drone at 0 HP is destroyed.

**Vehicles.** Statistics are HP, AC, Armor (subtracted from damage), Speed (added to the driver's vehicle checks), Trauma Target (never below 6), crew and hardpoints. In vehicle combat each vehicle is its own side; the driver spends a Main action every round keeping control (or makes a Luck save to stop safely instead of crashing); each mounted weapon needs a gunner; a moving vehicle adds the driver's Drive to its AC, a stationary one takes −4; firing personal weapons from a moving vehicle is −4. A destroyed vehicle hits its occupants with the same damage (Luck save for half); a crash at speed calls for Physical and Luck saves — fail one for half max HP, fail both for Mortally Wounded and a Major Injury. **Chases:** the fleeing side sets the pace with a Dex/Drive (or Dex/Exert, Con/Exert on foot) check, allies add up to +3, and pursuers must beat it (foot) or meet it (vehicles) with situational modifiers.

| Sample vehicle | Cost | Speed | Armor | TT | AC | HP | Crew |
|---------------|------|-------|-------|----|----|----|------|
| Motorcycle | $1K | 1 | 4 | 10 | 13 | 10 | 1 |
| Car | $5K | 0 | 6 | 12 | 11 | 30 | 5 |
| Truck | $7.5K | 0 | 6 | 12 | 11 | 35 | 2 |

---

## Status Effects / Conditions

Severity classes are the display's four: `danger`, `warn`, `info`, `buff`, declared in `systems/cwn/ui.json` under the conditions widget's `class_map`.

| Condition | Severity | Effect summary |
|-----------|----------|----------------|
| mortally wounded | danger | Helpless; dies at the end of the sixth round unless stabilised |
| unconscious | danger | Out — non-lethal 0 HP, strain overload, or a Stun knockout |
| coma | danger | From a Major Injury; lasts until Prosthetic Cyber is installed |
| internal damage | danger | Dead within the hour without a clinic |
| frail | warn | Next 0 HP is death; no natural healing |
| brain damage | danger | Coma until Prosthetic Cyber |
| gut wound | warn | −1 CON modifier until Prosthetic Cyber, unless treated within the hour |
| blinded | warn | Blind until cybereyes are fitted |
| leg ruined | warn | Crawling at best |
| arm ruined | warn | One working hand |
| stunned | warn | Loses the next Main action (a yanked jack) |
| poisoned | warn | As the toxin; usually a Physical save |
| psychosis | danger | Alienation over WIS: the character acts as an NPC |
| grappled | info | Cannot move; unarmed attacks only; takes the grappler's unarmed damage each round |
| prone | info | −2 to ranged attacks against you, +2 to melee attacks; half speed |
| surprised | info | Enemies take a free round |
| jacked in | info | Avatar in a node; a yanked cable stuns |
| total defense | buff | +2 both ACs, immune to Shock |
| hidden | buff | Unseen; attacks against you suffer the unseen-target penalty |

---

## Advancement

Levels 1–10. The default award is **3 XP for an average successful mission**; totals are cumulative.

| Level | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|-------|---|---|---|---|---|---|---|---|----|
| Fast campaign | 3 | 6 | 12 | 18 | 27 | 39 | 54 | 72 | 93 |
| Slow campaign | 6 | 15 | 24 | 36 | 51 | 69 | 87 | 105 | 139 |

Each level-up:

- **Hit points:** reroll 1d6 + CON modifier per level (1d6+2 with Hard To Kill), each die minimum 1; take the new total if higher, otherwise +1 max HP.
- **Saves:** every save target drops by 1.
- **Attack bonus:** half level, rounded down (On Target: full level).
- **Skill points:** **3** (Educated: 4), spend now or bank them (banked points need a teacher or an in-fiction reason when spent). Each skill level is bought in order and cannot be part-bought:

| Skill level | 0 | 1 | 2 | 3 | 4 |
|-------------|---|---|---|---|---|
| Cost | 1 | 2 | 3 | 4 | 5 |
| Minimum character level | 1 | 1 | 3 | 6 | 9 |

- **Attributes:** skill points may buy +1 to any attribute — the first boost costs 1, the second 2, and so on; **five boosts in a lifetime**, the third needing level 3, the fourth level 6, the fifth level 9. Not for Underdog Rule characters.
- **Foci** at 2, 5, 7 and 10; a **third Edge** at 5.

Track it on the display with `push_stats.py --player <name> --xp <current> <next>`.

---

## Gear and Economy

Prices are in dollars. Lifestyle is paid monthly and **moves the System Strain maximum** for as long as it is paid (or not):

| Per month | Lifestyle | Max strain |
|-----------|-----------|-----------|
| $0 | Squatting in an abandoned building | −2 |
| $300 | A dirty shared slum apartment | −1 |
| $1,000 | Middle-class rental | ±0 |
| $5,000 | Clean, secure building | +1 |
| $20,000 | Luxury | +2 |

- **Bribes** are priced in multiples of the target's daily wage: ×2 to overlook a minor infraction or leak something, ×5 for a small favour, ×14 and up for anything that could cause them trouble, ×180 for something that could get them fired.
- **Encumbrance:** Stowed items up to STR, Readied up to half STR; a one-hand item is 1, a two-hand item 2. Using a Stowed item takes a Main action to Ready it. Three small items bundle as one. A table may drop encumbrance and simply keep loads reasonable.
- **Mods** to weapons, armour, cyber, decks, drones and vehicles need Fix (and Heal for cyber), a workshop and often rare components, and each one counts against the tech's **Maintenance score** (INT mod + CON mod + 3 × Fix).

---

## Bold Play Reward

**Reward name:** none in the SRD.

The SRD defines no meta-currency for bold play. Reward it in the fiction and in XP: a Contact earned for keeping a promise, a reaction shifted a step, a lead that only exists because a player took the risk. If the table wants a visible token anyway, the display's generic milestone badge carries any label (`push_stats.py --player <name> --milestone "<label>" --delta 1`) — make it clear at the table that this is a house rule.

---

## Campaign Arc Preferences

**Preferred campaign mode:** Either. Improvised play suits the job-to-job structure; imported scenarios work as long as they are written for these rules.

**Typical arc structure:** Dynamic, built from jobs: a fixer or Contact offers work, the crew plans, infiltrates under mission time, and lives with what they did. Faction-web suits a city campaign where corporations, gangs and the authorities all keep score.

**Genre conventions:** Violence is fast and lethal — a single Traumatic Hit can end a fight, so telegraph danger and reward planning, cover and surprise. **Mission time** (minute by minute during an infiltration) is where tension comes from: the longer the crew takes, the more likely a patrol or an alert. Money is always short, lifestyle has to be paid, and cyber costs the body. The "All Is Lost" beat often lands as a betrayal by an employer, a burnt safe house, or a crew member Frail and out of options.

---

## Additional System Notes

- **Skill checks are 2d6, not d20.** It is the most common mistake: a d20 skill check makes every roll swingy and every bonus meaningless. Saves and attacks are the d20 rolls.
- **Saves are roll-over targets that go down as characters level.** A save target of 13 means "roll 13 or more on a d20". Do not add the attribute modifier to the roll — it is already in the target.
- **Do not import 5e reflexes.** No advantage/disadvantage, no critical hits on a natural 20, no proficiency bonus, no death saves (six rounds to stabilise instead), no short rests. The 3–18 scores carry a much flatter modifier: a 16 is +1, not +3.
- **The Trauma Die is the drama.** Roll it with every lethal hit and say the number against the Trauma Target out loud. Armour that raises Trauma Target is why corp security is hard to put down.
- **Two ACs.** Ask whether the attack is ranged or melee before comparing; most armour protects better against bullets than blades or the reverse.
- **Strain is the second health bar.** Healing in the field, combat drugs and cyber activations all spend it; a character at their strain maximum cannot be patched up again until they sleep. Push it to the display when it changes.
- **Name the die in every call** (see Rolling).
- **No system-specific scripts are required.** `dice.py` and `combat.py` handle the rolls; the SRD's full equipment, cyberware and program lists are longer than this summary — invent sensibly in their spirit when a player asks for something not listed here.
