import { markdownToHtml } from '../../utils/markdown'

Component({
  properties: {
    /** Markdown 源文本 */
    content: { type: String, value: '' },
  },
  data: {
    html: '',
  },
  observers: {
    content(val: string): void {
      this.setData({ html: markdownToHtml(val || '') })
    },
  },
  lifetimes: {
    attached(): void {
      this.setData({ html: markdownToHtml(this.data.content || '') })
    },
  },
})
