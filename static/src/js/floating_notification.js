/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FloatingNotification extends Component {
    static template = "vehicle_rental.FloatingNotification";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            count: 0,
            visible: true
        });

        onWillStart(async () => {
            await this.loadCount();
        });

        onMounted(() => {
            // Actualizar el contador cada 30 segundos
            this.interval = setInterval(() => {
                this.loadCount();
            }, 30000);
        });
    }

    async loadCount() {
        try {
            const count = await this.orm.searchCount(
                "crm.lead",
                [["name", "ilike", "%Consulta de Reserva%"], ["stage_id", "=", 1]]
            );
            this.state.count = count;
        } catch (error) {
            console.error("Error loading booking enquiries count:", error);
        }
    }

    async onClick() {
        // Abrir la acción de consultas de reserva
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'crm.lead',
            name: 'Consultas de Reserva',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'], [false, 'form']],
            domain: [['name', 'ilike', '%Consulta de Reserva%'], ['stage_id', '=', 1]],
            context: {},
        });
    }

    willUnmount() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }
}

// Registrar el componente en el systray (barra superior) pero como componente flotante
registry.category("main_components").add("FloatingNotification", {
    Component: FloatingNotification,
});

