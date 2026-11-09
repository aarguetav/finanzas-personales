# Secretos y rotación

La aplicación todavía no tiene autenticación ni aislamiento de usuarios y no
está lista para desplegarse públicamente, aunque `FINANZAS_ENV=production`
desactive la documentación de la API.

| Variable | Uso actual | Tratamiento |
|---|---|---|
| `SECRET_KEY` | Obligatoria en producción; reservada para la configuración de seguridad de las fases posteriores. Todavía no firma ni protege sesiones. | Valor aleatorio y exclusivo de al menos 32 bytes; guardar en el gestor de secretos del entorno, nunca en Git. |

`FINANZAS_ENV` y `FINANZAS_DB` son configuración, no secretos: el primero acepta
`development` o `production` y el segundo apunta a la base. `.env.example` solo
documenta nombres: la aplicación no carga archivos `.env` automáticamente.

## Rotación

1. Genera un valor aleatorio nuevo usando un generador criptográfico en el
   gestor de secretos del entorno; no reutilices el anterior ni lo registres.
2. Actualiza `SECRET_KEY` allí y reinicia el proceso con la nueva configuración.
3. Retira el valor anterior del gestor y revisa quién tuvo acceso. Si pudo
   filtrarse, trátalo como comprometido y revisa también los registros y copias.

Cuando se implementen sesiones, debe definirse y probarse el efecto de la
rotación sobre ellas. No hay usuarios ni credenciales de aplicación todavía.
