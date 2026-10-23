# Auditoría de seguridad — 2026-09-02

Este directorio fue incluido en la auto-auditoría del Mac del 2026-09-02.

**Informe completo:** `~/Desktop/auto-auditoria del mac/AUDITORIA-SEGURIDAD-2026-09-02.md`

## Estado del repositorio

- Remote: `git@github.com-cositt:cositt/cs_vehicle_rental_19.git`
- Cambios sin commitear en el momento de la auditoría: 1
- Auditado en busca de secretos versionados el 2026-09-02.

## Reglas vigentes

1. No commitear `.env`, `*.pem`, `*.p12`, `id_rsa*` ni `odoo.conf` con
   valores reales.
2. No volcar valores de credenciales en el chat, en logs ni en ficheros nuevos.
3. Los certificados bajo `l10n_*`, `odoo-19.0/` y `enterprise-19.0/` son
   fixtures de test públicos de Odoo, no son secretos.
