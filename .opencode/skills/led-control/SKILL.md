---
name: led-control
description: Ovládanie LED osvetlenia pozícií náradia - zapnutie, vypnutie, kontrola stavu
compatibility: kluky
---

## Čo robím

Zapínam a vypínam LED osvetlenie na ESP32 pásikoch, ktoré ukazujú kde je náradie. Tiež viem skontrolovať, či sú zapnuté.

## Kedy ma použi

- „Zapni ledky"
- „Vypni LED osvetlenie"
- „Sú ledky zapnuté?"
- „Skontroluj stav LEDiek"

## Tooly

| Tool | Čo robí |
|------|---------|
| `get_led_flag` | Vráti či sú LED zapnuté (`true`) alebo vypnuté (`false`) |
| `set_led_flag` | Zapne (`true`) alebo vypne (`false`) LED osvetlenie |

## Pravidlá

- Nikdy si nevymýšľaj stav LED
- Vždy používaj výsledok z toolu
- `set_led_flag` používa iba hodnoty `true` alebo `false`

## Workflow

### Zapnutie LED

1. Zavolaj `set_led_flag(true)`
2. Potvrď používateľovi zapnutie

### Vypnutie LED

1. Zavolaj `set_led_flag(false)`
2. Potvrď používateľovi vypnutie

### Kontrola stavu

1. Zavolaj `get_led_flag`
2. Oznám používateľovi aktuálny stav

## Odpoveď používateľovi

- Pri zapnutí LED:
  - povedz, že LED osvetlenie je zapnuté
  - môžeš spomenúť, že pri ukázaní pozície bude náradie blikať

- Pri vypnutí LED:
  - povedz, že LED sú vypnuté
  - lokácie sa budú oznamovať len slovne

- Pri kontrole stavu:
  - povedz, či sú LED zapnuté alebo vypnuté

## Tip

Keď sú LED vypnuté a používateľ sa pýta na pozíciu náradia, neinformuj ho o LED — len povedz kde náradie je.

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