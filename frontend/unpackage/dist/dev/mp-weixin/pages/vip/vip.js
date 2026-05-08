"use strict";
const common_vendor = require("../../common/vendor.js");
const _sfc_main = {
  __name: "vip",
  setup(__props) {
    const currentDays = common_vendor.ref(0);
    const openPayMenu = (days) => {
      currentDays.value = days;
      common_vendor.index.showActionSheet({
        itemList: ["微信支付", "支付宝支付"],
        success: function(res) {
          if (res.tapIndex === 0) {
            startPay("wxpay");
          } else {
            startPay("alipay");
          }
        },
        fail: function(res) {
          common_vendor.index.__f__("log", "at pages/vip/vip.vue:72", res.errMsg);
        }
      });
    };
    const startPay = (provider) => {
      common_vendor.index.showLoading({ title: "创建订单..." });
      common_vendor.index.request({
        url: "http://127.0.0.1:8000/api/pay/create_order",
        // 记得改IP
        method: "POST",
        data: {
          days: currentDays.value,
          provider
        },
        success: (res) => {
          common_vendor.index.hideLoading();
          if (res.data.code === 200) {
            const orderInfo = res.data.orderInfo;
            if (typeof orderInfo === "string" && orderInfo.includes("simulation")) {
              common_vendor.index.showModal({
                title: "模拟支付",
                content: "检测到未配置真实支付Key，是否模拟支付成功？",
                success: (mockRes) => {
                  if (mockRes.confirm)
                    mockSuccess();
                }
              });
              return;
            }
            common_vendor.index.requestPayment({
              provider,
              orderInfo,
              success: function(res2) {
                mockSuccess();
              },
              fail: function(err) {
                common_vendor.index.showToast({ title: "支付取消或失败", icon: "none" });
              }
            });
          } else {
            common_vendor.index.showToast({ title: "订单创建失败", icon: "none" });
          }
        }
      });
    };
    const mockSuccess = () => {
      common_vendor.index.request({
        url: `http://127.0.0.1:8000/api/pay/mock_success?days=${currentDays.value}`,
        method: "POST",
        success: () => {
          common_vendor.index.showToast({ title: "开通成功！", icon: "success" });
          setTimeout(() => {
            common_vendor.index.reLaunch({ url: "/pages/mine/mine" });
          }, 1500);
        }
      });
    };
    const navTo = (page) => {
      const routes = {
        "index": "/pages/index/index",
        "prepare": "/pages/prepare/prepare",
        "mine": "/pages/mine/mine"
      };
      common_vendor.index.reLaunch({ url: routes[page] });
    };
    return (_ctx, _cache) => {
      return {
        a: common_vendor.o(($event) => openPayMenu(7)),
        b: common_vendor.o(($event) => openPayMenu(30)),
        c: common_vendor.o(($event) => openPayMenu(365)),
        d: common_vendor.o(($event) => navTo("index")),
        e: common_vendor.o(($event) => navTo("prepare")),
        f: common_vendor.o(($event) => navTo("mine"))
      };
    };
  }
};
const MiniProgramPage = /* @__PURE__ */ common_vendor._export_sfc(_sfc_main, [["__scopeId", "data-v-61fb1047"]]);
wx.createPage(MiniProgramPage);
//# sourceMappingURL=../../../.sourcemap/mp-weixin/pages/vip/vip.js.map
