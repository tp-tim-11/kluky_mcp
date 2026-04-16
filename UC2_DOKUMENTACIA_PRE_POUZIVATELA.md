# UC2 – Dokumentácia pre používateľa a tím

Tento dokument popisuje fungovanie UC2 (servisné návody a znalostná báza) v systéme Kluky.

---

## 1) Účel UC2

UC2 zabezpečuje prácu s manuálmi a servisnými návodmi. Umožňuje:

- vyhľadávať relevantné sekcie dokumentov na základe otázky,
- zobrazovať katalóg manuálov a tém,
- vracať detailný text konkrétnych sekcií (napr. časť manuálu).

Používajú sa dva MCP nástroje:

- `get_documents`  
  - vyhľadá kandidátske sekcie a vráti katalóg,

- `get_document_info`  
  - vráti detailný text konkrétneho dokumentu alebo sekcie.

---

## 2) Použitie z pohľadu používateľa

### A) Otázka typu „ako nastaviť / opraviť…“

**Odporúčaný postup:**

1. Zavoláme `get_documents` s otázkou  
   - prípadne s jej jazykovo upravenou verziou,

2. Vyberieme najrelevantnejšie sekcie  
   - podľa názvu, `summary` a rozsahu strán,

3. Pre vybrané sekcie zavoláme `get_document_info`  
   - ideálne s konkrétnym `unit_no`,

4. Odpoveď skladáme primárne z reálneho textu sekcie  
   - nie iba zo `summary`.

---

### B) Zoznam dokumentov

Zavoláme `get_documents` s dotazom typu „zoznam všetkých dokumentov“ a použijeme `manuals_catalog`:

- názov manuálu,
- počet sekcií v manuáli.

---

### C) Prehľad tém

Použijeme `topics_by_manual` z `get_documents`:

- ku každému manuálu vypíšeme unikátne názvy sekcií (témy).

---

## 3) Vstupy a výstupy

### `get_documents`

#### Vstup

- `queries`  
  - aspoň jeden dotaz (zoznam stringov),

- `top_k`  
  - počet kandidátov na vrátenie,  
  - rozsah: 1–200,  
  - predvolená hodnota: 8,

- `manual_doc_id`  
  - voliteľný filter na konkrétny manuál.

#### Výstup

- `results`  
  - kandidátske sekcie obsahujúce:
    - `manual`,
    - `title`,
    - `unit_no`,
    - `start_page`,
    - `end_page`,
    - `summary`,

- `manuals_catalog`  
  - prehľad všetkých manuálov a počtu ich sekcií,

- `topics_by_manual`  
  - prehľad tém rozdelený podľa manuálov.

---

### `get_document_info`

#### Vstup

Je potrebné zadať aspoň jedno z:

- `doc_id`,
- `manual_name`.

Voliteľne:

- `unit_no`  
  - špecifikuje konkrétnu sekciu.

#### Výstup

- identifikácia dokumentu,
- počet vrátených jednotiek (`unit_count`),
- spojený text sekcií (`text`), ktorý obsahuje:
  - `unit_no`,
  - informácie o rozsahu strán.

---

## 4) Implementácia

UC2 pozostáva z dvoch hlavných častí:

- `uc2.py` vyberá najrelevantnejšie časti manuálov,
- `pageIndexRetrieval.py` načítava presný text vybraných sekcií.

### Ako funguje spracovanie

1. **Čistenie dotazov (`queries`)**
   - odstraňujeme prázdne hodnoty,
   - odstraňujeme duplicitné dotazy,

2. **Výber relevantných sekcií**
   - porovnávame dotaz s:
     - názvom manuálu,
     - názvom sekcie,
     - `summary`,
   - sekcie s vyššou zhodou majú vyššie skóre,

3. **Príprava prehľadov**
   - `manuals_catalog` – prehľad manuálov,
   - `topics_by_manual` – prehľad tém.

---

### Detailné načítanie (`get_document_info`)

Dokument identifikujeme:

- pomocou `doc_id`,
- alebo pomocou `manual_name` (ak `doc_id` nie je známe).

#### Práca s `unit_no`

- ak je zadané → vrátime konkrétnu sekciu,
- ak nie je zadané → vrátime celý dokument.

#### Chybové stavy

- neexistujúci dokument alebo sekcia → systém vráti chybovú odpoveď.

---

### 4.1) PageIndex – nastavenie

Používame knižnicu [PageIndex](https://github.com/VectifyAI/PageIndex), ktorú prispôsobujeme našej infraštruktúre.

#### Postup

1. **Vytvorenie forku**
   - vytvoríme fork repozitára do našej organizácie,

2. **Inicializácia projektu**
   - pridáme súbor `pyproject.toml`,

3. **Úprava `utils`**
   - upravíme prácu s URL,
   - nastavíme `base_url` pre interné zdroje,

4. **Pridanie do projektu**
   ```bash
   uv add <repo-url-na-fork>
   ```

#### Poznámka

Tieto úpravy sú nutné, pretože upstream verzia knižnice nepočíta s naším prostredím a spôsobom prístupu k dokumentom.

---

### 4.2) PageIndex vrstva a ingest pipeline

#### Ingest pipeline

1. **Načítanie dokumentu**

   * Dokument pridaný na úložisko stiahneme.
   * Následne spustíme ingest proces.

2. **Deduplikácia**

   * Vypočítame hash obsahu dokumentu.
   * Ak dokument už v systéme existuje, ingest preskočíme.

3. **Detekcia typu súboru**

   * **PDF a Markdown** → spracujeme priamo cez PageIndex.
   * **Ostatné formáty** → skonvertujeme do Markdownu pomocou knižnice `MarkItDown`.

#### Vytvorenie stromu v PageIndexe

PageIndex dokument spracuje a:

* vytvorí **hierarchický strom** podobný obsahu dokumentu,
* reprezentuje jednotlivé uzly pomocou:

  * titulku,
  * rozsahu strán alebo textu,
  * sumarizácie obsahu,
* môže **automaticky zlúčiť menšie uzly** podľa:

  * počtu tokenov,
  * počtu strán.

Výstupom je **stromová JSON štruktúra**, ktorú používame ako index pre retrieval.

#### Tree-based retrieval

Nad vytvoreným stromom prebieha **LLM-riadené vyhľadávanie**:

* model iteratívne vyberá relevantné uzly (`node_id`),
* strom prechádzame postupne podľa relevancie,
* dokument tak vieme prehľadávať bez potreby full chunkingu.

#### Flattening do `DocUnit`

Pre potreby databázy strom transformujeme na lineárnu reprezentáciu.

**`DocUnit` obsahuje:**

* `unit_no`,
* rozsah strán,
* titulok,
* `summary`,
* text.

#### Post-processing

Po flatteningu vykonávame:

* **zlučovanie malých sekcií**

  * aby sme predišli príliš krátkym chunkom,

* **fallback pre page range**

  * ak chýbajú informácie o stránkach, použijeme odhad podľa PDF.

#### Zápis do databázy

Zápis je **idempotentný** a prebieha cez `reindex_doc`:

1. odstránime existujúce záznamy pre daný `doc_id`,
2. vložíme nové záznamy typu `DocUnit`.

---

### 4.3) Dátový model indexu (`doc_units`)

Schéma indexu je definovaná v `SUPABASE_SQL_CREATE`.

#### Kľúčové polia

* **Identita a zdroj**

  * `doc_id`
  * `manual_name`
  * `source_path`
  * `source_type`

* **Granularita obsahu**

  * `unit_type`
  * `unit_no`
  * `start_page`
  * `end_page`

* **Obsah pre retrieval**

  * `title`
  * `heading_path`
  * `summary`
  * `text`

* **Fulltextové vyhľadávanie**

  * `search_vector` (PostgreSQL fulltext)
  * GIN index pre rýchle vyhľadávanie

* **Unikátnosť**

  * zabezpečujeme kombináciou `(doc_id, unit_type, unit_no)`

---

### 4.4) Retrieval pipeline a ranking kandidátov

UC2 retrieval prebieha v dvoch krokoch:

1. výber kandidátov cez `get_documents`,
2. detailné načítanie cez `get_document_info`.

#### Normalizácia dotazu

Vstupné `queries` čistíme nasledovne:

* odstránime nadbytočné medzery,
* odstránime prázdne hodnoty,
* odstránime duplicity.

#### Tokenizácia

Z dotazov používame slová s dĺžkou aspoň 3 znaky.

#### Skórovanie kandidátov

Každá sekcia v katalógu dostane skóre podľa zhody výrazov:

* zhoda v `manual_name`, `title` a `summary` zvyšuje skóre,
* zhoda priamo v `title` má vyššiu váhu, aby sme preferovali sekcie s presným tematickým názvom.

#### Filter manuálu

Ak je zadaný `manual_doc_id`, kandidátov filtrujeme:

* iba na daný manuál,
* vrátane jeho child variantov `doc_id`.

#### Radenie

Kandidátov triedime podľa:

* skóre,
* `updated_at` (novšie záznamy majú prioritu),
* názvu manuálu,
* `unit_no`.

#### Metadata pre agenta

Výstup obsahuje aj:

* `manuals_catalog`,
* `topics_by_manual`.

Vďaka tomu vieme odpovedať aj na otázky typu:

* „Vypíš dokumenty.“
* „Aké témy máme?“

---

### 4.5) Detailné načítanie sekcie (`get_document_info`) a validácie

Po výbere kandidáta voláme detailný endpoint, ktorý vracia reálny text sekcie pre finálnu odpoveď.

#### Identifikácia dokumentu

Dokument identifikujeme:

* primárne cez `doc_id`,
* alternatívne cez `manual_name`, pričom vyberieme najnovší zodpovedajúci `doc_id`.

#### Validácia vstupu

Musí byť zadané aspoň jedno z nasledujúcich polí:

* `doc_id`,
* `manual_name`.

Validáciu vykonávame cez model validator.

#### Voliteľný `unit_no`

* Ak je `unit_no` zadané, vrátime iba konkrétnu sekciu.
* Ak `unit_no` zadané nie je, vrátime celý dokument vo forme všetkých jednotiek v správnom poradí.

#### Formát textu

Výstup skladáme z jednotlivých unitov a dopĺňame technické hlavičky:

* `unit_type`,
* `unit_no`,
* `start_page`,
* `end_page`.

#### Chybové stavy

* neexistujúci manuál → chyba „manuál neexistuje“,
* neexistujúci `doc_id` → chyba „dokument neexistuje“,
* neexistujúci `unit_no` v dokumente → chyba „dokument nemá dané `unit_no`“.

#### Dôvod návrhu v agentovi

Postupujeme nasledovne:

* najprv použijeme `get_documents`,
* potom pre vybrané sekcie použijeme `get_document_info`,
* `summary` používame len orientačne,
* finálnu odpoveď vždy staviame na reálnom texte dokumentu.

---

## 5) Dôležité pre bežnú prevádzku

* Pre presné odpovede používame `get_document_info` s konkrétnym `unit_no`.
* Ak potrebujeme iba orientačný prehľad, použijeme `get_documents`.
* Pri požiadavke „Vypíš všetky dokumenty“:

  * neaplikujeme tematické filtrovanie,
  * vrátime celý katalóg.
* Pri otázke „Aké témy máme?“ použijeme `topics_by_manual`.

---

## 6) Známe limity

* Relevancia výsledkov závisí od kvality `title` a `summary` v indexe.
* Pri veľmi krátkych alebo nejednoznačných otázkach môže byť výber sekcií širší.
* Ak v databáze neexistuje dané `unit_no`, nie je možné vrátiť detail sekcie.
* Pri skenovaných PDF bez textovej vrstvy môže konverzia zlyhať, preto je potrebný OCR vstup.

---

## 7) UC2 – rýchly návod

Nižšie uvádzame typické otázky a očakávané výstupy.

### Ako sa spýtať na postup

**Čo zadáme:**
„Ako nastavíme prehadzovačku na MTB?“

**Čo očakávame:**

* stručný postup,
* praktické kroky z konkrétnej sekcie manuálu.

### Ako získať zoznam dokumentov

**Čo zadáme:**
„Vypíš všetky dokumenty.“

**Čo očakávame:**

* zoznam manuálov,
* počet sekcií pre každý manuál.

### Ako získať prehľad tém

**Čo zadáme:**
„Aké témy máme k brzdám?“

**Čo očakávame:**

* prehľad tém rozdelený podľa manuálov,
* napríklad: odvzdušnenie, nastavenie páky, brzdové platničky.

### Ako získať konkrétnu sekciu

**Čo zadáme:**
„Ukáž konkrétnu časť manuálu k reťazi.“

**Čo očakávame:**

* presný text jednej sekcie,
* nie celý manuál.

### Keď je odpoveď príliš všeobecná

**Čo zadáme:**
„Daj detail pre konkrétnu sekciu.“

**Čo očakávame:**

* presnejší výstup,
* menej všeobecného textu,
* viac praktických krokov.

### Keď výsledok nesedí

**Čo zadáme:**
„Skúsme inú formuláciu otázky.“

**Čo očakávame:**

* lepší výber sekcií,
* presnejšie odpovede, pretože systém je citlivý na názvy a `summary` v indexe.
