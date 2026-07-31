/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * End-to-end walkthrough of the vehicle return, driven from the real UI.
 *
 * Covers the bugs fixed on 2026-07-30 that only show up in the browser:
 *  - the damage painter opens from inside the return dialog,
 *  - closing it comes back to the return instead of dropping everything,
 *  - the painter re-initialises on every dialog (MutationObserver),
 *  - the wizard keeps what was typed across the round trip.
 */

const drawOnCanvas = () => {
    const dialog = [...document.querySelectorAll(".modal")].pop();
    const canvas = dialog.querySelector("#damage_canvas");
    const rect = canvas.getBoundingClientRect();
    const at = (x, y) => ({
        bubbles: true,
        clientX: rect.left + x,
        clientY: rect.top + y,
    });
    canvas.dispatchEvent(new MouseEvent("mousedown", at(100, 100)));
    canvas.dispatchEvent(new MouseEvent("mousemove", at(180, 160)));
    canvas.dispatchEvent(new MouseEvent("mouseup", at(180, 160)));
};

registry.category("web_tour.tours").add("vehicle_return_flow_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "El contrato de prueba está en curso",
            trigger: ".o_form_view .o_field_widget[name='reference_no']",
            run: () => {},
        },
        {
            content: "Abrir el asistente de devolución",
            trigger: "button[name='b_in_progress_to_c_return']",
            run: "click",
        },
        {
            content: "El asistente se abre en un diálogo",
            trigger: ".modal .o_field_widget[name='odometer'] input",
            run: "edit 23500",
        },
        {
            content: "Nivel de combustible a la devolución",
            trigger: ".modal .o_field_widget[name='fuel_level'] select",
            run: "select 3",
        },
        {
            content: "Los kilómetros recorridos se calculan en vivo",
            trigger: ".modal .o_field_widget[name='km_driven']:contains('13,500')",
            run: () => {},
        },
        {
            content: "Confirmar la inspección",
            trigger: ".modal .o_field_widget[name='inspection_done'] input",
            run: "click",
        },
        {
            content: "Marcar que el vehículo presenta daños",
            trigger: ".modal .o_field_widget[name='has_damage'] input",
            run: "click",
        },
        {
            content: "Anotar unas notas antes de ir al editor",
            trigger: ".modal .o_field_widget[name='notes'] textarea",
            run: "edit Revisado en el mostrador",
        },
        {
            content: "Abrir el editor de daños",
            trigger: ".modal button[name='action_open_damage_painter']",
            run: "click",
        },
        {
            content: "El editor carga con su canvas",
            trigger: ".modal #damage_canvas",
            run: () => {},
        },
        {
            content: "La referencia del painter está en el DOM (no en la URL)",
            trigger: ".modal .o_damage_painter_ref",
            run: () => {},
        },
        {
            content: "Dibujar una marca",
            trigger: ".modal #damage_canvas",
            run: drawOnCanvas,
        },
        {
            content: "Guardar la imagen",
            trigger: ".modal .o_save_damage_btn",
            run: "click",
        },
        {
            content: "Volver a la devolución",
            trigger: ".modal button[name='action_back_to_wizard']",
            run: "click",
        },
        {
            content: "El asistente reaparece con lo introducido intacto",
            trigger: ".modal .o_field_widget[name='notes'] textarea:value(Revisado en el mostrador)",
            run: () => {},
        },
        {
            content: "Y con las marcas pintadas",
            trigger: ".modal .o_field_widget[name='painted_damage_image'] img",
            run: () => {},
        },
        {
            content: "Reabrir el editor: debe volver a inicializarse",
            trigger: ".modal button[name='action_open_damage_painter']",
            run: "click",
        },
        {
            content: "El canvas del segundo diálogo también está vivo",
            trigger: ".modal #damage_canvas",
            run: drawOnCanvas,
        },
        {
            content: "Guardar de nuevo",
            trigger: ".modal .o_save_damage_btn",
            run: "click",
        },
        {
            content: "Volver otra vez a la devolución",
            trigger: ".modal button[name='action_back_to_wizard']",
            run: "click",
        },
        {
            content: "Describir los daños",
            trigger: ".modal .o_field_widget[name='damage_description'] .odoo-editor-editable",
            run: "editor Rayón en la puerta delantera",
        },
        {
            content: "No enviar el correo de cierre en la prueba",
            trigger: ".modal .o_field_widget[name='send_closing_email'] input:checked",
            run: "click",
        },
        {
            content: "Confirmar la devolución sin valorar el importe",
            trigger: ".modal button[name='action_confirm_return']",
            run: "click",
        },
        {
            content: "El contrato queda en Devuelto",
            trigger: ".o_form_view .o_statusbar_status button[data-value='c_return'].o_arrow_button_current",
            run: () => {},
        },
        {
            content: "Y muestra la devolución registrada",
            trigger: "button[name='action_view_returns']:contains('1')",
            run: () => {},
        },
    ],
});
