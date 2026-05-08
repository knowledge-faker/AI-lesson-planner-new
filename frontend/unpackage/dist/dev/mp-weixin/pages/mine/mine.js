"use strict";
const common_vendor = require("../../common/vendor.js");
const _sfc_main = {
  __name: "mine",
  setup(__props) {
    const userInfo = common_vendor.ref({
      nickname: "加载中...",
      is_vip: false,
      vip_expiry_str: "",
      stats: { total: 0, lesson: 0, quiz: 0, html: 0 }
    });
    common_vendor.onShow(() => {
      common_vendor.index.request({
        url: "http://127.0.0.1:8000/api/user/info",
        method: "GET",
        success: (res) => {
          if (res.data.code === 200) {
            const data = res.data.data;
            userInfo.value = data;
            if (data.vip_expiry) {
              userInfo.value.vip_expiry_str = data.vip_expiry.split("T")[0];
            }
          }
        },
        fail: () => {
          common_vendor.index.showToast({ title: "无法连接到服务器", icon: "none" });
        }
      });
    });
    const navTo = (name) => {
      common_vendor.index.reLaunch({ url: `/pages/${name}/${name}` });
    };
    const logout = () => {
      common_vendor.index.showToast({ title: "功能开发中", icon: "none" });
    };
    return (_ctx, _cache) => {
      return common_vendor.e({
        a: common_vendor.t(userInfo.value.nickname),
        b: common_vendor.t(userInfo.value.is_vip ? "VIP会员" : "普通用户"),
        c: common_vendor.n(userInfo.value.is_vip ? "tag-vip active" : "tag-vip"),
        d: userInfo.value.is_vip
      }, userInfo.value.is_vip ? {
        e: common_vendor.t(userInfo.value.vip_expiry_str)
      } : {}, {
        f: common_vendor.o(($event) => navTo("vip")),
        g: common_vendor.o(logout),
        h: common_vendor.t(userInfo.value.stats.total),
        i: common_vendor.t(userInfo.value.stats.lesson),
        j: common_vendor.t(userInfo.value.stats.quiz),
        k: common_vendor.t(userInfo.value.stats.html),
        l: common_vendor.o(($event) => navTo("index")),
        m: common_vendor.o(($event) => navTo("index")),
        n: common_vendor.o(($event) => navTo("prepare")),
        o: common_vendor.o(($event) => navTo("vip"))
      });
    };
  }
};
const MiniProgramPage = /* @__PURE__ */ common_vendor._export_sfc(_sfc_main, [["__scopeId", "data-v-7c2ebfa5"]]);
wx.createPage(MiniProgramPage);
//# sourceMappingURL=../../../.sourcemap/mp-weixin/pages/mine/mine.js.map
