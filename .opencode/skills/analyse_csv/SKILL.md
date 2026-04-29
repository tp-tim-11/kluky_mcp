---
name: analyse_csv
description: Analyzuje exportované servisné záznamy z CSV a vytvára stručný prehľad opráv, zákazníkov, dielov a používaného náradia.
---

# Analyse CSV Skill

## Účel

Použi tento skill, keď používateľ chce štatistiku, prehľad alebo analýzu servisných záznamov.

Skill neslúži na:
- pridávanie záznamov
- úpravu záznamov
- jednoduché vypísanie histórie

Na to už existujú UC3 tooly.

Tento skill robí **analytickú vrstvu nad CSV exportom**.

---

## Kedy skill použiť

Použi tento skill pri požiadavkách typu:

- koľko opráv bolo vykonaných
- koľko ľudí opravovalo
- čo sa opravuje najčastejšie
- ktoré časti bicyklov sa kazia najviac
- aké náradie sa používa najčastejšie
- kto má najviac servisných záznamov
- prehľad servisnej aktivity
- štatistika opráv
- analýza servisných záznamov

---

## Nepoužívaj skill, keď

- používateľ chce pridať záznam
- používateľ chce upraviť záznam
- používateľ chce históriu konkrétneho človeka
- používateľ chce iba export CSV bez analýzy

---

## Použitý MCP tool

Najprv zavolaj:

`export_all_records_to_csv_desktop`

Odporúčaný parameter:

`filename = servisne_zaznamy_analyza.csv`

Tool vráti **absolútnu cestu k CSV súboru**.

Tento súbor musíš:
1. otvoriť
2. prečítať ako tabuľku
3. analyzovať jeho riadky

Neprestaň po exporte — pokračuj analýzou.

---

## Očakávané CSV stĺpce

- record_id
- log_id
- first_name
- last_name
- subject_name
- dt
- what_i_am_fixing
- work_desc
- faults
- raw_data
- repaired_with

---

## Analýza

Zo súboru vypočítaj:

### 1. Počet servisných záznamov
- počítaj riadky, kde `log_id` nie je prázdne

### 2. Počet zákazníkov
- unikátne kombinácie `first_name + last_name`

### 3. Počet predmetov opravy
- unikátne `subject_name`

### 4. Najčastejšie opravované časti
- podľa `what_i_am_fixing`

### 5. Najčastejšie používané náradie
- podľa `repaired_with`
- hodnoty môžu byť oddelené čiarkou
- rozdeľ, očisti a spočítaj

### 6. Najaktívnejší zákazníci
- podľa počtu záznamov na osobu

### 7. Aktivita podľa dátumu
- použi `dt`
- agreguj podľa mesiaca alebo dňa

### 8. Opakujúce sa problémy
- sleduj `what_i_am_fixing`, `faults`, `work_desc`
- identifikuj opakovania

---

## Normalizácia dát

Pred počítaním jemne zjednoť hodnoty:

- defekt / defekty = jedna skupina
- motorová pila / motorová píla = jedna skupina
- odstráň nadbytočné medzery
- ignoruj veľkosť písmen

Ak si nie si istý, ber hodnoty oddelene.

---

## Formát odpovede

Odpovedaj po slovensky, stručne a ako človek zo servisu.

### Štruktúra:

1. Krátke zhrnutie (1 veta)
2. Číselný prehľad
3. Najčastejšie položky
4. Krátka interpretácia

### Príklad štýlu:

„Pozrel som servisné záznamy — vyzerá to tak, že bicykle sa tu najviac hádajú s brzdami a defektmi, klasika dielňa.“

---

## Pravidlá

- Nikdy si nevymýšľaj čísla
- Ak CSV nemá dáta, povedz to
- Ak niečo chýba, analyzuj len dostupné údaje
- Nevymýšľaj príčiny problémov
- Výstup je orientačný prehľad, nie presná štatistika

---

## DÔLEŽITÉ

- Nikdy nevypisuj interné premýšľanie
- Nepíš "Thinking"
- Nepíš kroky analýzy
- Nepíš čo ideš spraviť
- Nepíš debug info
- Nevypisuj JSON

Používateľ musí vidieť iba finálny výsledok.