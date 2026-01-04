// ==UserScript==
// @name         多账号自动登录脚本
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  自动登录多个账户并登出
// @author       Linux.do
// @match        https://linux.do/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=linux.do
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// ==/UserScript==

(function () {
    'use strict';

    const styles = `
        .tm-toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .tm-toast {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: #333;
            padding: 12px 24px;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            font-size: 14px;
            font-weight: 500;
            animation: tm-slide-in 0.3s ease-out forwards;
            min-width: 200px;
            text-align: center;
        }
        @keyframes tm-slide-in {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .tm-toast.fade-out {
            animation: tm-slide-out 0.3s ease-in forwards;
        }
        @keyframes tm-slide-out {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }

        #tm-config-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(4px);
            z-index: 9998;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: tm-fade-in 0.2s ease-out;
        }
        #tm-config {
            background: rgba(255, 255, 255, 0.95);
            padding: 24px;
            border-radius: 20px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
            width: 450px;
            max-width: 90vw;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        @keyframes tm-fade-in {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        #tm-config h2 {
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 20px;
            color: #1d1d1f;
            text-align: center;
        }
        #tm-accounts-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        #tm-accounts-table th {
            text-align: left;
            font-size: 13px;
            color: #86868b;
            padding: 8px;
            border-bottom: 1.5px solid #ebebeb;
            font-weight: 600;
        }
        #tm-accounts-table td {
            padding: 12px 8px;
            vertical-align: middle;
            border-bottom: 1px solid #f2f2f2;
        }
        .tm-config-input {
            width: 100%;
            box-sizing: border-box;
            padding: 10px 12px;
            border: 1.5px solid #d2d2d7;
            border-radius: 10px;
            font-size: 14px;
            outline: none;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            background: #ffffff;
            color: #1d1d1f;
        }
        .tm-config-input:focus {
            border-color: #0071e3;
            box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.1);
        }
        .tm-btn-container {
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }
        .tm-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tm-btn-primary {
            background: #0071e3;
            color: white;
        }
        .tm-btn-primary:hover {
            background: #0077ed;
        }
        .tm-btn-secondary {
            background: #e8e8ed;
            color: #1d1d1f;
        }
        .tm-btn-secondary:hover {
            background: #d2d2d7;
        }
        .tm-btn-danger {
            background: #ff3b30;
            color: white;
            width: 24px;
            height: 24px;
            padding: 0;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.2s;
            margin: 0 auto;
            line-height: normal;
        }
        .tm-btn-danger:hover {
            background: #ff453a;
            transform: scale(1.1);
        }

        #tm-status-indicator {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            pointer-events: none;
            animation: tm-pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes tm-pop-in {
            from { transform: translateX(-50%) translateY(-50px); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
        .tm-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: tm-spin 0.8s linear infinite;
        }
        @keyframes tm-spin {
            to { transform: rotate(360deg); }
        }
    `;

    const styleElement = document.createElement('style');
    styleElement.textContent = styles;
    document.head.appendChild(styleElement);

    const toastContainer = document.createElement('div');
    toastContainer.className = 'tm-toast-container';
    document.body.appendChild(toastContainer);

    let accounts = GM_getValue('accounts', []);
    let scriptEnabled = GM_getValue('scriptEnabled', false);

    GM_registerMenuCommand('配置账号', openConfig);
    GM_registerMenuCommand('启动/停止脚本', toggleScript);

    function showMessage(message, timeout = 3000) {
        const toast = document.createElement('div');
        toast.className = 'tm-toast';
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('fade-out');
            toast.addEventListener('animationend', () => {
                toast.remove();
            });
        }, timeout);
    }

    function updateRunningStatus(text) {
        let indicator = document.getElementById('tm-status-indicator');
        if (!text) {
            if (indicator) indicator.remove();
            return;
        }
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'tm-status-indicator';
            indicator.innerHTML = '<div class="tm-spinner"></div><span id="tm-status-text"></span>';
            document.body.appendChild(indicator);
        }
        document.getElementById('tm-status-text').textContent = text;
    }

    function toggleScript() {
        scriptEnabled = !scriptEnabled;
        GM_setValue('scriptEnabled', scriptEnabled);
        showMessage('脚本现在' + (scriptEnabled ? '启动' : '停止') + '。');
        if (scriptEnabled) {
            GM_setValue('shouldRunMain', true);
            main();
        } else {
            GM_setValue('shouldRunMain', false);
        }
    }

    function openConfig() {
        if (document.getElementById('tm-config-overlay')) return;

        let configHtml = `
            <div id="tm-config-overlay">
                <div id="tm-config">
                    <h2>账号配置</h2>
                    <table id="tm-accounts-table">
                        <thead>
                            <tr>
                                <th style="width: 45%;">用户名</th>
                                <th style="width: 45%;">密码</th>
                                <th style="width: 50px; text-align: center;">操作</th>
                            </tr>
                        </thead>
                        <tbody id="tm-accounts-list"></tbody>
                    </table>
                    <div class="tm-btn-container">
                        <button id="tm-add-account" class="tm-btn tm-btn-secondary">添加账号</button>
                        <button id="tm-save-config" class="tm-btn tm-btn-primary">保存配置</button>
                        <button id="tm-close-config" class="tm-btn tm-btn-secondary">取消</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', configHtml);

        accounts.forEach((account, index) => {
            addAccountFields(index, account.username, account.password);
        });

        document.getElementById('tm-add-account').addEventListener('click', () => {
            addAccountFields(document.querySelectorAll('.tm-account-tr').length);
        });

        document.getElementById('tm-save-config').addEventListener('click', saveConfig);
        document.getElementById('tm-close-config').addEventListener('click', () => {
            document.getElementById('tm-config-overlay').remove();
        });
        document.getElementById('tm-config-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'tm-config-overlay') e.target.remove();
        });
    }

    function addAccountFields(index, username = '', password = '') {
        let accountHtml = `
            <tr class="tm-account-tr" data-index="${index}">
                <td>
                    <input type="text" class="tm-config-input tm-username" value="${username}" placeholder="用户名">
                </td>
                <td>
                    <input type="password" class="tm-config-input tm-password" value="${password}" placeholder="密码">
                </td>
                <td>
                    <button class="tm-btn tm-btn-danger tm-remove-account" title="移除账号">×</button>
                </td>
            </tr>
        `;
        document.getElementById('tm-accounts-list').insertAdjacentHTML('beforeend', accountHtml);

        let removeButtons = document.getElementsByClassName('tm-remove-account');
        let lastButton = removeButtons[removeButtons.length - 1];
        lastButton.addEventListener('click', function () {
            this.closest('tr').remove();
        });
    }

    function saveConfig() {
        let accountRows = document.getElementsByClassName('tm-account-tr');
        accounts = Array.from(accountRows).map(tr => {
            return {
                username: tr.querySelector('.tm-username').value,
                password: tr.querySelector('.tm-password').value
            };
        }).filter(acc => acc.username && acc.password);

        GM_setValue('accounts', accounts);
        showMessage('配置已保存！');
        document.getElementById('tm-config-overlay').remove();
    }

    function isLoggedIn() {
        return document.querySelector('#toggle-current-user') !== null;
    }

    function waitForElement(selector, callback, checkVisibility = false, timeout = 5000) {
        let start = Date.now();
        let interval = setInterval(() => {
            let element = document.querySelector(selector);
            let isVisible = element && (element.offsetParent !== null);
            if (element && (!checkVisibility || isVisible)) {
                clearInterval(interval);
                callback(element);
            } else if (Date.now() - start >= timeout) {
                clearInterval(interval);
                console.error('等待元素超时: ', selector);
                showMessage('操作超时，脚本停止。');
                GM_setValue('scriptEnabled', false);
            }
        }, 100);
    }

    function login(account, callback) {
        if (!isLoggedIn()) {
            let loginButton = document.querySelector('.login-button');
            if (loginButton) {
                loginButton.click();
                waitForElement('#login-account-name', () => {
                    let usernameField = document.getElementById('login-account-name');
                    let passwordField = document.getElementById('login-account-password');

                    usernameField.value = '';
                    passwordField.value = '';

                    setTimeout(() => {
                        usernameField.value = account.username;
                        passwordField.value = account.password;

                        usernameField.dispatchEvent(new Event('input', { bubbles: true }));
                        passwordField.dispatchEvent(new Event('input', { bubbles: true }));

                        setTimeout(() => {
                            document.getElementById('login-button').click();

                            setTimeout(() => {
                                let alertElement = document.querySelector('#modal-alert.alert.alert-error');
                                if (alertElement && alertElement.textContent.includes('请稍后再尝试登录。')) {
                                    console.log('出现错误提示，正在重试登录...');
                                    setTimeout(() => {
                                        document.getElementById('login-button').click();
                                    }, 500);
                                } else if (typeof callback === "function") {
                                    callback();
                                }
                            }, 100);
                        }, 800);
                    }, 200);
                });
            }
        }
    }

    function logout(callback) {
        waitForElement('#toggle-current-user', (profileButton) => {
            profileButton.click();
            waitForElement('.bottom-tabs .user-menu-tab', (profileTab) => {
                profileTab.click();
                waitForElement('.logout .profile-tab-btn', (logoutButton) => {
                    logoutButton.click();
                    if (typeof callback === "function") {
                        callback();
                    }
                });
            });
        });
    }

    function main() {
        if (!GM_getValue('shouldRunMain', false)) {
            return;
        }
        console.log('开始处理账号');

        setTimeout(() => {
            console.log('开始处理账号');

            let accountIndex = GM_getValue('accountIndex', 0);

            if (scriptEnabled && accountIndex < accounts.length) {
                if (isLoggedIn()) {
                    console.log('已登录，准备登出');
                    updateRunningStatus(`账号 ${accountIndex + 1}/${accounts.length} 处理中... 准备登出`);
                    logout(() => {
                        // 登出后不立即增加索引，等跳转到未登录状态后再处理下一个
                        document.addEventListener('DOMContentLoaded', main);
                    });
                } else {
                    let account = accounts[accountIndex];
                    console.log('准备登录账号：', account.username);
                    updateRunningStatus(`正在登录：${account.username} (${accountIndex + 1}/${accounts.length})`);
                    GM_setValue('currentAccount', account.username);
                    login(account, () => {
                        // 登录成功，增加索引，准备处理下一个（或者刷新页面）
                        GM_setValue('accountIndex', accountIndex + 1);
                        document.addEventListener('DOMContentLoaded', main);
                    });
                }
            } else {
                console.log('所有账号处理完毕');
                updateRunningStatus(null);
                GM_setValue('accountIndex', 0);
                GM_setValue('shouldRunMain', false);
                GM_setValue('scriptEnabled', false);
                showMessage('操作完成');
            }
        }, 2000);
    }

    window.addEventListener('load', function () {
        if (GM_getValue('shouldRunMain', false) && GM_getValue('scriptEnabled', false)) {
            let accountIndex = GM_getValue('accountIndex', 0);
            if (accountIndex < accounts.length) {
                updateRunningStatus(`准备处理第 ${accountIndex + 1}/${accounts.length} 个账号...`);
            }
            main();
        }
    });
})();
