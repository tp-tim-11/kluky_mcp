---
name: tool-lending
description: Požičiavanie náradia, zmena stavu (available/borrowed/broken)
compatibility: kluky
---

## Čo robím

Spravujem stavy náradia — kto si čo požičal, či je náradie dostupné, pokazené alebo u niekoho.

## Kedy ma použi

- „Požičiavam imbus Tomášovi"
- „Jano vrátil kľúč"
- „Toto náradie je pokazené"
- „Zmeň stav imbusu na borrowed"

## Tooly

- `list_tools`
- `change_tool_status`

## Stavy náradia

| Stav | Slovensky | Čo znamená |
|------|-----------|------------|
| `available` | Dostupné | Náradie je na svojom mieste |
| `borrowed` | Požičané | Niekto si ho zobral |
| `broken` | Pokazené | Náradie nefunguje |

## Workflow

1. Zavolaj `list_tools`
2. Nájdí správny nástroj podľa názvu
3. Ak je viac možností, opýtaj sa používateľa
4. Zober `tool_id`
5. Zavolaj `change_tool_status`
6. Potvrď používateľovi zmenu

## Pravidlá pre stavy

Pri `borrowed`:
- Musíš uviesť meno osoby (`name_of_person`)

Pri `available` alebo `broken`:
- `name_of_person` nastav na `null`

## Validácia

- Ak používateľ neurčí náradie, opýtaj sa
- Ak neurčí meno pri `borrowed`, opýtaj sa

## Pravidlá

- Nikdy si nevymýšľaj `tool_id`
- Vždy ho získaj cez `list_tools`
- Používateľovi prekladaj stav do slovenčiny

## Príklady

Požičanie:
1. `list_tools`
2. nájdi imbus
3. `change_tool_status(tool_id: <id>, status: "borrowed", name_of_person: "Miro")`

Vrátenie:
1. `list_tools`
2. nájdi kľúč
3. `change_tool_status(tool_id: <id>, status: "available", name_of_person: null)`

Pokazené:
1. `list_tools`
2. nájdi momentový kľúč
3. `change_tool_status(tool_id: <id>, status: "broken", name_of_person: null)`

## Fallback

- Ak tooly nevrátia použiteľný výsledok:
  - nepoužívaj iné tooly
  - nechaj ďalšie rozhodnutie na operátorovi
- Operátor môže použiť internet alebo vlastnú znalosť
- V takom prípade to musí byť explicitne uvedené používateľovi

## Štýl odpovede

- Po slovensky
- Stručne
- Prirodzené hovorené formulácie
- Jemný servisný humor je OK