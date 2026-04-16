# UC3 – Dokumentácia pre používateľa a tím

Tento dokument popisuje fungovanie UC3 v systéme Kluky. UC3 slúži na správu servisných záznamov – vytvorenie nového zápisu, zobrazenie histórie, úpravu existujúceho zápisu a export všetkých záznamov do CSV.

---

## 1) Účel UC3

UC3 uchováva servisnú históriu opráv. Systém vie zaznamenať, kto priniesol bicykel alebo servisovaný predmet, čo sa opravovalo, aký bol popis práce a aké náradie alebo materiál boli použité.

UC3 umožňuje:

- vytvoriť nový servisný záznam,
- vypísať všetky servisné záznamy pre konkrétne meno a priezvisko,
- upraviť existujúci záznam doplnením novej poznámky,
- exportovať všetky servisné záznamy do CSV súboru,
- prezerať záznamy aj cez view v Supabase.

Používajú sa štyri MCP nástroje:

- `add_record_if_not_exists`  
  Vytvorí alebo znovu použije hlavičku servisného záznamu pre daného používateľa a predmet a pridá nový servisný log.

- `get_all_records_for_name`  
  Vráti všetky servisné záznamy pre osobu podľa mena a priezviska.

- `update_record`  
  Upraví existujúci servisný log. Nový text sa doplní k pôvodnému popisu a zároveň sa môže zmeniť opravovaná časť a pridať použité náradie.

- `export_all_records_to_csv_desktop`  
  Exportuje všetky servisné záznamy do CSV súboru na plochu používateľa.

---

## 2) Použitie z pohľadu používateľa

### A) Vytvorenie nového záznamu

Používateľ môže povedať napríklad:

> Zapíš opravu reťaze pre Jozefa Kráľa na bicykli Trek Marlin 7. Vymenil som reťaz a použil nitovač.

Systém z toho potrebuje získať tieto údaje:

- meno zákazníka,
- priezvisko zákazníka,
- servisovaný predmet alebo bicykel,
- opravovanú časť,
- popis práce,
- použité náradie alebo materiál.

Ak niektorý povinný údaj chýba, asistent sa používateľa dopýta.

Po úspešnom zápise systém potvrdí, že záznam bol pridaný.

---

### B) Vypísanie servisnej histórie

Používateľ môže povedať napríklad:

> Ukáž servisné záznamy pre Jozefa Kráľa.

Systém vyhľadá všetky záznamy podľa mena a priezviska a zobrazí ich v čitateľnom tvare.

Odporúčaný formát výstupu:

```text
Servisné záznamy pre Jozef Kráľ:

Záznam 1
- Dátum: 15. apríla 2026
- Bicykel: Trek Marlin 7
- Opravovaná časť: Reťaz
- Popis práce: Vymenená opotrebovaná reťaz za novú.
- Použité náradie: nitovač, mierka reťaze
```

Interné technické polia ako `record_id`, `log_id`, `raw_data`, `faults`, `first_mention` a `last_update` sa bežnému používateľovi nevypisujú.

Ak sa nenájdu žiadne záznamy, odporúčaná odpoveď je:

```text
Pre používateľa Jozef Kráľ som nenašiel žiadne servisné záznamy.
```

---

### C) Úprava existujúceho záznamu

Používateľ môže povedať napríklad:

> K poslednému záznamu doplň, že som ešte nastavil prehadzovačku.

Úprava funguje tak, že nový text sa neprerobí namiesto pôvodného, ale doplní sa k existujúcemu popisu. Vďaka tomu zostáva zachovaná história práce.

Pri úprave je potrebné poznať:

- `record_id` – identifikátor servisnej hlavičky,
- `log_id` – identifikátor konkrétneho servisného zápisu,
- novú opravovanú časť,
- nový text poznámky,
- prípadne nové použité náradie.

Používateľovi sa tieto technické ID bežne nezobrazujú. Používa ich najmä interná logika asistenta pri práci s databázou.

---

### D) Export všetkých záznamov do CSV

Používateľ môže povedať napríklad:

> Exportuj všetky servisné záznamy do CSV.

Systém zavolá `export_all_records_to_csv_desktop` a vytvorí CSV súbor na ploche používateľa.

Ak používateľ nezadá názov súboru, vytvorí sa automatický názov v tvare:

```text
servisne_zaznamy_YYYYMMDD_HHMMSS.csv
```

CSV obsahuje tieto stĺpce:

| Stĺpec | Popis |
|---|---|
| `record_id` | ID servisnej hlavičky |
| `log_id` | ID konkrétneho servisného zápisu |
| `first_name` | meno zákazníka |
| `last_name` | priezvisko zákazníka |
| `subject_name` | servisovaný predmet alebo bicykel |
| `first_mention` | dátum prvého vytvorenia servisnej hlavičky |
| `last_update` | dátum poslednej aktualizácie servisnej hlavičky |
| `dt` | dátum konkrétneho servisného zápisu |
| `what_i_am_fixing` | opravovaná časť |
| `work_desc` | popis vykonanej práce |
| `faults` | zaznamenané chyby, ak existujú |
| `raw_data` | pôvodný text používateľa / interný surový zápis |
| `repaired_with` | použité náradie alebo materiál |

CSV sa zapisuje s kódovaním `utf-8-sig`, aby sa správne otvorilo aj v Exceli.

---

## 3) Vstupy a výstupy nástrojov

### `add_record_if_not_exists`

#### Vstup

| Parameter | Popis |
|---|---|
| `first_name` | meno zákazníka |
| `last_name` | priezvisko zákazníka |
| `subject_name` | servisovaný predmet alebo bicykel |
| `what_i_am_fixing` | konkrétna opravovaná časť |
| `raw_text` | pôvodný text / popis práce od používateľa |
| `repaired_with` | zoznam použitého náradia alebo materiálu |

#### Výstup

- `pridal som` – záznam bol úspešne pridaný,
- `nepridal som` – zápis sa nepodaril.

---

### `get_all_records_for_name`

#### Vstup

| Parameter | Popis |
|---|---|
| `first_name` | meno zákazníka |
| `last_name` | priezvisko zákazníka |

#### Výstup

Zoznam servisných záznamov. Každý záznam obsahuje napríklad:

- `record_id`,
- `log_id`,
- `first_name`,
- `last_name`,
- `subject_name`,
- `first_mention`,
- `last_update`,
- `dt`,
- `what_i_am_fixing`,
- `work_desc`,
- `faults`,
- `raw_data`,
- `repaired_with`.

Pri odpovedi používateľovi sa technické polia nezobrazujú. Výstup sa prekladá do prirodzeného slovenského formátu.

---

### `update_record`

#### Vstup

| Parameter | Popis |
|---|---|
| `record_id` | ID servisnej hlavičky z tabuľky `repair_records` |
| `log_id` | ID konkrétneho zápisu z tabuľky `repair_logs` |
| `what_i_am_fixing` | nová alebo aktuálna opravovaná časť |
| `raw_text` | nový text, ktorý sa doplní k existujúcemu zápisu |
| `repaired_with` | nové alebo doplnené použité náradie |

#### Výstup

- `update sa podaril` – úprava bola uložená,
- `update sa nepodaril` – úprava zlyhala alebo záznam neexistuje.

---

### `export_all_records_to_csv_desktop`

#### Vstup

| Parameter | Popis |
|---|---|
| `filename` | voliteľný názov CSV súboru |

Ak názov nemá príponu `.csv`, systém ju automaticky doplní.

#### Výstup

- cesta k uloženému CSV súboru na ploche používateľa.

---

## 4) Supabase view

V Supabase je dostupný view pre pohodlné čítanie servisných záznamov. View spája údaje z viacerých tabuliek do jedného prehľadného výstupu, aby nebolo nutné ručne skladať joiny nad servisnými tabuľkami.

View je určený najmä na:

- rýchlu kontrolu servisných záznamov v Supabase UI,
- jednoduché filtrovanie podľa zákazníka, predmetu alebo dátumu,
- kontrolu exportovaných údajov,
- prehľadné zobrazenie použitého náradia pri jednotlivých opravách.

Logicky obsahuje rovnaké údaje ako CSV export:

- ID servisnej hlavičky,
- ID servisného logu,
- meno a priezvisko zákazníka,
- názov servisovaného predmetu,
- dátumy vytvorenia a aktualizácie,
- opravovanú časť,
- popis práce,
- pôvodný text zápisu,
- použité náradie alebo materiál.

---

## 5) Technický popis implementácie

UC3 je implementované v súbore:

```text
src/kluky_mcp/tools/uc3.py
```

Vstupné modely sú definované v:

```text
src/kluky_mcp/models.py
```

Pripojenie na databázu zabezpečuje:

```text
src/kluky_mcp/db.py
```

Databáza je PostgreSQL a beží cez Supabase. Po pripojení sa nastavuje časová zóna:

```sql
SET TIME ZONE 'Europe/Bratislava';
```

---

## 6) Databázové tabuľky a prepojenia

### `users`

Uchováva zákazníkov.

Používané polia:

- `id`,
- `first_name`,
- `last_name`.

Pri zápise sa používateľ vyhľadá podľa presného mena a priezviska. Ak neexistuje, vytvorí sa nový riadok.

---

### `items`

Uchováva servisované predmety, napríklad bicykle.

Používané polia:

- `id`,
- `name`,
- `code`.

UC3 pracuje s predmetmi, kde `code IS NULL`. Ak predmet s daným názvom neexistuje, vytvorí sa nový.

---

### `repair_records`

Predstavuje hlavičku servisnej histórie pre konkrétneho zákazníka a konkrétny predmet.

Používané polia:

- `id`,
- `user_id`,
- `item_id`,
- `first_mention`,
- `last_update`.

Prepojenia:

- `repair_records.user_id` → `users.id`,
- `repair_records.item_id` → `items.id`.

Pre dvojicu `user_id` + `item_id` existuje unikátny záznam. Pri opakovanom zápise pre rovnakého zákazníka a rovnaký predmet sa nepoužije nová hlavička, ale existujúca.

---

### `parts`

Uchováva časti servisovaného predmetu, ktoré sa opravovali.

Používané polia:

- `id`,
- `item_id`,
- `name`.

Prepojenie:

- `parts.item_id` → `items.id`.

Pre rovnaký predmet a rovnaký názov časti sa používa existujúci záznam. Unikátnosť je riešená cez dvojicu `item_id` + `name`.

---

### `repair_logs`

Predstavuje konkrétny servisný zápis v rámci servisnej hlavičky.

Používané polia:

- `id`,
- `record_id`,
- `part_id`,
- `dt`,
- `work_desc`,
- `faults`,
- `raw_data`.

Prepojenia:

- `repair_logs.record_id` → `repair_records.id`,
- `repair_logs.part_id` → `parts.id`.

Pri vytvorení nového záznamu sa vloží nový riadok do `repair_logs`. Do `work_desc` aj `raw_data` sa uloží text z `raw_text`.

Pri úprave sa nový text pripojí k pôvodnému obsahu `work_desc` a `raw_data` cez nový riadok. Pôvodný obsah sa teda nemaže.

---

### `resources`

Uchováva náradie a materiál, ktoré sa môžu použiť pri oprave. Túto tabuľku využíva aj UC1.

Používané polia:

- `id`,
- `name`,
- `deleted`.

UC3 používa iba existujúce zdroje, kde `deleted = false`. Názvy v `repaired_with` sa párujú podľa presného názvu. Neexistujúce alebo zmazané náradie sa ignoruje.

---

### `repair_log_tools`

Prepájacia tabuľka medzi servisnými logmi a použitým náradím.

Používané polia:

- `log_id`,
- `tool_id`.

Prepojenia:

- `repair_log_tools.log_id` → `repair_logs.id`,
- `repair_log_tools.tool_id` → `resources.id`.

Jeden servisný zápis môže mať viac použitých nástrojov a jeden nástroj môže byť použitý vo viacerých zápisoch. Ide teda o many-to-many vzťah.

Pri vkladaní sa používa ochrana proti duplicitám cez `ON CONFLICT (log_id, tool_id) DO NOTHING`.

---

## 7) Tok dát pri vytvorení záznamu

1. Normalizuje sa meno a priezvisko používateľa.
2. Vyhľadá sa alebo vytvorí záznam v `users`.
3. Vyhľadá sa alebo vytvorí servisovaný predmet v `items`.
4. Vyhľadá sa alebo vytvorí hlavička v `repair_records` pre dvojicu používateľ + predmet.
5. Vyhľadá sa alebo vytvorí opravovaná časť v `parts`.
6. Vytvorí sa nový riadok v `repair_logs`.
7. Použité náradie sa vyhľadá v `resources`.
8. Väzby medzi logom a náradím sa zapíšu do `repair_log_tools`.
9. Transakcia sa potvrdí cez `commit`.

Ak nastane chyba, vykoná sa `rollback` a nástroj vráti neúspešnú odpoveď.

---

## 8) Tok dát pri zobrazení záznamov

`get_all_records_for_name` vyhľadáva podľa mena a priezviska. Výsledok skladá cez joiny:

```text
users
→ repair_records
→ items
→ repair_logs
→ parts
→ repair_log_tools
→ resources
```

Záznamy sú radené od najnovšieho podľa:

```sql
COALESCE(rl.dt, rr.last_update) DESC,
rr.id DESC,
rl.id DESC
```

Použité náradie sa agreguje do poľa `repaired_with`.

---

## 9) Tok dát pri úprave záznamu

1. `record_id` a `log_id` sa skonvertujú na čísla.
2. Overí sa, že daný `repair_logs.id` patrí k danému `repair_records.id`.
3. Načíta sa pôvodný `work_desc`, `raw_data` a `item_id`.
4. Nový text sa doplní k pôvodnému textu cez nový riadok.
5. Vyhľadá sa alebo vytvorí nová opravovaná časť v `parts`.
6. Aktualizuje sa riadok v `repair_logs`.
7. Nové použité náradie sa pripojí cez `repair_log_tools`.
8. Transakcia sa potvrdí cez `commit`.

---

## 10) Tok dát pri exporte CSV

Export skladá rovnaký prehľad ako výpis záznamov, ale bez filtra na konkrétneho používateľa. Dáta sa zoradia od najnovších a zapíšu sa do CSV súboru.

Používa sa:

- `csv.writer`,
- `StringIO`,
- automatické zistenie plochy cez `xdg-user-dir DESKTOP`,
- fallback na `~/Desktop`,
- kódovanie `utf-8-sig`.

---

## 11) Dôležité pravidlá a limity

- Meno, priezvisko a názov predmetu sa pri zápise normalizujú – odstraňujú sa nadbytočné medzery a slová sa kapitalizujú.
- Vyhľadávanie histórie je podľa presného mena a priezviska po normalizácii.
- Náradie v `repaired_with` sa páruje podľa presného názvu v tabuľke `resources`.
- Neexistujúce náradie sa nevytvára automaticky, iba sa ignoruje.
- Úprava záznamu nemaže pôvodný popis, ale dopĺňa nový text.
- Používateľovi sa nezobrazujú interné databázové ID, ak to nie je nutné.
- CSV export je globálny – exportuje všetky servisné záznamy, nie iba jedného používateľa.
- Supabase view slúži na pohodlné čítanie a kontrolu dát, zápis sa vykonáva cez MCP nástroje.
