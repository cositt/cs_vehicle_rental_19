/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DelayNotification extends Component {
    static template = "vehicle_rental.DelayNotification";

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
            // Calcular la fecha límite: ahora + 2 horas
            // Usamos el formato que Odoo espera: YYYY-MM-DD HH:MM:SS
            const now = new Date();
            const twoHoursFromNow = new Date(now.getTime() + (2 * 60 * 60 * 1000));
            
            // Formatear la fecha en formato local (no UTC) para que coincida con la zona horaria del servidor
            const year = twoHoursFromNow.getFullYear();
            const month = String(twoHoursFromNow.getMonth() + 1).padStart(2, '0');
            const day = String(twoHoursFromNow.getDate()).padStart(2, '0');
            const hours = String(twoHoursFromNow.getHours()).padStart(2, '0');
            const minutes = String(twoHoursFromNow.getMinutes()).padStart(2, '0');
            const seconds = String(twoHoursFromNow.getSeconds()).padStart(2, '0');
            const limitDate = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            
            // Buscar contratos en progreso que ya pasaron la fecha de devolución o están a punto de pasar (dentro de 2 horas)
            const count = await this.orm.searchCount(
                "vehicle.contract",
                [
                    ["status", "=", "b_in_progress"],
                    ["end_date", "<=", limitDate]
                ]
            );
            this.state.count = count;
        } catch (error) {
            console.error("Error loading delayed contracts count:", error);
        }
    }

    async onClick() {
        // Calcular la fecha límite: ahora + 2 horas
        const now = new Date();
        const twoHoursFromNow = new Date(now.getTime() + (2 * 60 * 60 * 1000));
        
        // Formatear la fecha en formato local (no UTC) para que coincida con la zona horaria del servidor
        const year = twoHoursFromNow.getFullYear();
        const month = String(twoHoursFromNow.getMonth() + 1).padStart(2, '0');
        const day = String(twoHoursFromNow.getDate()).padStart(2, '0');
        const hours = String(twoHoursFromNow.getHours()).padStart(2, '0');
        const minutes = String(twoHoursFromNow.getMinutes()).padStart(2, '0');
        const seconds = String(twoHoursFromNow.getSeconds()).padStart(2, '0');
        const limitDate = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        
        // Abrir la vista de contratos filtrada por retrasos
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'vehicle.contract',
            name: 'Contratos con Retraso',
            view_mode: 'kanban,form',
            views: [[false, 'kanban'], [false, 'form']],
            domain: [
                ['status', '=', 'b_in_progress'],
                ['end_date', '<=', limitDate]
            ],
            context: {},
        });
    }

    willUnmount() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }
}

// Registrar el componente en el registry
registry.category("main_components").add("DelayNotification", {
    Component: DelayNotification,
});

