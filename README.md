# spider-notify

> ⚠️ **Solo Linux.** Hecho y probado en CachyOS (Arch Linux) + KDE Plasma 6. No
> se sabe si funciona en otras distros de Linux — no funciona en Windows ni macOS.

Demonio de notificaciones para KDE Plasma 6, con icono propio, arriba de la pantalla, estilo oscuro/lavanda.

## Por qué existe

KDE Plasma 6 en Wayland no pre-registra `org.freedesktop.Notifications` al arrancar la sesión — usa activación por D-Bus (`plasma_waitforname`), y a veces ninguna implementación termina quedándose con ese nombre de bus. Este proyecto registra el servicio de notificaciones de escritorio (`org.freedesktop.Notifications`) él mismo, dibujando las notificaciones con PyQt6 en vez de depender del sistema por defecto.

Funciona como reemplazo genérico: cualquier notificación del sistema (`notify-send`, apps, etc.) la recoge y la pinta con este estilo.

## Icono

El original de mi propia instalación usa un icono de Spider-Man generado con IA — no lo incluyo aquí por posibles derechos de imagen de Marvel. Pon tu propio PNG (cuadrado, fondo transparente recomendado) en `~/.local/share/icons/notify-icon.png`, o cambia la ruta con la variable de entorno `NOTIFY_ICON_PATH`. Sin icono también funciona (deja el hueco en blanco).

## Instalación

1. Copia `spider-notify.py` a tu `$HOME`.
2. Copia `notify-daemon.service` a `~/.config/systemd/user/` y actívalo:
   ```bash
   systemctl --user enable --now notify-daemon.service
   ```
3. Prueba con:
   ```bash
   notify-send "Título" "Cuerpo del mensaje"
   ```

## Notas técnicas

- Necesita `QT_QPA_PLATFORM=xcb` (viene en el `.service`) porque en Wayland nativo `setGeometry`/animaciones de posición de KDE Plasma se ignoran.
- Usa coordenadas absolutas del escritorio virtual (`screen.x()`/`screen.y()`) para funcionar bien en setups multi-monitor.
- Apila varias notificaciones activas a la vez, reordenándolas con animación al cerrarse una.

## Requisitos

Python 3, `python-dbus`, `python-gobject`, PyQt6.

---

Hecho con ayuda de IA (Claude Code). Puede tener fallos en configuraciones distintas a la mía (otro gestor de ventanas, un solo monitor, otra versión de Plasma) — si algo no pinta bien, lo primero es mirar `journalctl --user -u notify-daemon.service`.
