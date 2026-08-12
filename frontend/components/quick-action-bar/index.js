"use strict";
Component({
    properties: {
        /** 快捷操作：{label, prompt} */
        actions: {
            type: Array,
            value: [],
        },
    },
    methods: {
        onTap(e) {
            const idx = e.currentTarget.dataset.index;
            const item = this.data.actions[idx];
            if (item) {
                this.triggerEvent('select', { prompt: item.prompt, label: item.label });
            }
        },
    },
});
