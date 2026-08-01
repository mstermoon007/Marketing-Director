"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * 企业信息填写页
 */
const request_1 = require("../../api/request");
Page({
    data: {
        form: {
            business_name: '',
            industry: '',
            city: '',
            product_desc: '',
            price_range: '',
            target_customers: '',
            competitors: '',
            current_channels: '',
            monthly_revenue: '',
            team_size: '',
            biggest_pain: '',
        },
        submitting: false,
        canSubmit: false,
    },
    onInput(e) {
        const field = e.currentTarget.dataset.field;
        const val = e.detail.value;
        const form = Object.assign(Object.assign({}, this.data.form), { [field]: val });
        const required = ['business_name', 'industry', 'city', 'product_desc', 'target_customers'];
        const canSubmit = required.every((k) => form[k].trim() !== '');
        this.setData({ form, canSubmit });
    },
    async onSubmit() {
        if (!this.data.canSubmit)
            return;
        this.setData({ submitting: true });
        try {
            const result = await (0, request_1.post)('/business', this.data.form);
            const app = getApp();
            app.saveState('businessId', result.id);
            wx.showToast({ title: '创建成功', icon: 'success' });
            setTimeout(() => {
                wx.navigateTo({ url: `/pages/diagnosis/index?business_id=${result.id}` });
            }, 800);
        }
        catch (err) {
            wx.showToast({
                title: err.message || '创建失败',
                icon: 'none',
            });
        }
        finally {
            this.setData({ submitting: false });
        }
    },
});
