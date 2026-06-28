# System Module — Basic Roleplaying (BRP)

BRP is a percentile, skill-based universal game engine by Chaosium. Genre-agnostic: horror, fantasy, sci-fi, historical, pulp, modern. Deadly and realistic in tone — success is never guaranteed and characters can die fast.

Source: *Basic Roleplaying: Universal Game Engine* (Chaosium, 2023). ORC licensed. See NOTICE.

---

## Dice Convention

**Core resolution:** Roll D100 (percentile), aim LOW. Roll ≤ skill% = success.

**Success thresholds:**

| Level    | Threshold                        | Effect |
|----------|----------------------------------|--------|
| Critical | ≤ skill ÷ 20 (round up)         | Best result; combat: max damage + ignore armor |
| Special  | ≤ skill ÷ 5 (round up)          | Great result; combat: knockdown, impale, or bleed |
| Success  | ≤ skill%                         | Normal result |
| Failure  | > skill% (max 95 always fails)   | No effect |
| Fumble   | 96–00 (or 00 only at high skill) | Worst result; roll on fumble table |

*01–05 always succeeds regardless of penalties. 96+ always fails regardless of skill.*

**Difficulty modifiers:**

| Modifier   | Effect       |
|------------|-------------|
| Easy       | skill × 2   |
| Average    | no change   |
| Difficult  | skill ÷ 2   |
| Impossible | 01% or no roll |

**Characteristic rolls:** When no skill applies, roll Characteristic × 5 (e.g. STR×5 for raw strength, INT×5 for recall, DEX×5 for reflex).

**Resistance roll:** When two forces oppose each other directly (not skill vs skill): Chance = 50% + (active × 5) − (passive × 5). Difference ≥ 10 = automatic result.

**Example inline combat narration:**
`Aelith attacks the guard: D100 = 34 vs Sword 55% — success! 1D8+1D4 DB = 7 damage`

---

## Ability Scores / Statistics

Characteristics are the core stats. Most rolled 3D6; INT and SIZ rolled 2D6+6.

| Stat | Name         | Governs |
|------|-------------|---------|
| STR  | Strength    | Melee damage, lifting, grapple |
| CON  | Constitution| Endurance, hit points, poison resistance |
| SIZ  | Size        | Mass, hit points, damage modifier |
| INT  | Intelligence| Learning, INT rank in powers, Idea roll |
| POW  | Power       | Willpower, magic, Luck roll, power points |
| DEX  | Dexterity   | Initiative, agility, Agility roll |
| CHA  | Charisma    | Social influence, Charm roll |
| EDU  | Education   | (Optional) Formal knowledge, Know roll |

---

## Character Structure

| Field | Notes |
|-------|-------|
| Hit Points (HP) | (CON + SIZ) ÷ 2 rounded up |
| Major Wound Level | HP ÷ 2 rounded up — single hits at or above this are major wounds |
| Power Points (PP) | = POW; fuel for magic, psychic abilities, superpowers |
| Damage Modifier (DB) | From STR+SIZ table: ≤8 = −1D6, 13–16 = +1D4, 17–24 = +1D6, 25–32 = +2D6 |
| Movement (MOV) | 10 meters/round (human default) |
| Sanity (SAN) | POW × 5 (optional; horror genre) |
| Skills | Six categories; rated 0–100%+ |
| Defense | Active — roll Parry or Dodge vs incoming attacks |

---

## Health and Damage

- Weapons deal listed dice + Damage Modifier (DB). Subtract from HP.
- **Major wound** (single hit ≥ Major Wound Level): victim rolls CON×5 or falls unconscious.
- **0 HP:** unconscious and dying.
- **Negative HP:** dead (typically at −CON or gamemaster's discretion).
- **Healing:** First Aid skill can stabilise; Medicine for surgery; natural recovery 1D3 HP/week.

**Hit Locations (optional, D20):** 1–4 Right Leg | 5–8 Left Leg | 9–11 Abdomen | 12 Chest | 13–15 Right Arm | 16–18 Left Arm | 19–20 Head. Each location has its own HP pool (~HP÷3 for limbs/head; ~HP×0.4 for chest).

---

## Primary Resource

**Resource name:** Power Points (PP)
**Range:** 0 to POW (typically 3–18)
**Tracking:** Spent on spells, psychic abilities, superpowers, and certain resistance rolls. Recovered at rest — roughly 1 PP per hour of rest, fully restored after a night's sleep. Map to display sidebar as PP current/max.

*Sanity (SAN)* is a secondary resource in horror campaigns: POW×5 starting total; lost on witnessing horrors; restored slowly through roleplay and recovery.

---

## Rests and Recovery

- **Short rest (1 hour):** First Aid roll to recover 1D3 HP; PP recovery begins.
- **Long rest (8 hours):** Natural healing 1 HP; PP fully restored.
- **Weeks of rest:** 1D3 HP per week for serious wounds.
- **First Aid:** Successful roll immediately stabilises a dying character (stops HP loss); can be attempted once per wound.
- Map to `calendar.py rest short` (1 hr) and `calendar.py rest long` (8 hr).

---

## Incapacitation and Death

- **Unconscious:** HP = 0 or failed CON roll after a major wound. Character cannot act; stable until further damage or First Aid.
- **Dying:** Unconscious + untreated wounds. Loses 1 HP/round until death or First Aid success.
- **Dead:** HP drops to −CON or lower (gamemaster's threshold). No resurrection by default — BRP is a mortality-respecting system.
- **Major wound CON roll:** Roll CON×5 (Average difficulty) or fall unconscious immediately regardless of remaining HP.
- Track with: `tracker.py condition add <name> incapacitated`

---

## Status Effects / Conditions

Standard BRP conditions — update `CONDITION_COLOURS` in `tracker.py`:

| Condition      | Severity | Effect summary |
|----------------|----------|----------------|
| unconscious    | critical | Cannot act; CON roll each round or continue losing HP |
| bleeding       | critical | Lose 1 HP/round until First Aid or Healing roll |
| impaled        | critical | Weapon lodged; extra DB damage; STR contest to remove |
| dying          | critical | Unconscious + losing HP; needs immediate First Aid |
| major wound    | warn     | CON roll passed but significant injury; GM discretion on penalties |
| prone          | warn     | Dodge at Difficult; melee attacks against prone at Easy |
| stunned        | warn     | Lose next action; defence rolls at Difficult |
| fatigued       | warn     | Skills at Difficult (optional fatigue rules) |
| poisoned       | warn     | Ongoing CON vs Potency resistance rolls |
| insane         | warn     | SAN-triggered; GM determines expression |
| shaken         | info     | Mild SAN loss; next social/mental roll at Difficult |
| grappled       | info     | Cannot move freely; opposed STR or Grapple to escape |
| invisible      | buff     | Attackers at Difficult to target |
| berserk        | buff     | +1D10 DB; cannot parry, dodge, or disengage |

---

## Advancement

- **Experience checks:** Each skill successfully used in a dramatic situation gets a tick.
- **Between sessions:** Roll D100 for each ticked skill — if the roll *exceeds* the current skill rating, the skill increases by 1D6%.
- **Characteristic improvement:** POW can be raised by winning a POW vs POW contest against a higher POW opponent.
- **No level system** — advancement is incremental and skill-specific.

---

## Bold Play Reward

**Reward name:** Luck roll / Special success
**Effect:** The GM may award an unspent Luck roll (POW×5) to a player for bold or clever play — this roll can be used once to avoid a catastrophic outcome. A natural special or critical success also functions as the system's built-in bold-play payoff.
**How to award:** Outstanding roleplay, clever tactical decisions, or staying true to character under pressure.

---

## Combat

### Round Structure (12 seconds)

1. **Statements** — declare intent, DEX order (highest first). Defences need not be pre-declared.
2. **Powers Phase** — instantaneous powers resolve in INT order (highest first).
3. **Action Phase** — attacks and actions resolve in DEX order (highest first).
4. **Resolution** — compare results on the Attack & Defense Matrix; apply damage.

Multiple actions: each action after the first is at DEX rank −5.

### Attack & Defense Matrix

| Attack  | Defense     | Result |
|---------|------------|--------|
| Success | Success    | Deflected — no damage |
| Special | Success    | Special negated; normal hit |
| Critical| Special    | Reduced to special result |
| Critical| Critical   | Attacker's weapon may be damaged |
| Success | Fail/None  | Hit — weapon damage + DB |
| Special | Fail/None  | Special effect + damage |
| Critical| Fail/None  | Max weapon damage + DB; ignore all armour |
| Fail    | —          | Miss |
| Fumble  | —          | Roll on fumble table |

### Special Success Effects

- **Slashing:** Bleeding (1 HP/round until treated)
- **Impaling:** Weapon lodges; +DB damage; victim must win STR contest to remove
- **Crushing/Bludgeoning:** Knockdown — resist with STR+SIZ vs attacker's STR+SIZ or fall prone

### Parry & Dodge

- **Parry:** Roll ≤ weapon/shield skill. Each subsequent parry −30% cumulative.
- **Dodge:** Roll ≤ Dodge skill. Each subsequent dodge −30% cumulative. Normally cannot dodge bullets/arrows.
- Cannot combine parry and dodge unless Fighting Defensively (forfeit offence; one free non-penalised dodge).

---

## Skills

Rated 0–100%+, organised in six categories:

- **Combat:** Melee Weapon, Missile Weapon, Brawl, Dodge, Grapple, Shield
- **Communication:** Bargain, Command, Fast Talk, Language, Persuade, Status
- **Manipulation:** Craft, Fine Manipulation, Sleight of Hand, Throw
- **Mental:** Appraise, Knowledge (specialty), Research, Science (specialty)
- **Perception:** Insight, Listen, Sense, Spot, Track
- **Physical:** Climb, Jump, Ride, Stealth, Swim

Skills can specialize (Melee Weapon (Sword) and Melee Weapon (Axe) are separate). Base chance varies by skill and campaign era.

---

## Powers (Genre-Dependent)

BRP supports multiple power types — enable whichever fit the campaign:

| Type | Fuel | Notes |
|------|------|-------|
| Magic | Power Points | Spells; INT rank activation |
| Sorcery | Power Points | Elemental/demonic summoning; more complex |
| Psychic Abilities | Power Points | POW vs POW resistance often required |
| Mutations | Passive | Beneficial and adverse genetic traits |
| Superpowers | Power Points | Epic/SuperHuman campaigns |

PP recover with rest (~1/hour). All powers are optional and genre-dependent — only load what the campaign uses.

---

## Power Levels

Calibrate to campaign tone:

| Level      | Prof. Skill Points | Max Starting Skill | Tone |
|------------|-------------------|--------------------|----|
| Normal     | 250               | 75%                | Horror, gritty realism |
| Heroic     | 325               | 90%                | Pulp, fantasy adventurers |
| Epic       | 400               | 101%               | Veteran heroes, arch-mages |
| SuperHuman | 500               | Unlimited          | Costumed supers, demigods |

---

## Campaign Arc Preferences

**Preferred campaign mode:** Either (improvised or imported)
**Typical arc structure:** Dynamic for most genres; hub-and-spoke for horror investigation (Call of Cthulhu style); linear for published scenarios.
**Genre conventions:** BRP rewards investigation, negotiation, and avoiding combat over brute force. The "All Is Lost" beat often lands as a catastrophic wound, a major NPC death, or a Sanity break. Endings should respect the cost the characters paid to get there.

---

## Additional System Notes

- **Narrate success levels.** Don't just say pass/fail — a special success deserves a vivid description of the exceptional outcome; a fumble deserves a moment of horror.
- **BRP is lethal.** Major wounds can end a character in one blow. Retreat, cover, and First Aid are serious tactical options. Don't soften this.
- **Resistance table for anything vs anything.** Poison vs CON, fire intensity vs armour rating, willpower contests — all handled identically.
- **No healing magic by default** in non-fantasy genres. In horror: healing is slow, scarce, and precious.
- **No system-specific scripts are required** for basic BRP play. The rules above are sufficient for the GM model to resolve all standard situations. Add scripts if specific dice pool calculations or extended tables prove unreliable in practice.
