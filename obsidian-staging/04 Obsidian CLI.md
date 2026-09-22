---
title: Obsidian CLI
tipo: herramienta
estado: configuracion-pendiente
tags:
  - landingpage
  - infraestructura
  - obsidian
  - cli
---

# Obsidian CLI

## Para qué se incorpora

El CLI oficial permite consultar y mantener el vault desde la terminal usando el índice de Obsidian. Evita cargar colecciones enteras de Markdown para operaciones concretas y reduce pasos manuales al crear notas, buscar contexto, comprobar enlaces o consultar propiedades.

No reemplaza la lectura dirigida ni habilita la publicación de información privada: sigue aplicando la separación definida en [[El repo guarda lo que se ejecuta, el vault lo que se sabe]].

## Requisitos y activación

1. Tener Obsidian Desktop 1.12.7 o posterior instalado.
2. Abrir Obsidian y elegir el vault correcto.
3. En **Configuración → General**, habilitar **Command line interface**.
4. Aceptar el registro del comando cuando Obsidian lo solicite.
5. Verificar en una terminal nueva:

```powershell
obsidian version
obsidian vault info=path
```

El CLI necesita la aplicación de Obsidian en ejecución; si no está abierta, el primer comando la inicia.

## Operaciones útiles

```powershell
# Buscar notas sin recorrer todos los archivos
obsidian search query="modelo de negocio" limit=10

# Leer solo una nota conocida
obsidian read path="Modelo LandingPage/00 Modelo LandingPage.md"

# Revisar enlaces sin resolver antes de compartir el vault
obsidian unresolved verbose

# Ver backlinks de una nota para decidir dónde enlazarla
obsidian backlinks file="Modelo LandingPage"

# Crear una nota desde la terminal
obsidian create path="Modelo LandingPage/Nueva nota.md" content="# Nueva nota" silent
```

Usar `path=` para apuntar a una ubicación exacta y `file=` cuando el nombre sea único. Antes de aplicar cambios masivos, usar primero comandos de lectura o reporte.

## Estado de configuración

- **21-09-2026:** se comprobó que el comando no estaba disponible y se obtuvo el instalador oficial de Obsidian 1.13.7.
- Pendiente: completar el instalador y habilitar **Command line interface** desde la configuración de la app; luego ejecutar la verificación anterior.

## Fuente

La guía oficial: [Obsidian CLI](https://help.obsidian.md/cli).
