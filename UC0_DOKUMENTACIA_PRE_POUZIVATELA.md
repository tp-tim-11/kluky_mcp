# UC0 – Dokumentácia pre používateľa a tím

Tento dokument popisuje fungovanie UC0 (správa session a hlasové odpovede) v systéme Kluky.

---

## 1) Účel UC0

UC0 zabezpečuje základnú komunikáciu medzi agentom a používateľom. Umožňuje:

- spustiť novú konverzáciu (vymazať históriu),
- získať poslednú správu od používateľa,
- odoslať hlasovú (TTS) odpoveď používateľovi.

Používajú sa tri MCP nástroje:

- `new_session`  
  - vymaže aktuálnu konverzáciu a spustí novú session,

- `last_user_message`  
  - vráti poslednú správu od používateľa,

- `send_tts_response`  
  - odošle text ako hlasovú odpoveď cez TTS.

---

## 2) Použitie z pohľadu používateľa

### A) Spustenie novej session

**Odporúčaný postup:**

1. Zavoláme `new_session`  
   - keď chceme začať novú konverzáciu od začiatku,

2. Systém vymaže históriu  
   - a potvrdí úspešné spustenie.

---

### B) Získanie poslednej správy

Zavoláme `last_user_message`:

- vráti text poslednej správy od používateľa,
- používa sa napríklad pri spracovaní hlasového vstupu.

---

### C) Odoslanie hlasovej odpovede

Zavoláme `send_tts_response` s textom:

- text sa odošle na TTS engine,
- používateľ počuje odpoveď namiesto iba čítania.

---

## 3) Vstupy a výstupy

### `new_session`

#### Vstup

- bez parametrov

#### Výstup

- potvrdenie o vymazaní session,
- alebo chybová správa ak API neodpovedá.

---

### `last_user_message`

#### Vstup

- bez parametrov

#### Výstup

- text poslednej správy od používateľa.

---

### `send_tts_response`

#### Vstup

- `text`  
  - text na prečítanie,  
  - povinný parameter,  
  - rozsah: 1–400 znakov.

#### Výstup

- potvrdenie o odoslaní,
- alebo chybová správa ak TTS engine neodpovedá.

---

## 4) Implementácia

UC0 pozostáva z jedného súboru `uc0.py` a komunikuje s lokálnym API serverom.

### Ako funguje komunikácia

1. **`new_session`**
   - posiela GET požiadavku na `http://localhost:8321/v1/new_session`,

2. **`last_user_message`**
   - posiela GET požiadavku na `http://localhost:8321/v1/last_user_message`,

3. **`send_tts_response`**
   - posiela POST požiadavku na `http://localhost:8321/v1/speak`,
   - v tele požiadavky odosiela `{"text": "..."}`.

### Spracovanie odpovedí

- pri HTTP 200 → vrátime telo odpovede,
- pri inom statuse → vrátime chybovú správu s kódom a telom.

---

## 5) Dôležité pre bežnú prevádzku

- API server musí bežať na `localhost:8321`, inak všetky nástroje zlyhajú.
- `send_tts_response` má limit 400 znakov – pri dlhých odpovediach je potrebné text skrátiť.
- `new_session` nevráti históriu konverzácie – je nevratná operácia.

---

## 6) Známe limity

- Nástroje závisia od dostupnosti lokálneho API servera.
- `send_tts_response` má maximálnu dĺžku textu 400 znakov.
- Ak TTS engine neodpovedá, odpoveď nebude prečítaná nahlas, ale iba zobrazená.

---

## 7) UC0 – rýchly návod

Nižšie uvádzame typické situácie a očakávané výstupy.

### Ako spustiť novú konverzáciu

**Čo zadáme:**
„Začni novú session."

**Čo očakávame:**

* vymazanie histórie konverzácie,
* potvrdenie o úspešnom reštarte.

### Ako získať poslednú správu

**Čo zadáme:**
„Čo povedal používateľ naposledy?"

**Čo očakávame:**

* text poslednej správy od používateľa.

### Ako odoslať hlasovú odpoveď

**Čo zadáme:**
„Povedz používateľovi: Vaša oprava je pripravená."

**Čo očakávame:**

* odoslanie textu na TTS,
* potvrdenie o úspešnom odoslaní.

### Keď API server neodpovedá

**Čo nastane:**
Všetky nástroje UC0 vrátia chybovú správu s HTTP kódom.

**Čo robiť:**

* skontrolovať, či lokálny API server beží na porte 8321,
* reštartovať server ak je to potrebné.