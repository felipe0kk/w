# STEAM KEY HUNTER V2.1

Aplicación local para consultar promociones de juegos de Steam desde GamerPower. Incluye búsqueda automática, búsqueda manual, filtros, favoritos y base de datos local.

## Obtener el EXE sin instalar Python en tu PC

Este proyecto incluye un flujo de compilación en GitHub Actions. GitHub compila el ejecutable en un equipo Windows y permite descargarlo como artefacto.

1. Crea un repositorio nuevo en https://github.com/new.
2. Sube el contenido completo de esta carpeta al repositorio (incluida la carpeta `.github`).
3. En GitHub abre la pestaña **Actions**.
4. Selecciona **Build Windows EXE** y pulsa **Run workflow**.
5. Cuando termine en verde, abre esa ejecución y descarga **SteamKeyHunter-Windows** en la sección Artifacts.
6. Descomprime el artefacto y ejecuta `SteamKeyHunter.exe`.

No necesitas instalar Python para ejecutar el EXE. La compilación sí se realiza en los servidores Windows de GitHub. Si prefieres compilar localmente, instala Python 3.10+ y ejecuta `build_windows.bat`.

## Funciones

- Consulta promociones de Steam desde la API pública de GamerPower.
- Actualización automática cada 15 minutos y botón de búsqueda manual.
- Filtros: todas, posibles claves/sorteos y favoritos.
- Búsqueda por título y descripción.
- Favoritos persistentes en SQLite.
- Abre la interfaz en el navegador en `http://127.0.0.1:5187`.

## Importante

La etiqueta «posible clave / sorteo» es una clasificación por palabras del anuncio; no garantiza que el premio sea una clave directa ni que siga disponible. Verifica siempre la fuente original, región, requisitos y fecha. La aplicación no genera claves, no accede a cuentas Steam ni reclama premios automáticamente.

Datos locales: `%LOCALAPPDATA%\\SteamKeyHunter\\steam_key_hunter_v2.db`.
Fuente: https://www.gamerpower.com/ — API: https://www.gamerpower.com/api-read
