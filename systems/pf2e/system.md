# System Module — PF2e-compatible (ORC)

This file is loaded alongside `SKILL.md` at session start. It defines the mechanical rules, character structure, and dice conventions for the Pathfinder Second Edition remaster rules released under the ORC License. Everything here is specific to this system — generic GM principles are in `SKILL.md`.

Source: *Pathfinder Player Core* remaster material, ORC licensed. See NOTICE.

**On naming.** The directory and the `**System Module:**` value are `pf2e`; the display label is "PF2e-compatible (ORC)". The *Pathfinder* wordmark belongs to Paizo and is not used as this module's name. The rules below are the ORC-licensed mechanics, which are free to use and adapt.

---

## Dice Convention

**Core resolution:** `d20 + modifier` vs a Difficulty Class (DC). The modifier is `ability modifier + proficiency bonus + item/circumstance/status bonuses − penalties`.

**Four degrees of success.** This is the single most important difference from d20 systems that only pass or fail. Always resolve to a degree, and narrate the degree:

| Degree | Condition |
|--------|-----------|
| Critical success | Beat the DC by 10 or more |
| Success | Meet or beat the DC |
| Failure | Miss the DC |
| Critical failure | Miss the DC by 10 or more |

A **natural 20 improves the degree by one step**; a **natural 1 worsens it by one step**. So a natural 20 that only meets the DC is a critical success, and a natural 20 that misses by 15 is still only a failure. A natural 1 on a roll that beat the DC by 10 lands on an ordinary success.

**Narrate the degree, not just the outcome.** A critical success should feel materially different from a success — more ground gained, an extra beat of advantage, a detail revealed. A critical failure is a real setback, not a louder miss. If every degree reads the same in the prose, the system's defining mechanic is invisible to the table.

- Damage: dice per weapon/spell, plus the relevant modifier. A **critical hit doubles the total damage** (roll normally, then double), rather than doubling only the dice.
- There is no advantage/disadvantage. Favourable and unfavourable circumstances are **numeric bonuses and penalties** of three kinds — circumstance, status and item — and **two bonuses of the same kind do not stack; take the highest**. Penalties of the same kind likewise take the worst, except untyped penalties, which do stack.

Example inline combat narration:
`Kyra Strikes the hobgoblin: d20+9 = 23 vs AC 18 — success by 5, a hit. 1d8+4 = 9 slashing.`
`Valeros Strikes again: d20+4 (−5 multiple attack) = 24 vs AC 18 — beat it by 6, still a hit. 1d8+4 = 11 slashing.`

---

## Ability Scores / Statistics

Six attributes: **STR, DEX, CON, INT, WIS, CHA**

**The remaster works in attribute MODIFIERS directly.** There are no 3–18 scores to convert. A character sheet stores the modifier itself, typically in the range −1 to +4 at level 1 and up to +7 at high level. There is no `floor((score − 10) / 2)` step anywhere in this system — if you find yourself deriving a modifier from a score, you are playing a different game.

This matters for the display: `systems/pf2e/ui.json` sets `show_modifier: false` on the attribute grid, because the number shown *is* the modifier.

**Proficiency** replaces a single proficiency bonus. Each statistic has a rank:

| Rank | Bonus |
|------|-------|
| Untrained | +0 (does not add level) |
| Trained | level + 2 |
| Expert | level + 4 |
| Master | level + 6 |
| Legendary | level + 8 |

Untrained adds **nothing at all**, not even level. Every other rank adds the character's level on top of the rank bonus, which is why a level-10 Expert (+14) is far ahead of a level-10 Trained (+12) and why an untrained character falls behind fast.

**Saving throws:** Fortitude, Reflex, Will.

**Perception is its own statistic**, not a skill, and it drives initiative in most encounters. A character has a Perception proficiency rank like any other statistic.

**Class DC** is the DC enemies roll against for some class abilities: `10 + key attribute modifier + proficiency`.

---

## Character Structure

A character carries:

- **Ancestry** (and optionally a heritage) — grants attribute boosts, HP, size, speed, ancestry feats
- **Background** — two attribute boosts, a skill, a Lore skill, a skill feat
- **Class** — the key attribute, class DC, HP per level, proficiencies, class feats
- **Level** 1–20
- **Attribute modifiers** (see above), with **four boosts at levels 5, 10, 15 and 20**
- **Skill proficiency ranks** across the 17 skills
- **Feats** in four streams: ancestry, class, skill, and general
- **Hit Points** — ancestry HP + (class HP + CON modifier) per level
- **Armor Class** — `10 + DEX modifier (capped by armor) + proficiency + item bonus`
- **Hero Points** and, for some classes, **Focus Points**

**Attribute boosts at level 1** come from ancestry, background, class key attribute, and four free boosts. A boost raises a modifier by 1, except that a modifier already at +4 or higher rises by only 1 per *two* boosts — this is the "partial boost" rule. The practical ceiling at level 1 is +4.

---

## Health and Damage

- Single HP pool. Damage subtracts; healing adds, never above maximum.
- **Temporary HP** does not stack — a new grant replaces the old one if higher.
- **0 HP:** the character falls unconscious and gains the **dying 1** condition (dying 2 if the blow was a critical hit, or if they were already wounded — see below).
- Damage types matter: physical (bludgeoning/piercing/slashing), energy, alignment-adjacent, mental, poison, bleed. **Resistance** subtracts a flat value; **weakness** adds one; **immunity** ignores the damage entirely.
- **Persistent damage** recurs at the end of the character's turn, then allows a DC 15 flat check to end it.

---

## Primary Resource

**Resource name:** Focus Points (and spell slots for prepared/spontaneous casters)

- **Focus Points** power focus spells. Most characters with any focus spells have a pool of 1–3. **Refocus** is a 10-minute activity that recovers one point. Track as current/max.
- **Spell slots** work by rank (1st–10th), prepared or spontaneous depending on class. These map to the display's level-banded pip widget exactly as 5e slots do.
- **Hero Points** are the table-level resource — see Bold Play Reward.

Map Focus Points and Hero Points to the display sidebar; spell slots ride the existing `pip_levels` widget.

---

## Rests and Recovery

- **Short rest / 10 minutes:** **Refocus** recovers one Focus Point. Treat Wounds (Medicine) can heal a willing creature and remove the wounded condition on a success.
- **Long rest / 8 hours of sleep:** recover `level × CON modifier` HP (minimum `level`), regain all spell slots and Focus Points, reduce most valued conditions by 1, and remove fatigued.
- Map to `calendar.py rest short` (1 hr) and `calendar.py rest long` (8 hr). The mechanical Refocus window is 10 minutes, which is shorter than the generic short rest — narrate the ten minutes and use the short rest for time bookkeeping.
- There are **no hit dice** in this system. Recovery is the formula above, plus Medicine.

---

## Incapacitation and Death

This system does **not** use three-successes-three-failures death saves. It uses a dying track:

- **Dying 1–4**, a valued condition. At **dying 4 the character dies.**
- While dying, at the start of each of your turns make a **recovery check**: a flat check against **DC 10 + your dying value**. Critical success reduces dying by 2, success by 1, failure increases it by 1, critical failure by 2.
- Losing the dying condition leaves you **wounded 1** (or increases wounded by 1). **Wounded adds its value to your dying condition the next time you drop**, which is what makes a second knockdown in the same fight so dangerous.
- Taking damage while dying increases dying by 1, or by 2 if it was a critical hit.
- **Doomed** reduces the dying value at which you die — doomed 1 means you die at dying 3.
- Wounded is cleared by Treat Wounds or a full night's rest; doomed reduces by 1 per night.

Track with `tracker.py condition add <name> dying` and keep the value in the condition label (`dying 2`), since the value is the mechanic.

---

## Status Effects / Conditions

**Most conditions are VALUED.** "Frightened 2" is not flavour — it is a −2 status penalty to every check and DC. Always state the value when applying one, and track it, because it changes between turns.

`frightened` **decreases by 1 at the end of each of the affected creature's turns** automatically. A GM who forgets this leaves a fight permanently harder than the rules intend.

Severity classes below are the display's four: `danger`, `warn`, `info`, `buff`. They are declared in `systems/pf2e/ui.json` under the conditions widget's `class_map` — **not** in any script.

| Condition | Severity | Valued | Effect summary |
|-----------|----------|--------|----------------|
| dying | danger | yes | Unconscious, near death; recovery check each turn; dying 4 is death |
| unconscious | danger | no | −4 AC, Perception and Reflex; off-guard; prone; cannot act |
| paralyzed | danger | no | Off-guard; cannot act except mental actions |
| petrified | danger | no | A statue; cannot act or perceive |
| stunned | danger | yes | Lose that many actions; cannot act while any remain |
| confused | danger | no | Off-guard, cannot act deliberately, attacks at random |
| controlled | danger | no | Another creature dictates your actions |
| doomed | danger | yes | Your dying threshold drops by the value |
| wounded | warn | yes | Adds to dying the next time you fall |
| frightened | warn | yes | Status penalty to ALL checks and DCs; reduces by 1 each turn |
| sickened | warn | yes | Status penalty to all checks; cannot ingest anything |
| slowed | warn | yes | Lose that many actions each turn |
| clumsy | warn | yes | Status penalty to Dex-based checks and DCs, including AC and Reflex |
| enfeebled | warn | yes | Status penalty to Str-based checks and DCs |
| stupefied | warn | yes | Status penalty to Int/Wis/Cha checks; spells need a flat check |
| drained | warn | yes | Status penalty to Con checks; lose value × level HP and max HP |
| fatigued | warn | no | −1 AC and saves; no exploration activities |
| fleeing | warn | no | Must spend actions moving away from the source |
| immobilized | warn | no | Cannot use move actions |
| restrained | warn | no | Off-guard and immobilized; cannot use attack actions |
| blinded | warn | no | Cannot see; all terrain difficult; −4 to sight-based Perception DCs |
| off-guard | info | no | −2 circumstance penalty to AC |
| prone | info | no | Off-guard, −2 to attacks; Stand to clear |
| grabbed | info | no | Off-guard and immobilized; manipulate actions need a DC 5 flat check |
| concealed | info | no | Attacks against you need a DC 5 flat check |
| dazzled | info | no | Everything is concealed to you |
| deafened | info | no | Cannot hear; −2 initiative and sound-based Perception |
| fascinated | info | no | −2 Perception and skills; no hostile concentrate actions |
| encumbered | info | no | Clumsy 1 and −10 feet to all Speeds |
| hidden | buff | no | The attacker knows your space, not you: DC 11 flat check to target |
| invisible | buff | no | Undetected by sight |
| quickened | buff | no | One extra action each turn, usually restricted in use |

---

## Combat

### The three-action economy

Each combatant gets **three actions and one reaction** per round. This replaces the move/action/bonus-action split entirely, and it is the system's second defining mechanic.

- A **Strike** is one action. **Stride** (move your Speed) is one action. Raising a shield, drawing a weapon, standing from prone, opening a door, Demoralize, Recall Knowledge — each one action.
- Some activities cost two or three actions, and spells usually cost two (the old "one action to cast" is not the default here).
- **Actions never bank across rounds.** Unspent actions are lost.
- **Reactions** trigger off something else — Attack of Opportunity is *not* universal; most creatures do not have it.

**Multiple Attack Penalty (MAP).** The second attack in a round takes **−5**, the third and beyond **−10** (−4/−8 with an agile weapon). The penalty resets at the start of your next turn. This is why three Strikes is usually the wrong play and why the table should feel the choice.

Narrate action spend naturally — "two quick strikes, then a step back out of reach" — rather than reading a counter aloud. But do count: a round where a character took four actions is a rules error the table will notice.

### Initiative

Usually a **Perception** check. Some scenes call for Stealth (an ambush) or another skill — say which statistic you are rolling and why. There is no separate initiative modifier.

### Other core combat rules

- **Flanking:** two allies on opposite sides make the target **off-guard** (−2 AC). This is the system's reliable teamwork lever; prompt for it when the map allows.
- **Cover:** standard cover is a +2 circumstance bonus to AC, greater cover +4, and cover can be used for Stealth.
- **Critical hits** come from beating AC by 10 or more, *or* from a natural 20 that hits. Doubling applies to the whole damage total.
- **Difficult terrain** costs an extra 5 feet per square of movement; greater difficult terrain costs 10.

---

## Skills

Seventeen fixed skills, each governed by an attribute. **Lore** is specialisable — a character has specific Lores ("Lore (Sailing)"), not a general one.

| Skill | Attribute | | Skill | Attribute |
|-------|-----------|-|-------|-----------|
| Acrobatics | DEX | | Occultism | INT |
| Arcana | INT | | Performance | CHA |
| Athletics | STR | | Religion | WIS |
| Crafting | INT | | Society | INT |
| Deception | CHA | | Stealth | DEX |
| Diplomacy | CHA | | Survival | WIS |
| Intimidation | CHA | | Thievery | DEX |
| Lore | INT | | Medicine | WIS |
| Nature | WIS | | | |

**Skill actions are defined, not freeform.** Demoralize (Intimidation), Trip and Grapple and Shove (Athletics), Feint (Deception), Treat Wounds (Medicine), Recall Knowledge (the relevant lore skill), Create a Diversion (Deception) — each is a named action with a cost and four outcomes. Prefer naming the action a player is taking over inventing a bespoke check, because the named ones have defined critical successes and critical failures that make the degrees matter.

**Skill feats** are a separate feat stream gained at even levels, and they are what turn a Trained skill into a distinctive capability.

---

## Advancement

- Levels 1–20. **1,000 XP per level**, awarded for encounters, accomplishments and milestones rather than per-monster bookkeeping.
- A moderate-threat encounter for a party of four is worth roughly 80 XP; an accomplishment 30 XP; a full session's progress commonly lands 150–400 XP.
- Every level grants a class feat or feature; **attribute boosts at 5, 10, 15 and 20**; skill increases at even levels; ancestry feats at odd levels; general feats at 3, 7, 11, 15, 19.
- Proficiency ranks advance by class progression, not automatically — a skill increase moves one skill up one rank.

---

## Bold Play Reward

**Reward name:** Hero Point

A player may spend **one Hero Point to reroll a check** (taking the second result), or **all of their Hero Points to avoid death** — stabilising at 0 HP with the dying condition removed instead of dying.

Characters start each session with **1 Hero Point**, and the GM awards roughly **one per hour of play** for clever, brave or characterful action. Hero Points do not carry over between sessions.

**Hard mechanical trigger (the table-visible backstop for SKILL.md Standard 12).** Keep one automatic award so bold play is never unrewarded because the GM forgot: when a player character turns a **critical failure into a success**, or achieves a **critical success on a check the table did not expect to land**, award a Hero Point on the spot. Both are moments everyone at the table sees.

Record the change with `push_stats.py --player <name> --milestone "Hero Point" --delta 1` so the count on screen moves when the award happens. A Hero Point awarded but never pushed is a reward the player cannot see and will not spend.

---

## Campaign Arc Preferences

**Preferred campaign mode:** Either (improvised or imported). Published adventure paths import well, since they are already act-and-chapter shaped.

**Typical arc structure:** Dynamic for improvised play; linear or hub-and-spoke for imported adventure paths.

**Genre conventions:** This system rewards tactical teamwork and preparation. Flanking, Demoralize, Trip, Recall Knowledge before committing — a party that coordinates is doing the thing the rules reward, so give those plays visible mechanical traction. Encounter difficulty is finely tuned: a moderate encounter should cost resources, and a severe one should feel genuinely survivable only through good play. The "All Is Lost" beat often lands as a character at dying 3, or a boss escaping with what the party came for.

---

## Additional System Notes

- **The degree of success is the voice of this system.** If your narration reads the same for a success and a critical success, the table is playing a flatter game than the rules provide. This is the single highest-value habit for this module.
- **Count the three actions.** It is the most common thing to get wrong, and the easiest for a player to catch.
- **State condition values aloud.** "Frightened 2" tells the player what to subtract; "frightened" does not. And decrement it at the end of their turn.
- **Do not import 5e reflexes.** No advantage/disadvantage, no ability scores, no hit dice, no universal Attack of Opportunity, no bonus actions, no death saving throws, no proficiency bonus shared across everything. Every one of those has a different answer here.
- **Who rolls.** Under the `players` roll mode in `SKILL.md`, call for the roll and let the player roll it — never roll a PC's d20 for them. Under GM-rolls mode, roll and narrate from the result. The degree-of-success framing is the same either way; only the hand on the die changes.
- **No system-specific scripts are required** for basic play. The rules above are sufficient for the GM model to resolve standard situations. `dice.py` handles every roll this system needs. Add scripts later if a specific calculation proves unreliable in practice.
