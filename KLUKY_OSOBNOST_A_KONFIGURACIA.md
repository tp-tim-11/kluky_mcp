# Kluky – Dokumentácia osobnosti a konfigurácie agenta

Tento dokument popisuje ako a kde sa nastavuje osobnosť a správanie agenta Kluky — čo je v `AGENTS.md` a `operator.md` a aký je medzi nimi rozdiel.

---

## 1) Účel konfigurácie osobnosti

Konfigurácia osobnosti definuje kto Kluky je, ako komunikuje a ako sa rozhoduje. Skladá sa z dvoch súborov:

- `AGENTS.md`  
  - vstupný prehľad pre vývojárov — čo systém obsahuje a základné pravidlá správania,

- `.opencode/agents/operator.md`  
  - jadro agenta — rola, osobnosť, rozhodovací proces a presné pravidlá pre každú oblasť.

---

## 2) Rozdiel medzi AGENTS.md a operator.md

| | `AGENTS.md` | `operator.md` |
|---|---|---|
| **Kto to číta** | Vývojár / tím | Agent (LLM) pri každej konverzácii |
| **Čo obsahuje** | Prehľad štruktúry, zoznam komponentov, zhrnutie pravidiel | Presná rola, osobnosť, rozhodovací proces, detailné pravidlá |
| **Miera detailu** | Stručný prehľad | Kompletné inštrukcie |
| **Zmena správania agenta** | Nie priamo | Áno — agent podľa neho koná |

`AGENTS.md` je pre ľudí — vysvetľuje čo je v projekte.  
`operator.md` je pre agenta — hovorí mu čo má robiť.

---

## 3) AGENTS.md – čo obsahuje a prečo

`AGENTS.md` sa nachádza v koreni repozitára. Obsahuje:

- zoznam agentov a ich súborov,
- odkaz na implementáciu toolov v `src/kluky_mcp/tools`,
- **zhrnuté pravidlá správania** — rýchly prehľad pre nového člena tímu.

### Kľúčové pravidlá definované v AGENTS.md

- Vždy odpovedaj po slovensky, vtipne a zrozumiteľne.
- Používateľovi tykaj — nikdy nevykaj.
- Odpovede sú prehávané ako **hovorené slovo** — vyhýbaj sa formuláciám odkazujúcim na písaný text.
- Preferuj prirodzené hovorené formulácie: „poviem ti", „vysvetlím ti", „ukážem ti".
- Ak je otázka jednoduchá, odpovedz priamo a stručne.
- Ak je na odpoveď potrebný tool, najprv zavolaj tool.
- **Nikdy si nevymýšľaj** fakty, dostupnosť, ceny, termíny ani výsledky toolov.

---

## 4) operator.md – jadro osobnosti

`operator.md` je súbor ktorý agent dostane ako inštrukcie pri každej konverzácii. Je to **jediný súbor kde sa nastavuje správanie agenta**.

### 4.1) Rola

Agent sa volá **Kluky** a vystupuje ako operátor bicyklového servisu.

- Predstavuje sa ako technik v servise, ktorý komunikuje s kolegom v dielni.
- **Neimplementuje biznis logiku sám** — všetko beží cez MCP tooly.

### 4.2) Osobnosť

- **Vtipný** — používa ľahký servisný humor: prirovnania z dielne, krátke vtipné poznámky o náradí.
- **Zrozumiteľný** — vysvetľuje jednoducho, ako technik v servise.
- **Kompetentný** — pozná náradie, postupy, servisnú históriu.

Humor musí byť krátky a prirodzený. **Najdôležitejšia je vždy informácia**, humor je len doplnok.

### 4.3) Rozhodovací proces

Pri každej požiadavke:

```
1. Porozumej čo používateľ chce.
2. Potrebujem na to tool? Ak áno → vyber správny tool.
3. Mám všetky povinné parametre? Ak nie → opýtaj sa.
4. Zavolaj tool.
5. Vráť odpoveď.
```

### 4.4) TTS workflow

Každá odpoveď má dva výstupy:

1. **TTS verzia** (hovorená) — kratšia, max 400 znakov, 1–4 vety, poslaná cez `send_tts_response` **pred** dlhšou odpoveďou.
2. **Textová verzia** (obrazovka) — detailnejšia.

Výnimka: ak používateľ povie že nepočul, použi `last_user_message` — v tomto prípade **nepoužívaj TTS**.

### 4.5) Schopnosti (capabilities)

Operator má definované 4 oblasti s presnými pravidlami:

| Oblast | Tooly |
|--------|-------|
| **0. Session a TTS** | `new_session`, `last_user_message`, `send_tts_response` |
| **1. Náradie a LED** | `list_tools`, `show_tool_position`, `change_tool_status`, `get_led_flag`, `set_led_flag`, `show_mapping`, `set_mapping` |
| **2. Dokumentácia** | `get_documents`, `get_document_info` |
| **3. Servisné záznamy** | `add_record_if_not_exists`, `get_all_records_for_name`, `update_record`, `export_all_records_to_csv_desktop` |

Pre každú oblasť sú v `operator.md` uvedené presný workflow, povolené tooly, pravidlá čo sa nesmie a formát výstupu pre používateľa.

---

## 5) Kde a ako meniť osobnosť

### Zmena tónu a humoru

Upraviť v `operator.md`, sekcia `## Štýl odpovedí`.

### Zmena základných pravidiel

Upraviť v `AGENTS.md`, sekcia `## Pravidlá (zhrnutie)` — a zároveň zodpovedajúce miesto v `operator.md`.

### Pridanie novej schopnosti

1. Pridať nový tool do `src/kluky_mcp/tools/`
2. Zaregistrovať tool v `server.py`
3. Pridať capability sekciu do `operator.md` s popisom kedy a ako tool použiť

### Zmena workflow pre existujúcu oblasť

Upraviť príslušnú capability sekciu priamo v `operator.md`.

---

## 6) Dôležité pre bežnú prevádzku

- `operator.md` je **jediný súbor** ktorý priamo ovplyvňuje správanie agenta pri konverzácii.
- `AGENTS.md` slúži len pre orientáciu vývojárov — jeho zmena **nezmení** správanie agenta.
- Ak agent koná zle, riešenie je takmer vždy v `operator.md`.
- Pravidlá z `AGENTS.md` sú len zhrnutím — **podrobnosti sú vždy v `operator.md`**.

---

## 7) Známe limity

- Agent môže ignorovať pravidlá ak sú formulované nejasne alebo protirečivo.
- Príliš dlhý `operator.md` môže znížiť kvalitu odpovedí — LLM má obmedzenú pozornosť.
- Humor je ťažko predvídateľný — agenta možno smerovať štýlom, nie konkrétnymi vtipmi.
- Zmeny v `operator.md` sa prejavia až pri ďalšej konverzácii, nie v prebehajúcej.

---

## 8) Rýchly návod – ako zmeniť správanie

### Kluky je príliš formálny

**Kde zmeniť:** `operator.md` → sekcia `## Štýl odpovedí`  
**Čo urobiť:** Pridať konkrétnejší popis požadovaného tónu alebo príklady viet.

### Kluky vyka namiesto tykania

**Kde zmeniť:** `operator.md` → pravidlá štýlu  
**Čo skontrolovať:** Či je tam explicitne uvedené „tykaj, nikdy nevykaj".

### Kluky odmieta odpovedať na niečo čo má vedieť

**Kde zmeniť:** `operator.md` → príslušná capability sekcia  
**Čo urobiť:** Pridať explicitné povolenie a workflow pre daný prípad.

### Kluky si vymýšľa fakty

**Kde zmeniť:** `operator.md` → globálne pravidlá  
**Čo urobiť:** Zosilniť zákaz vymýšľania a povinnosť použiť tool.

### Kluky nepoužíva TTS

**Kde zmeniť:** `operator.md` → sekcia `### 0. Session a hlasová odpoveď`  
**Čo skontrolovať:** Poradie krokov — TTS sa musí volať **pred** textovou odpoveďou.