"use strict";
/**
 * 统一API请求封装
 *
 * 所有后端返回格式：{ code: 0, data: {...}, message: "ok" }
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.get = get;
exports.post = post;
exports.upload = upload;
const getBase = () => {
    const app = getApp();
    return app.globalData.apiBase;
};
/** 通用 GET */
function get(path) {
    return new Promise((resolve, reject) => {
        wx.request({
            url: getBase() + path,
            method: 'GET',
            success(res) {
                const r = res.data;
                if (r.code === 0) {
                    resolve(r.data);
                }
                else {
                    reject(new Error(r.message || '请求失败'));
                }
            },
            fail(err) {
                reject(new Error(err.errMsg || '网络错误'));
            },
        });
    });
}
/** 通用 POST（JSON body） */
function post(path, body = {}) {
    return new Promise((resolve, reject) => {
        wx.request({
            url: getBase() + path,
            method: 'POST',
            header: { 'Content-Type': 'application/json' },
            data: body,
            success(res) {
                const r = res.data;
                if (r.code === 0) {
                    resolve(r.data);
                }
                else {
                    reject(new Error(r.message || '请求失败'));
                }
            },
            fail(err) {
                reject(new Error(err.errMsg || '网络错误'));
            },
        });
    });
}
/** 上传文件（multipart） */
function upload(path, files) {
    return new Promise((resolve, reject) => {
        // upload 支持多文件，逐个上传
        const results = [];
        let completed = 0;
        if (files.length === 0) {
            reject(new Error('请选择文件'));
            return;
        }
        files.forEach((filePath) => {
            wx.uploadFile({
                url: getBase() + path,
                filePath,
                name: 'files',
                success(res) {
                    try {
                        const r = JSON.parse(res.data);
                        results.push(r);
                        completed++;
                        if (completed === files.length) {
                            // 返回最后一个结果（后端合并处理）
                            resolve(results[results.length - 1].data);
                        }
                    }
                    catch (_a) {
                        completed++;
                        reject(new Error('解析响应失败'));
                    }
                },
                fail(err) {
                    reject(new Error(err.errMsg || '上传失败'));
                },
            });
        });
    });
}
