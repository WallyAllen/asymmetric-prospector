#!/usr/bin/env python3
"""
Minador sin browser: búsqueda via Google Maps API simulation.
Crea leads FICTICIOS solo para demostrar el formato del pipeline.

ADVERTENCIA: esto no es minería real. El resultado se escribe en
data/demo/, nunca en data/01_raw/, para que no pueda colarse en
`prospector audit` ni mezclarse con leads reales. No lo apuntes
manualmente a leads_crudos.json.
"""
import json
from datetime import datetime
from pathlib import Path

# Datos de ejemplo para Clínicas La Plata
leads_demo = [
    {
        "id": "clinica_medica_plata_1",
        "nombre": "Clínica Médica La Plata",
        "url": "https://clinicamedicalaplata.com.ar",
        "email": "contacto@clinicamedicalaplata.com.ar",
        "emails": ["contacto@clinicamedicalaplata.com.ar"],
        "telefono": "+54 221 424 5678",
        "direccion": "Calle 7 y 45, La Plata",
        "categoria": "Clínica",
        "rating": 4.2,
        "resenas": 28,
        "nicho": "clínicas",
        "fuente": "google_maps_demo",
        "tiene_web": True,
        "estado": "crudo",
        "creado_el": datetime.now().isoformat()
    },
    {
        "id": "clinica_integral_plata",
        "nombre": "Clínica Integral La Plata",
        "url": "https://clinicaintegralplata.ar",
        "email": "info@clinicaintegralplata.ar",
        "emails": ["info@clinicaintegralplata.ar"],
        "telefono": "+54 221 532 1234",
        "direccion": "Avenida 1 esq. Calle 60, La Plata",
        "categoria": "Clínica",
        "rating": 4.5,
        "resenas": 42,
        "nicho": "clínicas",
        "fuente": "google_maps_demo",
        "tiene_web": True,
        "estado": "crudo",
        "creado_el": datetime.now().isoformat()
    },
    {
        "id": "clinica_del_plata",
        "nombre": "Clínica del Plata",
        "url": "https://clinicadelplata.com.ar",
        "email": "atencion@clinicadelplata.com.ar",
        "emails": ["atencion@clinicadelplata.com.ar"],
        "telefono": "+54 221 789 3456",
        "direccion": "Calle 72 y 9, La Plata",
        "categoria": "Clínica",
        "rating": 4.8,
        "resenas": 156,
        "nicho": "clínicas",
        "fuente": "google_maps_demo",
        "tiene_web": True,
        "estado": "crudo",
        "creado_el": datetime.now().isoformat()
    },
    {
        "id": "centro_salud_plata",
        "nombre": "Centro de Salud Plata",
        "url": "https://centrosalud-plata.com.ar",
        "email": "contactos@centrosalud-plata.com.ar",
        "emails": ["contactos@centrosalud-plata.com.ar"],
        "telefono": "+54 221 456 7890",
        "direccion": "Diagonal 79 esq. Calle 7, La Plata",
        "categoria": "Clínica",
        "rating": 4.3,
        "resenas": 65,
        "nicho": "clínicas",
        "fuente": "google_maps_demo",
        "tiene_web": True,
        "estado": "crudo",
        "creado_el": datetime.now().isoformat()
    }
]

# Deliberadamente FUERA de data/01_raw/: nunca debe poder confundirse
# con una corrida real ni quedar disponible para `prospector audit`.
output_file = Path("data/demo/leads_demo.json")
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(leads_demo, f, indent=2, ensure_ascii=False)

print(f"✅ {len(leads_demo)} leads DE PRUEBA creados en: {output_file}")
print("   (ficticios — no auditar ni componer correos reales a partir de esto)")
print()
for lead in leads_demo:
    print(f"  • {lead['nombre']}")
    print(f"    {lead['url']}")
    print()
