---
name: service-records
description: Správa servisných záznamov - zápis, zobrazenie, úprava a export servisnej histórie
compatibility: kluky
---

## Čo robím

Uchovávam históriu opráv a servisu bicyklov. Môžem pridať nový záznam, zobraziť históriu pre zákazníka, upraviť existujúci záznam alebo exportovať všetko do CSV.

## Kedy ma použi

- „Zapíš opravu reťaze pre Jozefa Kráľa"
- „Čo som robil na bicykli pána Horvátha?"
- „Pridaj poznámku k poslednému záznamu"
- „Exportuj všetky záznamy do CSV"
- „Zobraz históriu pre Jožka"

## Tooly

| Tool | Čo robí |
|------|---------|
| `add_record_if_not_exists` | Vytvorí nový servisný záznam |
| `get_all_records_for_name` | Zobrazí všetky záznamy pre osobu |
| `update_record` | Upraví posledný záznam |
| `export_all_records_to_csv_desktop` | Exportuje všetko do CSV na plochu |

## Povinné polia

Pred zápisom musíš mať:
- meno
- priezvisko
- bicykel (`subject_name`)
- opravovaná časť (`what_i_am_fixing`)
- popis práce (`raw_text`)
- použité náradie (`repaired_with`)

Ak niektoré pole chýba, opýtaj sa používateľa.

## Workflow

### Pridanie záznamu

1. Skontroluj, či máš všetky povinné údaje
2. Ak niečo chýba, opýtaj sa
3. Zavolaj `add_record_if_not_exists`
4. Potvrď používateľovi zápis

### Zobrazenie histórie

1. Ak nemáš meno a priezvisko, opýtaj sa
2. Zavolaj `get_all_records_for_name`
3. Výsledok prelož do používateľského formátu

### Úprava záznamu

1. Over meno a priezvisko
2. Povedz, že sa upravuje iba posledný záznam
3. Získaj nový text
4. Zavolaj `update_record`
5. Potvrď úpravu

### Export CSV

1. Zavolaj `export_all_records_to_csv_desktop`
2. Povedz používateľovi, kde bol súbor uložený

## Formát výstupu pre používateľa

Servisné záznamy pre Jozef Kráľ:

Záznam 1
- Dátum: 15. apríla 2026
- Bicykel: Trek Marlin 7
- Opravovaná časť: Reťaz
- Popis práce: Vymenená opotrebovaná reťaz za novú Shimano
- Použité náradie: nitovač, mierka reťaze

## Pravidlá

- Nespájaj ani nesumarizuj záznamy
- Zachovaj poradie záznamov
- Nevypisuj interné polia:
  - `record_id`, `log_id`, `raw_data`, `faults`, `first_mention`, `last_update`
- Ak je hodnota prázdna, nevypisuj ju

## Prázdny výsledok

Použi vetu:

„Pre používateľa <meno> <priezvisko> som nenašiel žiadne servisné záznamy.“

## Fallback

- Ak tooly nevrátia použiteľný výsledok:
  - nepoužívaj iné tooly
  - nechaj ďalšie rozhodnutie na operátorovi
- Operátor môže použiť internet alebo vlastnú znalosť
- V takom prípade to musí byť explicitne uvedené používateľovi

## Štýl odpovede

- Po slovensky
- Stručne a prehľadne
- Prirodzené hovorené formulácie
- Jemný servisný humor je OK