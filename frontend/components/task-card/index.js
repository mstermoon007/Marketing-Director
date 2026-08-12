"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const constants_1 = require("../../utils/constants");
Component({
    properties: {
        task: { type: Object, value: {} },
        /** 所属日名称（日程页展示用） */
        dayName: { type: String, value: '' },
    },
    data: {
        statusLabel: '',
        checked: false,
    },
    observers: {
        task(val) {
            const status = (val && val.status) || constants_1.TASK_STATUS.PENDING;
            this.setData({
                statusLabel: constants_1.TASK_STATUS_LABEL[status] || '未开始',
                checked: status === constants_1.TASK_STATUS.DONE,
            });
        },
    },
    methods: {
        onToggle() {
            const t = this.data.task;
            this.triggerEvent('toggle', { id: t.id });
        },
    },
});
