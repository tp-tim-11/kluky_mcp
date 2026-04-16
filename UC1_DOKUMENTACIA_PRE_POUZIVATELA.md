# UC1 – Dokumentácia pre používateľa a tím

Tento dokument popisuje fungovanie UC1 (správa náradia a LED lokalizácia) v systéme Kluky.

---

## 1) Účel UC1

UC1 zabezpečuje správu náradia v dielni. Umožňuje:

- zobraziť zoznam náradia s aktuálnym stavom,
- zmeniť stav náradia (požičanie, vrátenie, poškodenie, strata),
- fyzicky ukázať polohu náradia pomocou LED pásov na ESP32,
- zapínať a vypínať LED lokalizáciu,
- spravovať mapovanie sektorov na IP adresy ESP32.

Používa sa sedem MCP nástrojov:

- `list_tools`  
  - zobrazí zoznam náradia s id, názvom, sektorom, pinom, LEDkou a stavom,

- `change_tool_status`  
  - zmení stav náradia a voliteľne zaznamená meno vypožičiavateľa,

- `show_tool_position`  
  - blikne LED nad konkrétnym náradím na ESP32 páse,

- `get_led_flag`  
  - skontroluje, či je LED lokalizácia zapnutá,

- `set_led_flag`  
  - zapne alebo vypne LED lokalizáciu,

- `show_mapping`  
  - zobrazí aktuálne mapovanie sektorov (A, B, C, D) na IP adresy ESP32,

- `set_mapping`  
  - automaticky vypočíta a nastaví IP adresy ESP32 podľa aktuálnej siete.

---

## 2) Použitie z pohľadu používateľa

### A) Zobrazenie náradia

**Odporúčaný postup:**

1. Zavoláme `list_tools`  
   - vráti kompletný zoznam náradia,

2. Pre každú položku dostaneme:  
   - id, názov, sektor, pin, LED, stav, meno vypožičiavateľa.

---

### B) Zmena stavu náradia

1. Zavoláme `change_tool_status` s názvom alebo id náradia a novým stavom,

2. Pri stave `BORROWED` je potrebné uviesť aj meno osoby,

3. Systém aktualizuje databázu a vráti potvrdenie.

**Dostupné stavy:**

| Anglicky   | Slovensky  |
|------------|------------|
| AVAILABLE  | Na mieste  |
| BORROWED   | Požičané   |
| BROKEN     | Pokazené   |
| LOST       | Stratené   |

---

### C) Lokalizácia náradia pomocou LED

1. Skontrolujeme `get_led_flag` – LED musí byť zapnuté,

2. Zavoláme `show_tool_position` s parametrami:
   - `sector` – písmeno sektora (A, B, C, D),
   - `pin` – číslo pinu LED pásu na ESP32,
   - `led` – číslo LEDky nad náradím.

3. ESP32 zabliká príslušnou LEDkou.

---

### D) Správa LED lokalizácie

- `get_led_flag` – zobrazí, či je LED zapnutá,
- `set_led_flag` s `true/false` – zapne alebo vypne LED.

---

### E) Správa ESP32 mapovania

- `show_mapping` – zobrazí aktuálne IP adresy pre každý sektor,
- `set_mapping` – automaticky prepočíta IP adresy podľa aktuálnej siete.

---

## 3) Vstupy a výstupy

### `list_tools`

#### Vstup

- bez parametrov

#### Výstup

- zoznam riadkov vo formáte:  
  `id | názov | sektor | pin | led | stav | Vypožičal: meno`

---

### `change_tool_status`

#### Vstup

- `tool_name`  
  - názov alebo id náradia,  
  - povinný parameter,

- `status`  
  - nový stav (AVAILABLE, BORROWED, BROKEN, LOST),  
  - povinný parameter,

- `name_of_person`  
  - voliteľné – meno osoby (povinné ak `status = BORROWED`).

#### Výstup

- potvrdenie o zmene stavu,
- alebo správa „Tool not found" ak náradie neexistuje.

---

### `show_tool_position`

#### Vstup

- `sector`  
  - písmeno sektora (A–D),  
  - povinný parameter,

- `pin`  
  - číslo pinu LED pásu na ESP32,  
  - povinný parameter,

- `led`  
  - číslo LEDky (0–63),  
  - povinný parameter.

#### Výstup

- odpoveď z ESP32 po úspešnom bliknutí,
- alebo chybová správa (timeout, odmietnuté spojenie, neplatný sektor/LED).

---

### `get_led_flag`

#### Vstup

- bez parametrov

#### Výstup

- „LED osvetlenie je zapnuté." alebo „LED osvetlenie je vypnuté."

---

### `set_led_flag`

#### Vstup

- `value`  
  - `true` = zapnúť, `false` = vypnúť.

#### Výstup

- potvrdenie o nastavení.

---

### `show_mapping`

#### Vstup

- bez parametrov

#### Výstup

- JSON objekt s IP adresami pre sektory A, B, C, D.

---

### `set_mapping`

#### Vstup

- bez parametrov

#### Výstup

- JSON objekt s novo vypočítanými IP adresami pre sektory A, B, C, D.

---

## 4) Implementácia

UC1 pozostáva z `uc1.py` a komunikuje s databázou a ESP32 zariadeniami.

### Databázová vrstva

- náradie je uložené v tabuľke `resources`,
- každý záznam obsahuje: `id`, `name`, `esp`, `pin`, `led`, `status`, `borrowed_by`, `deleted`,
- soft-delete: `deleted = false` filtruje len aktívne náradie.

### LED komunikácia s ESP32

Komunikácia prebieha cez TCP socket:

1. **Načítanie mapovania**  
   - zo súboru `esp32_map.json` získame IP adresu podľa sektora,

2. **Odoslanie príkazu**  
   - formát správy: `PIN:{pin},LED:{led}\n`,
   - pripojíme sa na port 8080 s timeoutom 5 sekúnd,

3. **Prijatie odpovede**  
   - ESP32 vráti potvrdenie a zatvorí spojenie.

### Mapovanie IP adries

- Sektory A, B, C, D majú priradené statické IP adresy na posledných oktetoch 101–104,
- `set_mapping` automaticky vypočíta správnu sieť podľa IP adresy servera,
- mapovania sa ukladajú do `esp32_map.json`.

### LED flag

- Stav (zapnuté/vypnuté) sa ukladá do `led_flag.json`,
- ak súbor chýba → predvolene sa LED blikanie vykonáva,
- `show_tool_position` skontroluje flag pred odoslaním príkazu na ESP32.

---

## 5) Dôležité pre bežnú prevádzku

- Pred `show_tool_position` vždy skontrolovať `get_led_flag`.
- Pri zmene WiFi siete zavolať `set_mapping` na aktualizáciu IP adries.
- Ak ESP32 neodpovedá – skontrolovať fyzické pripojenie a IP adresy cez `show_mapping`.
- `change_tool_status` akceptuje aj `id` náradia namiesto názvu.
- Maximum 64 LEDiek na jeden pás (0–63).

---

## 6) Známe limity

- ESP32 musí byť v rovnakej sieti ako server, inak TCP spojenie zlyhá.
- `set_mapping` predpokladá masku `/24` – pri iných maskách je potrebné nastaviť IP ručne cez JSON.
- Timeout pre ESP32 je 5 sekúnd – pri pomalej sieti môže dôjsť k false-negative.
- LED čísla nad 63 sú odmietnuté validáciou.

---

## 7) UC1 – rýchly návod

Nižšie uvádzame typické situácie a očakávané výstupy.

### Ako zobraziť zoznam náradia

**Čo zadáme:**
„Ukáž mi všetko náradie."

**Čo očakávame:**

* zoznam náradia s id, názvom, stavom a menom vypožičiavateľa.

### Ako požičať náradie

**Čo zadáme:**
„Náradie 'Moment kľúč' požičal Ján Novák."

**Čo očakávame:**

* aktualizácia stavu na BORROWED,
* zaznamená meno Ján Novák.

### Ako vrátiť náradie

**Čo zadáme:**
„Vráť Moment kľúč na miesto."

**Čo očakávame:**

* aktualizácia stavu na AVAILABLE,
* vymazanie mena vypožičiavateľa.

### Ako nájsť náradie pomocou LED

**Čo zadáme:**
„Kde je Moment kľúč? Ukáž polohu."

**Čo očakávame:**

* bliknutie LEDky nad náradím v príslušnom sektore,
* potvrdenie od ESP32.

### Ak LED nebliká

**Čo skontrolujeme:**

1. `get_led_flag` – je LED zapnutá?
2. `show_mapping` – sú IP adresy správne?
3. Fyzické pripojenie ESP32 k sieti.

### Keď sa zmenila WiFi sieť

**Čo urobíme:**
„Nastav nové ESP32 mapovanie."

**Čo očakávame:**

* `set_mapping` vypočíta nové IP adresy,
* vráti aktualizovaný JSON s adresami pre sektory A–D.
