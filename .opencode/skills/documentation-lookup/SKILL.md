---
name: documentation-lookup
description: Vyhľadávanie v servisných príručkách a dokumentácii bicyklov
compatibility: kluky
---

## Čo robím

Hľadám servisné návody, dokumentáciu a postupy pre opravy a údržbu bicyklov.

## Kedy ma použi

- „Ako nastaviť prehadzovačku?“
- „Postup na výmenu reťaze“
- „Ako spraviť brzdy“
- „Čo je v návode na odpruženie?“
- „Aké dokumenty máš k dispozícii?“
- „Aké témy máš k brzdám?“

## Povolené tooly

Používaj iba:
- `get_documents`
- `get_document_info`

Nepoužívaj žiadne iné tooly.

## Hlavné pravidlá

- Pred volaním `get_documents` preformuluj otázku do 1–2 krátkych variantov.
- Oprav gramatiku otázky bez zmeny významu.
- Ak `get_documents` vráti aspoň jednu relevantnú sekciu s `manual` a `unit_no`, vždy pred finálnou odpoveďou zavolaj `get_document_info` aspoň pre najrelevantnejšiu sekciu.
- Odpoveď skladaj primárne z textu z `get_document_info`, nie iba zo `summary`.
- Maximálne 1 retry `get_documents` je povolený iba ak prvý výsledok je prázdny alebo zjavne nerelevantný.
- Ak retrieval nestačí, môžeš doplniť odpoveď z vlastných znalostí, ale musíš to explicitne povedať.

## Workflow

### 1. Používateľ chce zoznam všetkých dokumentov

1. Zavolaj `get_documents` s query typu „zoznam všetkých dokumentov“.
2. Odpovedz zo `manuals_catalog`.
3. Začni vetou:
   `Mám k dispozícii tieto dokumenty:`
4. Vypíš názov manuálu a počet sekcií.
5. Na konci povedz:
   `Ak chceš, vyfiltrujem ich podľa témy.`

### 2. Používateľ chce dokumenty k téme

1. Zavolaj `get_documents` s 1–2 variantmi otázky v `queries`.
2. Vypíš najrelevantnejšie sekcie podľa:
   - `manual`
   - `title`
   - `unit_no`
   - `start_page` / `end_page`
   - `summary`
3. Ak existuje kandidát s `unit_no`, zavolaj `get_document_info` pre najrelevantnejšiu sekciu.
4. Odpoveď postav hlavne na texte dokumentu.

Preferovaný štýl:
`Máme k dispozícii napríklad <manual> a tieto sekcie sú k téme, ktorú potrebuješ:`

### 3. Používateľ sa pýta, ako niečo opraviť alebo nastaviť

1. Zavolaj `get_documents` raz s pôvodnou otázkou a prípadne jedným opraveným variantom.
2. Použi vyšší `top_k` (odporúčane 50–200).
3. Prezri `summary` a vyber 1–3 najrelevantnejšie sekcie.
4. Zavolaj `get_document_info` aspoň pre najrelevantnejšiu sekciu, prípadne aj pre ďalšie relevantné.
5. Finálnu odpoveď zlož hlavne z textu z dokumentu.

### 4. Používateľ chce dokumenty, ale nepovie tému

Použi túto formuláciu:

`Ahoj! Viem vyhľadať dokumenty ku konkrétnej téme. O akú oblasť bicyklov alebo údržby má ísť? Napr. nastavenie prehadzovačky, brzdy, reťaz, odpruženie, plášte, čistenie a údržba. Ak chceš, môžem vypísať aj zoznam všetkých dokumentov.`

### 5. Používateľ sa pýta, aké témy máme k dispozícii

1. Zavolaj `get_documents`.
2. Použi `topics_by_manual`.
3. Vypíš témy rozdelené podľa manuálov.

## Štýl odpovedí

- Po slovensky
- Stručne a zrozumiteľne
- Prirodzene, vhodne pre hovorenú odpoveď
- Jemný servisný humor je v poriadku, ale až po informácii