# HADES — সম্পূর্ণ Game Structure

Original Hades (Zagreus)-এর পুরো structure-এর একটি interactive Bengali guide —
একদম শুরু থেকে endgame পর্যন্ত।

**Live:** https://appleziarash1.github.io/emu/

## কী আছে

একটাই self-contained `index.html` — কোনো framework, CDN বা build step নেই।

| # | Section | # | Section |
| --- | --- | --- | --- |
| 01 | মূল Gameplay Loop | 13 | House of Hades |
| 02 | Six Infernal Arms + 24 Aspect (tabbed) | 14 | Mirror of Night |
| 03 | Daedalus Hammer | 15 | 25 Keepsakes |
| 04 | Boon system + rarity | 16 | Companions |
| 05 | God-by-God (Zeus → Chaos) | 17 | House Contractor |
| 06 | Status Effects | 18 | Fated List of Minor Prophecies |
| 07 | All 28 Duo Boons (god filter) | 19 | Permanent Currencies |
| 08 | Legendary Boons | 20 | Titan Blood |
| 09 | Pom of Power | 21 | 15 Pact of Punishment conditions |
| 10 | Charon's Shop + Well | 22 | Build examples |
| 11 | Room Rewards | 23 | Full progression flow |
| 12 | Four Realms + foes + boss entries | 24 | Five-layer summary |

## Interactive

- **Weapon tabs** — six Infernal Arms, each with its four aspects
- **Duo Boon filter** — pick a god to see the 7 Duo Boons it shares

## Data

The list-heavy sections were checked against sources rather than written from
memory: the 28 Duo Boons (eight Duo-offering gods, each sharing one with every
other), the 15 Pact conditions with rank and Heat values, the 25 Keepsakes and
the Mirror of Night talents.

## Local preview

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Deploy

Served by GitHub Pages from this branch. Push the branch and the site updates.
