"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const markdown_1 = require("../../utils/markdown");
Component({
    properties: {
        /** Markdown 源文本 */
        content: { type: String, value: '' },
    },
    data: {
        html: '',
    },
    observers: {
        content(val) {
            this.setData({ html: (0, markdown_1.markdownToHtml)(val || '') });
        },
    },
    lifetimes: {
        attached() {
            this.setData({ html: (0, markdown_1.markdownToHtml)(this.data.content || '') });
        },
    },
});
