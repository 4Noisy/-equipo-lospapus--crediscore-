# Falco · reglas de runtime de CrediScore (S10)

Kyverno **previene** (no deja entrar imágenes sin firma). Falco **detecta**: mira
las llamadas al sistema de los contenedores mientras corren y alerta si algo raro pasa.

## Nuestras 3 reglas ([rules-custom.yaml](rules-custom.yaml))

| Regla | Qué detecta | Por qué importa en CrediScore | Prioridad |
| :--- | :--- | :--- | :-: |
| Shell o proceso inesperado | Cualquier proceso distinto de `python3` dentro de scoring-api | La imagen es distroless y no trae shell. Si aparece uno, alguien metió un binario: compromiso casi seguro | CRITICAL |
| Escritura fuera de `/tmp` | La API abre un archivo para escribir fuera de `/tmp` | La API guarda todo en memoria. Escribir en otro lado es señal de persistencia o de código modificado | ERROR |
| Conexión saliente inesperada | La API se conecta a una IP pública | La API no llama a nadie afuera. Puede ser fuga de RUT y montos, o un reverse shell | CRITICAL |

## Ruta de alerta

```
Falco (DaemonSet) -> Falcosidekick -> canal #alertas-crediscore (Discord)
                                   -> incidente para el de turno (CRITICAL y ERROR)
```

- Regla del taller: **cada alerta High o más abre un incidente**, no se queda en un log.
- CRITICAL: se aísla el Pod (se le quita la etiqueta del Service) y se revisa.
- La NetworkPolicy (`k8s/networkpolicy.yaml`) ya bloquea la salida a Internet; la
  regla 3 avisa si alguien lo intenta igual.

## Cómo se prueba

El job `runtime (falco)` de [`supply-chain.yml`](../.github/workflows/supply-chain.yml)
levanta Falco con estas reglas, corre la API y simula los 3 ataques. Si alguna
regla no genera su alerta, el job falla.
