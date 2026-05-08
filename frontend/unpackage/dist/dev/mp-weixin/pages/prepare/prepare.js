"use strict";
const common_vendor = require("../../common/vendor.js");
const _sfc_main = {
  __name: "prepare",
  setup(__props) {
    const topic = common_vendor.ref("");
    const grade = common_vendor.ref("");
    const subject = common_vendor.ref("");
    const grades = ["小学", "初中", "高中"];
    const subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"];
    const onGradeChange = (e) => {
      grade.value = grades[e.detail.value];
    };
    const onSubjectChange = (e) => {
      subject.value = subjects[e.detail.value];
    };
    const navTo = (name) => {
      common_vendor.index.reLaunch({ url: `/pages/${name}/${name}` });
    };
    const doGenerate = () => {
      if (!topic.value || !grade.value || !subject.value) {
        return common_vendor.index.showToast({ title: "请填写完整信息", icon: "none" });
      }
      common_vendor.index.showLoading({ title: "AI 正在编写中..." });
      common_vendor.index.request({
        url: "http://localhost:8000/api/generate",
        method: "POST",
        timeout: 12e4,
        // 设置 100 秒超时，因为 AI 生成很慢
        data: {
          topic: topic.value,
          grade: grade.value,
          subject: subject.value
        },
        success: (res) => {
          common_vendor.index.hideLoading();
          if (res.data.code === 200) {
            const baseUrl = "http://127.0.0.1:8000/static/";
            const planUrl = baseUrl + res.data.data.plan;
            const quizUrl = baseUrl + res.data.data.quiz;
            const htmlUrl = baseUrl + res.data.data.html;
            common_vendor.index.showModal({
              title: "生成成功",
              content: "全套资源已准备就绪，是否立即查看下载链接？",
              confirmText: "去查看",
              success: (res2) => {
                if (res2.confirm) {
                  if (res2.confirm) {
                    let history = common_vendor.index.getStorageSync("history") || [];
                    history.unshift({
                      topic: topic.value,
                      subject: subject.value,
                      time: (/* @__PURE__ */ new Date()).toLocaleString(),
                      planUrl,
                      quizUrl,
                      htmlUrl
                    });
                    common_vendor.index.setStorageSync("history", history);
                    common_vendor.index.reLaunch({ url: "/pages/index/index" });
                  }
                }
              }
            });
          }
        },
        fail: (err) => {
          common_vendor.index.hideLoading();
          if (err.errMsg.indexOf("timeout") !== -1) {
            common_vendor.index.showToast({ title: "AI思考时间较长，请稍后在记录中查看", icon: "none" });
          } else {
            common_vendor.index.showToast({ title: "请求失败", icon: "none" });
          }
        }
      });
    };
    return (_ctx, _cache) => {
      return {
        a: common_vendor.t(grade.value || "点击选择（小学/初中/高中）"),
        b: common_vendor.n(grade.value ? "value" : "placeholder"),
        c: grades,
        d: common_vendor.o(onGradeChange),
        e: common_vendor.t(subject.value || "点击选择学科（语数外等）"),
        f: common_vendor.n(subject.value ? "value" : "placeholder"),
        g: subjects,
        h: common_vendor.o(onSubjectChange),
        i: topic.value,
        j: common_vendor.o(($event) => topic.value = $event.detail.value),
        k: common_vendor.o(doGenerate),
        l: common_vendor.o(($event) => navTo("index")),
        m: common_vendor.o(($event) => navTo("vip")),
        n: common_vendor.o(($event) => navTo("mine"))
      };
    };
  }
};
const MiniProgramPage = /* @__PURE__ */ common_vendor._export_sfc(_sfc_main, [["__scopeId", "data-v-d7449692"]]);
wx.createPage(MiniProgramPage);
//# sourceMappingURL=../../../.sourcemap/mp-weixin/pages/prepare/prepare.js.map
