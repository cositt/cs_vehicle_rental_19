/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

(function() {
    'use strict';

    let canvas = null;
    let ctx = null;
    let isDrawing = false;
    let currentTool = 'pen';
    let currentColor = '#FF0000'; // Rojo
    let lineWidth = 3;
    let fontSize = 16;
    let lastX = 0;
    let lastY = 0;
    let startX = 0;
    let startY = 0;
    let wizardId = null;
    let contractId = null;
    let canvasHistory = [];
    let historyStep = -1;

    async function getContractIdFromOdooForm() {
        // Buscar el contract_id directamente desde el formulario de Odoo usando la API del framework
        try {
            console.log('=== BUSCANDO CONTRACT ID DESDE ODOO ===');
            
            // Método 0: Analizar la URL completa
            const fullHash = window.location.hash;
            console.log('URL Hash completo:', fullHash);
            
            // Buscar active_id en la URL
            if (fullHash.includes('active_id')) {
                const activeIdMatch = fullHash.match(/active_id[=,](\d+)/);
                if (activeIdMatch && activeIdMatch[1]) {
                    contractId = parseInt(activeIdMatch[1]);
                    console.log('✅ Contract ID desde active_id:', contractId);
                    return contractId;
                }
            }
            
            // Buscar id del wizard en la URL
            if (fullHash.includes('id=')) {
                const idMatch = fullHash.match(/[?&]id=(\d+)/);
                if (idMatch && idMatch[1]) {
                    wizardId = parseInt(idMatch[1]);
                    console.log('✅ Wizard ID desde URL:', wizardId);
                    
                    // Ahora que tenemos el wizard ID, hacer una llamada RPC para obtener el contract_id
                    try {
                        console.log('Haciendo llamada RPC al wizard...');
                        const response = await fetch('/web/dataset/call_kw', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                jsonrpc: '2.0',
                                method: 'call',
                                params: {
                                    model: 'vehicle.contract.damage.painter',
                                    method: 'get_contract_id_for_js',
                                    args: [[wizardId]],
                                    kwargs: {}
                                },
                                id: Math.floor(Math.random() * 1000000)
                            })
                        });
                        const result = await response.json();
                        console.log('Respuesta RPC:', result);
                        if (result.result) {
                            contractId = result.result;
                            console.log('✅ Contract ID obtenido desde wizard:', contractId);
                            return contractId;
                        } else {
                            console.error('RPC no devolvió result:', result);
                        }
                    } catch (e) {
                        console.error('Error al obtener contract_id desde wizard:', e);
                    }
                }
            }
            
            // IMPORTANTE: Buscar en el MODAL, no en el formulario de fondo
            const modal = document.querySelector('.modal, .o_dialog');
            console.log('Modal encontrado:', !!modal);
            
            // Buscar el formulario DENTRO del modal
            const formElement = modal ? modal.querySelector('.o_form_view') : document.querySelector('.o_form_view');
            console.log('FormElement en modal:', !!formElement);
            console.log('Tiene __owl__:', formElement ? !!formElement.__owl__ : 'N/A');
            
            if (formElement && formElement.__owl__) {
                console.log('✓ Encontrado __owl__ en formulario');
                const component = formElement.__owl__.component;
                console.log('Component:', !!component);
                
                if (component && component.props && component.props.record) {
                    const record = component.props.record;
                    console.log('✓ Record encontrado');
                    console.log('Record.data:', record.data ? Object.keys(record.data) : 'sin data');
                    console.log('Record.resId:', record.resId);
                    
                    // Buscar contract_id en el record
                    if (record.data && record.data.contract_id) {
                        const contractIdData = record.data.contract_id;
                        console.log('contract_id data:', contractIdData, 'tipo:', typeof contractIdData);
                        
                        if (Array.isArray(contractIdData) && contractIdData.length > 0) {
                            contractId = contractIdData[0];
                            console.log('✅ Contract ID encontrado desde OWL (array):', contractId);
                        } else if (typeof contractIdData === 'number') {
                            contractId = contractIdData;
                            console.log('✅ Contract ID encontrado desde OWL (number):', contractId);
                        }
                    } else {
                        console.log('⚠️ No hay contract_id en record.data');
                    }
                    
                    // También intentar obtener el resId del wizard
                    if (record.resId) {
                        wizardId = record.resId;
                        console.log('✅ Wizard ID encontrado desde OWL:', wizardId);
                    }
                } else {
                    console.log('⚠️ No se encontró component.props.record');
                }
            } else {
                console.log('⚠️ No se encontró __owl__ en formElement');
            }
            
            // Método 2: Buscar en el DOM de forma manual DENTRO DEL MODAL
            const contractFieldDiv = modal ? 
                modal.querySelector('.o_field_widget[name="contract_id"]') : 
                document.querySelector('.o_field_widget[name="contract_id"]');
            console.log('Campo contract_id en DOM del modal:', !!contractFieldDiv);
            
            if (contractFieldDiv && !contractId) {
                console.log('✓ Campo contract_id encontrado en DOM, buscando input...');
                const many2oneInput = contractFieldDiv.querySelector('input');
                console.log('Input many2one:', !!many2oneInput);
                
                if (many2oneInput) {
                    console.log('Input value:', many2oneInput.value);
                    if (many2oneInput.value) {
                        // Extraer el ID del formato "id,nombre"
                        const value = many2oneInput.value;
                        const match = value.match(/^(\d+)/);
                        if (match) {
                            contractId = parseInt(match[1]);
                            console.log('✅ Contract ID desde input many2one:', contractId);
                        }
                    }
                }
            }
            
            // Método 3: Buscar TODOS los campos del formulario DEL MODAL
            console.log('--- Listando TODOS los campos del MODAL ---');
            const allFields = modal ? 
                modal.querySelectorAll('.o_field_widget') : 
                document.querySelectorAll('.o_field_widget');
            console.log(`Total de campos encontrados en modal: ${allFields.length}`);
            allFields.forEach((field, index) => {
                const name = field.getAttribute('name');
                if (name) {
                    console.log(`Campo ${index}: ${name}`);
                }
            });
            
            console.log('=== RESULTADO ===');
            console.log('Contract ID final:', contractId || 'NO ENCONTRADO');
            console.log('Wizard ID final:', wizardId || 'NO ENCONTRADO');
            
            return contractId;
            
        } catch (e) {
            console.error('❌ Error al obtener Contract ID:', e);
            console.error('Stack:', e.stack);
            return null;
        }
    }

    function initDamagePainter() {
        // console.log('Iniciando damage painter...');
        
        // Esperar a que el DOM esté listo
        setTimeout(() => {
            canvas = document.getElementById('damage_canvas');
            if (!canvas) {
                // console.log('Canvas no encontrado, reintentando...');
                // Reintentar
                setTimeout(initDamagePainter, 500);
                return;
            }

            console.log('Canvas encontrado!');
            ctx = canvas.getContext('2d');
            
            // Obtener Contract ID del contexto de Odoo
            getContractIdFromOdooForm();

            // Cargar imagen base
            loadBaseImage();

            // Event listeners para herramientas
            document.querySelectorAll('.damage_tool').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    currentTool = e.currentTarget.dataset.tool;
                    document.querySelectorAll('.damage_tool').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                });
            });

            // Event listeners para colores
            document.querySelectorAll('.damage_color').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    currentColor = e.currentTarget.dataset.color;
                    document.querySelectorAll('.damage_color').forEach(b => b.style.border = 'none');
                    e.currentTarget.style.border = '3px solid black';
                });
            });
            
            // Event listener para input de color
            const colorInput = document.querySelector('.damage_color_input');
            if (colorInput) {
                colorInput.addEventListener('input', (e) => {
                    currentColor = e.target.value;
                });
            }
            
            // Establecer color inicial
            const firstColorBtn = document.querySelector('.damage_color');
            if (firstColorBtn) {
                firstColorBtn.style.border = '3px solid black';
            }
            
            // Botones de Undo y Clear
            const undoBtn = document.querySelector('.damage_undo');
            if (undoBtn) {
                undoBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    // Deshacer: volver al estado anterior
                    if (historyStep > 0) {
                        historyStep--;
                        const img = new Image();
                        img.src = canvasHistory[historyStep];
                        img.onload = () => {
                            ctx.clearRect(0, 0, canvas.width, canvas.height);
                            ctx.drawImage(img, 0, 0);
                        };
                    }
                });
            }
            
            const clearBtn = document.querySelector('.damage_clear');
            if (clearBtn) {
                clearBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (ctx && canvas) {
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        canvasHistory = [];
                        historyStep = -1;
                        loadBaseImage();
                    }
                });
            }

            // Event listener para grosor de línea
            const lineWidthInput = document.querySelector('.damage_line_width');
            if (lineWidthInput) {
                lineWidthInput.addEventListener('input', (e) => {
                    lineWidth = parseInt(e.target.value);
                    document.querySelector('.line_width_display').textContent = e.target.value;
                });
            }

            // Event listener para tamaño de fuente
            const fontSizeInput = document.querySelector('.damage_font_size');
            if (fontSizeInput) {
                fontSizeInput.addEventListener('input', (e) => {
                    fontSize = parseInt(e.target.value);
                    document.querySelector('.font_size_display').textContent = e.target.value;
                });
            }

            // Event listeners del canvas
            canvas.addEventListener('mousedown', startDrawing);
            canvas.addEventListener('mousemove', draw);
            canvas.addEventListener('mouseup', stopDrawing);
            canvas.addEventListener('mouseout', stopDrawing);

            // Touch events para móviles
            canvas.addEventListener('touchstart', handleTouchStart);
            canvas.addEventListener('touchmove', handleTouchMove);
            canvas.addEventListener('touchend', stopDrawing);

            // Botón de descargar imagen
            const downloadBtn = document.querySelector('.o_download_damage_btn');
            if (downloadBtn) {
                downloadBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    downloadCanvasImage();
                });
            }
            
            // Interceptar el botón de guardar - ANTES de enviar el formulario
            const saveBtn = document.querySelector('.o_save_damage_btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', function(e) {
                    saveCanvasImage();
                });
            }

            // Marcar primera herramienta como activa
            const firstTool = document.querySelector('.damage_tool');
            if (firstTool) {
                firstTool.classList.add('active');
            }
        }, 100);
    }

    function saveCanvasState() {
        // Guardar estado actual del canvas
        historyStep++;
        if (historyStep < canvasHistory.length) {
            canvasHistory.length = historyStep;
        }
        canvasHistory.push(canvas.toDataURL());
    }

    function loadBaseImage() {
        console.log('Cargando imagen base...');
        const baseImageField = document.querySelector('input[name="base_image"]');
        console.log('Campo base_image encontrado:', !!baseImageField);
        
        const img = new Image();
        
        img.onload = () => {
            console.log('Imagen cargada exitosamente, dibujando en canvas...');
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            // Guardar estado inicial
            saveCanvasState();
        };
        
        img.onerror = (e) => {
            console.error('Error al cargar imagen:', e);
        };

        if (baseImageField && baseImageField.value) {
            console.log('Usando imagen existente del contrato');
            img.src = 'data:image/png;base64,' + baseImageField.value;
        } else {
            console.log('Usando imagen por defecto: img.png');
            img.src = '/vehicle_rental/static/src/img/img.png';
        }
    }

    function startDrawing(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (currentTool === 'text') {
            const text = prompt('Ingrese el texto:');
            if (text) {
                ctx.font = `${fontSize}px Arial`;
                ctx.fillStyle = currentColor;
                ctx.fillText(text, x, y);
                saveCanvasState();
            }
            return;
        }

        isDrawing = true;
        startX = x;
        startY = y;
        lastX = x;
        lastY = y;
    }

    function draw(e) {
        if (!isDrawing || currentTool === 'text') return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Para pen, dibujar continuamente
        if (currentTool === 'pen') {
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(x, y);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.lineCap = 'round';
            ctx.stroke();
            lastX = x;
            lastY = y;
        } else {
            // Para figuras (circle, rectangle, arrow), mostrar preview
            if (canvasHistory.length > 0) {
                const img = new Image();
                img.src = canvasHistory[historyStep];
                img.onload = () => {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);
                    
                    // Dibujar preview de la figura
                    ctx.strokeStyle = currentColor;
                    ctx.fillStyle = currentColor;
                    ctx.lineWidth = lineWidth;
                    
                    if (currentTool === 'circle') {
                        const radius = Math.sqrt(Math.pow(x - startX, 2) + Math.pow(y - startY, 2));
                        ctx.beginPath();
                        ctx.arc(startX, startY, radius, 0, 2 * Math.PI);
                        ctx.stroke();
                    } else if (currentTool === 'rectangle') {
                        ctx.strokeRect(startX, startY, x - startX, y - startY);
                    } else if (currentTool === 'arrow') {
                        drawArrow(startX, startY, x, y);
                    }
                };
            }
        }
    }

    function stopDrawing(e) {
        if (!isDrawing) return;
        
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Dibujar figura final
        if (currentTool === 'circle') {
            const radius = Math.sqrt(Math.pow(x - startX, 2) + Math.pow(y - startY, 2));
            ctx.beginPath();
            ctx.arc(startX, startY, radius, 0, 2 * Math.PI);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.stroke();
            saveCanvasState();
        } else if (currentTool === 'rectangle') {
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.strokeRect(startX, startY, x - startX, y - startY);
            saveCanvasState();
        } else if (currentTool === 'arrow') {
            drawArrow(startX, startY, x, y);
            saveCanvasState();
        } else if (currentTool === 'pen') {
            saveCanvasState();
        }
        
        isDrawing = false;
    }

    function drawArrow(fromX, fromY, toX, toY) {
        const headlen = 15;
        const angle = Math.atan2(toY - fromY, toX - fromX);

        ctx.beginPath();
        ctx.moveTo(fromX, fromY);
        ctx.lineTo(toX, toY);
        ctx.strokeStyle = currentColor;
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - headlen * Math.cos(angle - Math.PI / 6), toY - headlen * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - headlen * Math.cos(angle + Math.PI / 6), toY - headlen * Math.sin(angle + Math.PI / 6));
        ctx.stroke();
    }

    function handleTouchStart(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();
        const mouseEvent = new MouseEvent('mousedown', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        canvas.dispatchEvent(mouseEvent);
    }

    function handleTouchMove(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        canvas.dispatchEvent(mouseEvent);
    }

    function downloadCanvasImage() {
        if (!canvas) {
            alert('Error: Canvas no encontrado');
            return;
        }
        
        try {
            // Convertir canvas a blob
            canvas.toBlob(function(blob) {
                // Crear URL temporal
                const url = URL.createObjectURL(blob);
                
                // Crear elemento <a> temporal para descargar
                const link = document.createElement('a');
                link.href = url;
                link.download = `danos_vehiculo_${new Date().getTime()}.png`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Liberar el URL
                URL.revokeObjectURL(url);
                
                alert('✅ Imagen descargada correctamente');
            }, 'image/png');
        } catch (error) {
            console.error('Error al descargar imagen:', error);
            alert('Error al descargar la imagen: ' + error.message);
        }
    }
    
    async function saveCanvasImage() {
        if (!canvas) {
            alert('❌ Canvas no encontrado');
            return;
        }
        
        console.log('=== INICIO GUARDADO ===');
        
        try {
            const fullUrl = window.location.href;
            console.log('URL:', fullUrl);
            
            // Convertir imagen a base64
            const base64Data = canvas.toDataURL('image/png').split(',')[1];
            console.log('✅ Imagen:', base64Data.length, 'bytes');
            
            // DETECTAR SI ESTAMOS EN EL WIZARD DE SUSTITUCIÓN
            const isSubstitutionWizard = fullUrl.includes('vehicle.substitution.damage.painter');
            console.log('¿Es wizard de sustitución?', isSubstitutionWizard);
            
            if (isSubstitutionWizard) {
                // GUARDAR EN EL WIZARD DE SUSTITUCIÓN
                // Obtener el ID del wizard painter desde la URL
                const wizardIdMatch = fullUrl.match(/vehicle\.substitution\.damage\.painter\/(\d+)/);
                if (!wizardIdMatch) {
                    alert('❌ No se pudo encontrar el ID del wizard');
                    return;
                }
                const painterId = parseInt(wizardIdMatch[1]);
                console.log('✅ Painter ID:', painterId);
                
                // Llamar al método save_image_to_wizard
                const saveResp = await fetch('/web/dataset/call_kw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            model: 'vehicle.substitution.damage.painter',
                            method: 'save_image_to_wizard',
                            args: [[painterId], base64Data],
                            kwargs: {}
                        },
                        id: Date.now()
                    })
                });
                
                const saveRes = await saveResp.json();
                console.log('Respuesta:', saveRes);
                
                if (saveRes.error) {
                    alert('❌ ' + (saveRes.error.data?.message || saveRes.error.message));
                } else if (saveRes.result && saveRes.result.success) {
                    console.log('✅ ¡GUARDADO EN WIZARD!');
                    
                    // Mostrar mensaje de éxito sin cerrar el modal
                    // El usuario lo cerrará manualmente cuando termine
                    const successMsg = document.createElement('div');
                    successMsg.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 15px 25px; border-radius: 5px; z-index: 99999; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);';
                    successMsg.innerHTML = '<i class="fa fa-check-circle"></i> Imagen guardada correctamente. Puedes cerrar el editor.';
                    document.body.appendChild(successMsg);
                    
                    setTimeout(() => {
                        successMsg.remove();
                    }, 5000);
                } else {
                    alert('❌ Error al guardar: ' + (saveRes.result?.message || 'Error desconocido'));
                }
                
            } else {
                // GUARDAR EN EL CONTRATO (lógica original)
                let finalContractId = null;
                
                // Método 1: Desde la variable global
                if (contractId) {
                    finalContractId = contractId;
                    console.log('✅ Contract ID (variable global):', finalContractId);
                }
                
                // Método 2: Extraer de la URL
                if (!finalContractId) {
                    const urlMatch = fullUrl.match(/vehicle\.contract\/(\d+)/);
                    if (urlMatch) {
                        finalContractId = parseInt(urlMatch[1]);
                        console.log('✅ Contract ID (URL):', finalContractId);
                    }
                }
                
                // Método 3: Buscar en el DOM
                if (!finalContractId) {
                    const allForms = document.querySelectorAll('.o_form_view');
                    for (const form of allForms) {
                        if (form.__owl__) {
                            const record = form.__owl__.component?.props?.record;
                            if (record && record.resModel === 'vehicle.contract' && record.resId) {
                                finalContractId = record.resId;
                                console.log('✅ Contract ID (DOM):', finalContractId);
                                break;
                            }
                        }
                    }
                }
                
                if (!finalContractId) {
                    alert('❌ No se pudo encontrar el ID del contrato');
                    return;
                }

                console.log('✅ Contract ID FINAL:', finalContractId);

                // Guardar en el contrato
                const saveResp = await fetch('/web/dataset/call_kw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            model: 'vehicle.contract',
                            method: 'write',
                            args: [[finalContractId], {painted_damage_image: base64Data}],
                            kwargs: {}
                        },
                        id: Date.now()
                    })
                });

                const saveRes = await saveResp.json();
                console.log('Respuesta guardado:', saveRes);

                if (saveRes.error) {
                    alert('❌ ' + (saveRes.error.data?.message || saveRes.error.message));
                } else if (saveRes.result) {
                    alert('✅ Imagen guardada correctamente');
                    console.log('✅ ¡GUARDADO EXITOSO!');
                    
                    // Cerrar el modal
                    setTimeout(() => {
                        const closeBtn = document.querySelector('.modal button[special="cancel"]');
                        if (closeBtn) closeBtn.click();
                    }, 300);
                    
                    // Recargar el formulario del contrato
                    setTimeout(() => {
                        const allForms = document.querySelectorAll('.o_form_view');
                        for (const form of allForms) {
                            if (form.__owl__) {
                                const component = form.__owl__.component;
                                const record = component?.props?.record;
                                if (record && record.resModel === 'vehicle.contract') {
                                    if (component.model && component.model.root) {
                                        component.model.root.load();
                                    }
                                    break;
                                }
                            }
                        }
                    }, 800);
                }
            }
        } catch (error) {
            console.error('ERROR:', error);
            alert('❌ ' + error.message);
        }
    }

    // Inicializar cuando el documento esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDamagePainter);
    } else {
        initDamagePainter();
    }

    // También inicializar en cambios de vista de Odoo
    if (window.addEventListener) {
        window.addEventListener('load', initDamagePainter);
    }

})();

