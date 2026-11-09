# Workflows de seguridad

- `gitleaks.yml` descarga una versión fijada, verifica su SHA-256 y revisa el
  historial disponible sin publicar hallazgos sensibles en el log.
- `codeql.yml` analiza Python y falla si encuentra resultados. Por el permiso
  mínimo `contents: read`, los resultados no se suben a Code Scanning; se deben
  investigar localmente si falla.

Los workflows verifican el historial y código que GitHub entrega al runner;
no sustituyen la revisión de datos personales ni la auditoría previa a publicar.
