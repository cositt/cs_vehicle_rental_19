/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";

const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;
import { loadJS, loadCSS } from "@web/core/assets"

class VehicleRentalDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            fleetVehicleStats: { 'total_vehicle': 0, 'available_vehicle': 0, 'under_maintenance_vehicle': 0 },
            vehicleContractStatus: { 'draft_vehicle': 0, 'in_progress_vehicle': 0, 'return_contract': 0, 'cancel_contract': 0 },
            vehicleCustomers: { 'customers': 0 },
            customerInvoices: { 'customer_invoice': 0, 'pending_invoices': 0 },
            rentContractDurations: { 'data': [] },
            invoiceStatusGraph: { 'x-axis': [], 'y-axis': [] },
        });

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });

        this.contractDurations = useRef('rent_contract_duration');
        this.invoiceStatusGraph = useRef('invoice_status_graph');

        onWillStart(async () => {

            let vehicleRentalData = await this.orm.call('vehicle.rental.dashboard', 'get_vehicle_rental_dashboard', []);
            if (vehicleRentalData) {
                this.state.fleetVehicleStats = vehicleRentalData;
                this.state.vehicleContractStatus = vehicleRentalData;
                this.state.vehicleCustomers = vehicleRentalData;
                this.state.customerInvoices = vehicleRentalData;
                this.state.rentContractDurations = { 'data': vehicleRentalData['rent_duration'] };
                this.state.invoiceStatusGraph = { 'x-axis': vehicleRentalData['rent_invoice_month'][0], 'y-axis': vehicleRentalData['rent_invoice_month'][1] };
            }
        });
        onMounted(() => {
            this.renderContractDurationsGraph();
            this.renderInvoiceStatusGraph(this.invoiceStatusGraph.el, this.state.invoiceStatusGraph);
        })
    }

    viewFleetVehicleDetails(status) {
        let domain, context;
        let fleetState = this.getFleetState(status);
        if (status === 'all') {
            domain = []
        } else {
            domain = [['status', '=', status]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: fleetState,
            res_model: 'fleet.vehicle',
            view_mode: 'kanban',
            views: [[false, 'list'], [false, 'form'], [false, 'kanban']],
            target: 'current',
            domain: domain,
            context: context,
        });
    }

    getFleetState(status) {
        let fleetState;
        if (status === 'all') {
            fleetState = 'Vehículos Totales'
        } else if (status === 'available') {
            fleetState = 'Vehículos Operacionales'
        } else if (status === 'in_maintenance') {
            fleetState = 'Vehículos en Mantenimiento'
        }
        return fleetState;
    }

    viewVehicleContractStatus(status) {
        let domain, context;
        let contracts = this.getContractState(status);
        if (status === 'all') {
            domain = []
        } else {
            domain = [['status', '=', status]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: contracts,
            res_model: 'vehicle.contract',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'pivot'], [false, 'activity'], [false, 'search']],
            target: 'current',
            domain: domain,
            context: context,
        });
    }

    getContractState(status) {
        let contracts;
        if (status === 'all') {
            contracts = 'Contratos'
        } else if (status === 'b_in_progress') {
            contracts = 'Contratos en Progreso'
        } else if (status === 'c_return') {
            contracts = 'Contratos Devueltos'
        } else if (status === 'd_cancel') {
            contracts = 'Contratos Cancelados'
        }
        return contracts;
    }

    viewVehicleCustomers() {
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Clientes',
            res_model: 'res.partner',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'activity']],
            target: 'current',
            context: context,
        });
    }
    viewCustomerInvoices() {
        let domain = [['vehicle_contract_id', '!=', false], ['move_type', '=', 'out_invoice']];
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Todas las Facturas',
            domain: domain,
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form'], [false, 'kanban'], [false, 'activity']],
            target: 'current',
            context: context,
        });
    }
    viewPendingInvoices() {
        let domain = [['payment_state', '!=', 'paid'], ['vehicle_contract_id', '!=', false], ['move_type', '=', 'out_invoice']];
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Facturas Pendientes',
            res_model: 'account.move',
            domain: domain,
            views: [[false, 'list'], [false, 'form'], [false, 'kanban'], [false, 'activity']],
            target: 'current',
            context: context,
        });
    }

    renderGraph(el, options) {
        const graphData = new ApexCharts(el, options);
        graphData.render();
    }

    renderContractDurationsGraph() {
        let contract_data = []
        let data = this.state.rentContractDurations['data']
        for (const ss of data) {
            contract_data.push({
                'name': ss['name'],
                'data': [{
                    'x': 'Duración de Contrato',
                    'y': [new Date(ss['start_date']).getTime(), new Date(ss['end_date']).getTime()],
                }]
            })
        }
        const options = {
            series: contract_data,
            chart: {
                height: 430,
                type: 'rangeBar',
            },
            plotOptions: {
                bar: {
                    horizontal: true
                }
            },
            colors: ['#71D3FA', '#98AFF8', '#AC9DF8', '#C08AF7', '#D378F6', '#E766F5'],
            dataLabels: {
                enabled: true,
                formatter: function (val) {
                    var a = new Date(val[0])
                    var b = new Date(val[1])
                    var diff = Math.floor((b - a) / (1000 * 60 * 60 * 24)); // Difference in days
                    return diff + (diff > 1 ? ' days' : ' day');
                },
                style: {
                    colors: ['#273029'],
                },
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shade: 'white',
                    type: "horizontal",
                    gradientToColors: undefined,
                    inverseColors: false,
                    opacityFrom: 1,
                    opacityTo: 1,
                    stops: [0, 50, 100],
                    colorStops: []
                },
            },
            yaxis: {
                title: {
                    text: 'Duración de Contrato',
                },
                labels: {
                    show: false
                }
            },
            xaxis: {
                type: 'datetime',
            },
            legend: {
                position: 'bottom',
            }
        };
        this.renderGraph(this.contractDurations.el, options);
    }

    renderInvoiceStatusGraph(div, vehicleRentalData) {
        const chartData = [];
        const root = am5.Root.new(div);
        root.setThemes([
            am5themes_Animated.new(root)
        ]);
        const chart = root.container.children.push(am5xy.XYChart.new(root, {
            panX: true,
            panY: true,
            wheelX: "panX",
            wheelY: "zoomX",
            pinchZoomX: true,
            paddingLeft: 0,
            paddingRight: 1
        }));
        const cursor = chart.set("cursor", am5xy.XYCursor.new(root, {}));
        cursor.lineY.set("visible", false);
        const xRenderer = am5xy.AxisRendererX.new(root, {
            minGridDistance: 30,
            minorGridEnabled: true,
        });
        xRenderer.labels.template.setAll({
            centerY: am5.p50,
            centerX: am5.p50,
            paddingRight: 15
        });
        xRenderer.grid.template.setAll({
            location: 1
        })
        const xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
            maxDeviation: 0.3,
            categoryField: "category",
            renderer: xRenderer,
            tooltip: am5.Tooltip.new(root, {})
        }));
        const yRenderer = am5xy.AxisRendererY.new(root, {
            strokeOpacity: 0.1
        })
        const yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            maxDeviation: 0.3,
            renderer: yRenderer
        }));
        const series = chart.series.push(am5xy.ColumnSeries.new(root, {
            name: "Series 1",
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: "value",
            sequencedInterpolation: true,
            categoryXField: "category",
            tooltip: am5.Tooltip.new(root, {
                labelText: "{valueY}"
            })
        }));
        series.columns.template.setAll({ cornerRadiusTL: 5, cornerRadiusTR: 5, strokeOpacity: 0 });
        series.columns.template.adapters.add("fill", function (fill, target) {
            return chart.get("colors").getIndex(series.columns.indexOf(target));
        });
        series.columns.template.adapters.add("stroke", function (stroke, target) {
            return chart.get("colors").getIndex(series.columns.indexOf(target));
        });
        for (var i = 0; i < vehicleRentalData['x-axis'].length; i++) {
            chartData.push({
                value: vehicleRentalData['y-axis'][i],
                category: vehicleRentalData['x-axis'][i],
            });
        }
        xAxis.data.setAll(chartData);
        series.data.setAll(chartData);
        series.appear(1000);
        chart.appear(1000, 100);
    }
}
VehicleRentalDashboard.template = "vehicle_rental.rental_dashboard";
registry.category("actions").add("vehicle_rental_dashboard", VehicleRentalDashboard);