#!/usr/bin/env python3
"""
Minador local: instrucciones para ejecutar en tu PC sin dependencias de cloud.
"""
print("""
════════════════════════════════════════════════════════════════════════════
                    PROSPECTOR MINE - INSTRUCCIONES
════════════════════════════════════════════════════════════════════════════

El minador necesita Playwright/Patchright instalado en tu PC (no en cloud).

PASOS:

1. Abre PowerShell como Administrador en tu PC

2. Navega a tu carpeta Prospector:
   cd "F:\.Proyectos\.LandingPage\Prospector"

3. Instala las dependencias (tarda ~5-10 min en primera ejecución):
   py -m pip install patchright playwright scrapling
   py -m patchright install chromium

4. Ejecuta el minador:
   py -m prospector mine "Clinicas La Plata"

ALTERNATIVA (si tienes problemas con patchright):
   py -m pip install playwright
   py -m playwright install
   py -m prospector mine "Clinicas La Plata"

════════════════════════════════════════════════════════════════════════════
""")
