/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component} from "@odoo/owl";
import {onMounted,} from "@odoo/owl";
import { user } from "@web/core/user";
import { _lt } from "@web/core/l10n/translation";
const { DateTime } = luxon

export class Timer_js extends Component {
    setup() {
        this.ormService = useService("orm");
        this.dialogService = useService("dialog");
        this.uid = user.userId;
        this.taskId = this.props.record.resId;
        this.duration = this._getStoredDuration() || 0;
        onMounted(async () => {
            let result = await this.ormService.searchRead(
                'project.task.user.time',
                [['task_id', '=', this.taskId], ['user_id', '=', this.uid]],
                ["start_time", "end_time"]
            );
            let currentDate = DateTime.now();

            if (result.length) {
                result.forEach(data => {
                    const startTime = DateTime.fromISO(data.start_time, { zone: "utc" });
                    const endTime = data.end_time 
                        ? DateTime.fromISO(data.end_time, { zone: "utc" }) 
                        : currentDate;

                    const durationInSeconds = endTime.diff(startTime, "seconds").seconds;

                    if (!isNaN(durationInSeconds)) {
                        this.duration += durationInSeconds;
                    }
                });

                this._startTimeCounter();
            } else {
                console.log("No data found...");
            }
        });
    }
    destroy() {
        super.destroy();
        clearInterval(this.timer);
        this._storeDuration();
    }

    _startTimeCounter() {
        if (this.props.record.data.task_Start) {
            this.timer = setInterval(() => {
                this.duration += 1;
                this._updateTimerDisplay();
                this._storeDuration();
            }, 1000);
        }
    }

    _updateTimerDisplay() {
        const hours = Math.floor(this.duration / 3600);
        const minutes = Math.floor((this.duration % 3600) / 60);
        const seconds = Math.floor(this.duration % 60);

        let timerField = this.__owl__.bdom.el.querySelector('span');
        if (timerField) {
            timerField.innerHTML = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    }

    _getStoredDuration() {
        return parseInt(localStorage.getItem(`timer_duration_${this.uid}_${this.taskId}`), 10);
    }

    _storeDuration() {
        localStorage.setItem(`timer_duration_${this.uid}_${this.taskId}`, this.duration);
    }
}

Timer_js.template = "bi_all_in_one_project_management_system.timer";

export const timer_js = {
    component: Timer_js,
};

registry.category("fields").add("timer_concept", timer_js);

