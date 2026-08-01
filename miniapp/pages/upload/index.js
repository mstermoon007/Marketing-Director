"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * 截图上传页
 */
const request_1 = require("../../api/request");
Page({
    data: {
        planId: '',
        files: [],
        submitting: false,
    },
    onLoad(options) {
        const planId = options.plan_id || getApp().globalData.planId;
        this.setData({ planId });
    },
    onChooseImage() {
        const count = 9 - this.data.files.length;
        if (count <= 0) {
            wx.showToast({ title: '最多上传9张', icon: 'none' });
            return;
        }
        wx.chooseMedia({
            count,
            mediaType: ['image'],
            sourceType: ['album', 'camera'],
            success: (res) => {
                const newPaths = res.tempFiles.map((f) => f.tempFilePath);
                this.setData({ files: [...this.data.files, ...newPaths] });
            },
        });
    },
    onChooseMessageFile() {
        wx.chooseMessageFile({
            count: 5,
            type: 'file',
            extension: ['csv'],
            success: (res) => {
                const newPaths = res.tempFiles.map((f) => f.path);
                this.setData({ files: [...this.data.files, ...newPaths] });
            },
        });
    },
    onPreviewImage(e) {
        const src = e.currentTarget.dataset.src;
        wx.previewImage({ urls: this.data.files, current: src });
    },
    onRemoveFile(e) {
        const idx = e.currentTarget.dataset.index;
        const files = [...this.data.files];
        files.splice(idx, 1);
        this.setData({ files });
    },
    async onSubmit() {
        if (this.data.files.length === 0) {
            wx.showToast({ title: '请上传截图或CSV文件', icon: 'none' });
            return;
        }
        if (!this.data.planId) {
            wx.showToast({ title: '缺少计划ID', icon: 'none' });
            return;
        }
        this.setData({ submitting: true });
        try {
            const result = await (0, request_1.upload)(`/review/${this.data.planId}`, this.data.files);
            const app = getApp();
            app.saveState('reviewId', result.id);
            wx.showToast({ title: '复盘完成', icon: 'success' });
            setTimeout(() => {
                wx.switchTab({ url: '/pages/review/index' });
            }, 800);
        }
        catch (err) {
            wx.showToast({ title: err.message || '上传失败', icon: 'none' });
        }
        finally {
            this.setData({ submitting: false });
        }
    },
});
