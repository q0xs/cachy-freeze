"use strict";

const fs = require("fs");

if (process.argv.length !== 3) {
  throw new Error("usage: node polkit-rules.js PATH-TO-RULES");
}

let employeeRule;
global.polkit = {
  Result: { YES: "yes", AUTH_ADMIN_KEEP: "auth-admin-keep" },
  addRule(callback) {
    employeeRule = callback;
  },
};

const rulesSource = fs.readFileSync(process.argv[2], "utf8");
// The production file is a PolicyKit JavaScript rule. This controlled test
// supplies only the PolicyKit symbols that file is allowed to register.
eval(rulesSource);

if (typeof employeeRule !== "function") {
  throw new Error("employee PolicyKit rule was not registered");
}

const allowedLoginActions = [
  "org.kde.kameleon.qmk.helper.HasDevices",
  "org.kde.kameleon.qmk.helper.ApplyColor",
  "org.kde.powerdevil.discretegpuhelper.hasdualgpu",
  "org.freedesktop.NetworkManager.network-control",
  "org.kde.powerdevil.chargethresholdhelper.getconservationmode",
  "org.kde.powerdevil.chargethresholdhelper.getthreshold",
];
const activeEmployee = {
  user: "__EMPLOYEE_USER__",
  local: true,
  active: true,
};

for (const actionId of allowedLoginActions) {
  if (employeeRule({ id: actionId }, activeEmployee) !== polkit.Result.YES) {
    throw new Error(`login action was not allowed: ${actionId}`);
  }
}

if (
  employeeRule({ id: "org.example.privileged" }, activeEmployee) !==
  polkit.Result.AUTH_ADMIN_KEEP
) {
  throw new Error("an unlisted action did not require administrator authentication");
}

if (
  employeeRule(
    { id: allowedLoginActions[0] },
    { user: "another-user", local: true, active: true },
  ) !== undefined
) {
  throw new Error("the employee rule affected another user");
}

if (
  employeeRule(
    { id: allowedLoginActions[0] },
    { user: "__EMPLOYEE_USER__", local: true, active: false },
  ) !== undefined
) {
  throw new Error("the employee rule affected an inactive session");
}

console.log("PolicyKit employee rule behavior passed.");
