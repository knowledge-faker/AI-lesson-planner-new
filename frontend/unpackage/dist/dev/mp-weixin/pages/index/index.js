"use strict";
const common_vendor = require("../../common/vendor.js");
const _sfc_main = {
  __name: "index",
  setup(__props) {
    const historyList = common_vendor.ref([]);
    common_vendor.onShow(() => {
      common_vendor.index.request({
        url: "http://127.0.0.1:8000/api/history",
        method: "GET",
        success: (res) => {
          if (res.data.code === 200) {
            const baseUrl = "http://127.0.0.1:8000/static/";
            historyList.value = res.data.data.map((item) => {
              const files = item.files_json;
              return {
                topic: item.topic,
                subject: item.subject,
                time: item.created_at.replace("T", " "),
                planUrl: baseUrl + files.plan,
                quizUrl: baseUrl + files.quiz,
                htmlUrl: baseUrl + files.html
              };
            });
          }
        }
      });
    });
    common_vendor.index.setNavigationBarTitle({ title: "AI 备课" });
    const openH5 = (url) => {
      if (!url)
        return common_vendor.index.showToast({ title: "链接不存在", icon: "none" });
      window.open(url);
    };
    const downloadFile = (url) => {
      if (!url)
        return common_vendor.index.showToast({ title: "链接不存在", icon: "none" });
      window.open(url);
    };
    const handleAction = (type) => {
      common_vendor.index.setStorageSync("genType", type);
      common_vendor.index.reLaunch({ url: "/pages/prepare/prepare" });
    };
    const navTo = (name) => {
      common_vendor.index.reLaunch({ url: `/pages/${name}/${name}` });
    };
    const goVip = () => {
      common_vendor.index.reLaunch({ url: "/pages/vip/vip" });
    };
    return (_ctx, _cache) => {
      return common_vendor.e({
        a: common_vendor.o(($event) => handleAction("plan")),
        b: common_vendor.o(($event) => handleAction("quiz")),
        c: common_vendor.o(($event) => handleAction("html")),
        d: common_vendor.o(goVip),
        e: common_vendor.f(historyList.value, (item, index, i0) => {
          return {
            a: common_vendor.t(item.subject),
            b: common_vendor.t(item.topic),
            c: common_vendor.t(item.time),
            d: common_vendor.o(($event) => downloadFile(item.planUrl), index),
            e: common_vendor.o(($event) => downloadFile(item.quizUrl), index),
            f: common_vendor.o(($event) => openH5(item.htmlUrl), index),
            g: index
          };
        }),
        f: historyList.value.length === 0
      }, historyList.value.length === 0 ? {} : {}, {
        g: common_vendor.o(($event) => navTo("prepare")),
        h: common_vendor.o(($event) => navTo("vip")),
        i: common_vendor.o(($event) => navTo("mine"))
      });
    };
  }
};
const MiniProgramPage = /* @__PURE__ */ common_vendor._export_sfc(_sfc_main, [["__scopeId", "data-v-1cf27b2a"]]);
wx.createPage(MiniProgramPage);
//# sourceMappingURL=../../../.sourcemap/mp-weixin/pages/index/index.js.map
