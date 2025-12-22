/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";
import { rpc } from "@web/core/network/rpc";
const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;


class VehicleAvailability extends Component {
  setup() {
    this.rpc = rpc;
    this.action = useService("action");
    this.orm = useService("orm");
    this.state = useState({})
    onWillStart(async () => {
      const data = await this.rpc('/get/contract/data')
      this.state.data = data.data
    })
    onMounted(() => {
      this.differentiateData(this.state.data)
    })
  }
  async differentiateData(data) {
    const result = [];
    const seen = new Set();
    for (const item of data) {
      const key = `${item.start_date}-${item.id}`;

      if (!seen.has(key)) {
        seen.add(key);
        result.push(item);
      }
    }

    await this.CreateChildParentRecords(result)
  }


  async CreateChildParentRecords(data) {
    let currentId = 1;
    const result = [];
    const seenTexts = new Map();
    for (const item of data) {

      // Check if the text has already been seen
      if (!seenTexts.has(item.text)) {
        // Create a parent record with a unique ID
        let parent = { ...item, open: true };
        parent.id = currentId++; // Assign the unique ID to the parent
        result.push(parent);

        seenTexts.set(item.text, parent.id);
      } else {
        // If the text has been seen, create a child record
        const parentId = seenTexts.get(item.text);
        let childRecord = { ...item, parent: parentId };
        childRecord.id = currentId++
        result.push(childRecord);
      }
    }
    result.forEach((task) => {
      task.start_date = task.start_date.toString();  // Convert back to string
      task.end_date = task.end_date.toString();      // Convert back to string
    });

    await this.renderGanttChart(result)
  }

  async renderGanttChart(contractdata) {
    let el = await document.getElementById('availibilityChart')
    if (el.innerHTML != '') {
      gantt.clearAll()
      el.innerHTML = ''
    }
    var tasks = {
      data: contractdata
    };

    const handleTaskClick = async (taskName) => {
        const domain = [
            ['reference_no','=',taskName],
        ];
        const records = await this.orm.searchRead('vehicle.contract',domain,['id']);
         let context = { 'create': false }
         return await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'contracts',
            res_model: 'vehicle.contract',
            res_id : records[0].id,
            view_mode: 'form',
            views: [[false,'form']],
            target: 'current',
            context: context,
        });
    };

     gantt.templates.task_text = function (start, end, task) {
        // Create a div with an onclick event
        return `<div class="task-text" data-task-name="${task.name}">${task.name}</div>`;
    };
    gantt.config.min_column_width = 50;
    gantt.config.readonly = true;
    gantt.config.columns = [
      { name: "text", label: "Vehículo", tree: true, width:250},
      { name: "start_date", label: "Fecha de inicio", align: "center",width:90},
      { name: "end_date", label: "Fecha de fin", align: "center", width:90},
      { name: "duration", label: "Duración", align: "center", width:90}
    ];

    gantt.templates.grid_folder = function (item) {
      return "<img class='gantt_tree_icon' src='/vehicle_rental/static/src/img/vehicle.png' alt='img' width='20px' height='20px'/>"
    };

    gantt.templates.grid_file = function (item) {
      return "<img class='gantt_tree_icon' src='/vehicle_rental/static/src/img/car-rental.png' alt='img' width='20px' height='20px'/>";
    };

    gantt.init(el);
    gantt.parse(tasks);

    el.addEventListener('click', function(event) {
        if (event.target.classList.contains('task-text')) {
            const taskId = event.target.getAttribute('data-task-name');
            handleTaskClick(taskId);
        }
    });


  }


}
VehicleAvailability.template = "vehicle_rental.availability_vehicle";
registry.category("actions").add("vehicle_availability", VehicleAvailability);