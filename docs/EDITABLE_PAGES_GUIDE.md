# Guía: Haciendo Páginas Completamente Editables en Odoo

## Problema Inicial
Las plantillas XML de Odoo no eran editables desde el CMS visual. Los usuarios no podían modificar estilos, textos o contenido de las tarjetas y secciones.

## Causa Raíz
1. **Etiquetas Odoo `<t>` incompatibles**: Las etiquetas `<t>` (template tags) no son reconocidas por el editor CMS
2. **Falta de clase `o_editable`**: Sin esta clase, Odoo no marca elementos como editables
3. **Estructura incorrecta**: Los elementos no estaban envueltos en secciones HTML válidas

## Solución Implementada

### Paso 1: Convertir `<div>` en `<section>`
```xml
<!-- ❌ INCORRECTO -->
<div class="container py-5">
    <div class="col-lg-4"><h1>Título</h1></div>
</div>

<!-- ✅ CORRECTO -->
<section class="container py-5 o_editable">
    <div class="col-lg-4"><h1>Título</h1></div>
</section>
```

### Paso 2: Agregar clase `o_editable`
```xml
<!-- A nivel de sección principal -->
<section class="hero-section o_editable">
    
<!-- A nivel de elementos individuales (cards) -->
<div class="card o_editable">
    
<!-- A nivel de contenedor de múltiples items -->
<section class="container py-5 o_editable">
```

### Paso 3: Evitar Lógica de Plantilla Dentro
```xml
<!-- ❌ NO MEZCLAR CON LÓGICA ODOO DENTRO DE SECCIONES EDITABLES -->
<section class="o_editable">
    <t t-foreach="items" t-as="item">
        <div t-esc="item.name"/>
    </t>
</section>

<!-- ✅ USAR HTML PURO PARA EDITABLE -->
<section class="o_editable">
    <div>
        <h5>Titulo Fijo</h5>
        <p>Contenido Editable</p>
    </div>
</section>
```

## Archivos Modificados

### Completamente Editables
- `views/templates/sunset_home_basic.xml` - Hero, categorías, delegaciones, CTA
- `views/templates/sunset_services_page.xml` - Hero, 3 servicios, CTA
- `views/templates/sunset_contact_basic.xml` - Hero, info contacto, formulario

### Parcialmente (en progreso)
- `views/templates/sunset_home_page.xml` - Necesita mismo tratamiento
- `views/templates/sunset_home_simple.xml` - Necesita mismo tratamiento

### Para Pinveco (pendiente)
- `views/templates/pinveco_home_basic.xml`
- `views/templates/pinveco_contact_basic.xml`
- `views/templates/pinveco_services_page.xml`

## Problemas Encontrados

### 1. **XML Malformado al Eliminar Cards**
**Problema**: Al eliminar cards con sed, quedaron divs sin cerrar
**Síntoma**: Error `XMLSyntaxError: Opening and ending tag mismatch`
**Solución**: Reescribir completamente el archivo manteniendo estructura balanceada

### 2. **Atributos `data-oe-field` Innecesarios**
**Problema**: Usar `data-oe-field="arch"` no funcionaba
**Síntoma**: Todavía mostraba "Seleccione un bloque..."
**Solución**: Solo usar `class="o_editable"` es suficiente

### 3. **Etiquetas `<t>` Bloquean Edición**
**Problema**: Usar `<t t-set>` o `<t t-call>` dentro de `o_editable` causa problemas
**Síntoma**: El CMS no detectaba los elementos como editables
**Solución**: Mantener `<t>` solo al nivel superior, HTML puro dentro de secciones

### 4. **Necesidad de Incrementar Versión**
**Problema**: Odoo cachea vistas
**Solución**: Cambiar versión en `__manifest__.py` (19.0.5.7 → 19.0.5.8)
**Comando**: `sed -i 's/"19.0.5.7"/"19.0.5.8"/' __manifest__.py`

### 5. **Reiniciar Odoo después de cambios**
**Problema**: Los cambios no se reflejan sin reiniciar
**Solución**: `sudo docker restart odoo-sunsetrentpinveco && sleep 15`

## Proceso Recomendado para Nuevas Páginas

1. Identificar todas las secciones (Hero, Cards, CTA, etc)
2. Envolver cada sección en `<section>` con `o_editable`
3. Envolver cada tarjeta individual con `o_editable`
4. Verificar que NO haya etiquetas `<t>` con lógica dentro de secciones editables
5. Incrementar versión en `__manifest__.py`
6. Reiniciar Odoo
7. Probar en CMS

## Patrones Correctos

### Hero Section
```xml
<section class="hero-section o_editable" style="...">
    <div class="container">
        <h1>Título Editable</h1>
        <p>Descripción Editable</p>
    </div>
</section>
```

### Grid de Cards
```xml
<section class="container py-5 o_editable">
    <div class="row g-4">
        <div class="col-lg-4">
            <div class="card o_editable">
                <div class="card-body">
                    <!-- Contenido -->
                </div>
            </div>
        </div>
    </div>
</section>
```

### CTA Final
```xml
<section class="cta-section py-5 o_editable" style="...">
    <div class="container text-center">
        <h2>Call to Action Editable</h2>
        <p>Descripción</p>
        <a href="...">Botón</a>
    </div>
</section>
```

## Versiones de Módulo

- 19.0.5.6: Agregar `o_editable` simple (no funcionó)
- 19.0.5.7: Convertir a `<section>` (funcionó)
- 19.0.5.8: Agregar servicios y contacto editables

## Próximos Pasos

1. **Completar Sunset**: sunset_home_page.xml, sunset_home_simple.xml
2. **Crear Pinveco**: Copiar archivos de Sunset con colores azules (#0066B3, #4a90e2)
3. **Sincronizar**: Asegurar que actualizaciones de contenido se reflejen en ambas

## Diferencias de Color por Empresa

- **Sunset**: Gradiente dorado (#FFD700 → #FFA500), botones negros (#000000)
- **Pinveco**: Gradiente azul (#0066B3 → #4a90e2), botones azules

## Comandos Útiles

```bash
# Cambiar versión
sed -i 's/"19.0.5.X"/"19.0.5.Y"/' __manifest__.py

# Reiniciar Odoo
sudo docker restart odoo-sunsetrentpinveco && sleep 15

# Verificar sintaxis XML
python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.xml'); print('OK')"

# Ver cambios de git
git diff views/templates/file.xml
```

