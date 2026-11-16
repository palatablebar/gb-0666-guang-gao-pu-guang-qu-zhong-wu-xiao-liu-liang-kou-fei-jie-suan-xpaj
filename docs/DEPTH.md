# 深度登记 广告曝光有效性与费用结算

- 规模：中型
- 核心规则：按曝光ID裁决重复与冲突，按时间及ID确定日频次，再聚合有效CPM。冲销引用采信的原曝光，同一曝光最多冲销一次，费用回到原曝光账日。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 日志采信 | 读取曝光和冲销台账 | `GET /api/intake` | `app/modules/m1_intake/service.py` `app/modules/m1_intake/rules.py` | `tests/test_intake.py` |
| M2 计费契约 | 核查曝光ID、时区和渠道资费 | `GET /api/contract` | `app/modules/m2_contract/service.py` `app/modules/m2_contract/rules.py` | `tests/test_contract.py` |
| M3 有效性判定 | 排除机器曝光与超过频次事件 | `GET /api/model` | `app/modules/m3_model/service.py` `app/modules/m3_model/rules.py` | `tests/test_model.py` |
| M4 费用聚合 | 按渠道账日结算并核查冲销限额 | `GET /api/calculate` | `app/modules/m4_calculate/service.py` `app/modules/m4_calculate/rules.py` | `tests/test_calculate.py` |
| M5 争议隔离 | 定位冲突和无法合法冲销事件 | `GET /api/quarantine` | `app/modules/m5_quarantine/service.py` `app/modules/m5_quarantine/rules.py` | `tests/test_quarantine.py` |
| M6 渠道对账 | 逐渠道复算账单差额 | `GET /api/reconcile` | `app/modules/m6_reconcile/service.py` `app/modules/m6_reconcile/rules.py` | `tests/test_reconcile.py` |
| M8 跨渠道账单 | 30分钟窗口重叠裁决、正式账单与补数版本链 | `GET /api/overlap` | `app/modules/m8_overlap/service.py` `app/modules/m8_overlap/rules.py` | `tests/test_overlap.py` |
| M7 批次复核 | 幂等重算与版本归档 | `GET /api/batches` | `app/modules/m7_batches/service.py` `app/modules/m7_batches/rules.py` | `tests/test_batches.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | 历史编码日志 | 静默误算或覆盖证据 | UTF8失败后GB18030 | `app/modules/m1_intake/rules.py` | `tests/test_intake.py::test_gb18030` |
| TRAP-02 | 首列BOM | 静默误算或覆盖证据 | utf-8-sig解码 | `app/modules/m1_intake/rules.py` | `tests/test_intake.py::test_bom` |
| TRAP-06 | 全角CPM | 静默误算或覆盖证据 | NFKC后Decimal | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_fullwidth` |
| TRAP-07 | 用户ID缺失 | 静默误算或覆盖证据 | 哨兵隔离 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_missing` |
| TRAP-09 | 超大曝光ID | 静默误算或覆盖证据 | 全程字符串不转数值 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_big_id` |
| TRAP-10 | 单曝光舍入导致总额错误 | 静默误算或覆盖证据 | 渠道日聚合后舍入 | `app/modules/m4_calculate/rules.py` | `tests/test_calculate.py::test_aggregate_before_round` |
| TRAP-11 | 时区混用 | 静默误算或覆盖证据 | UTC存储北京时间账日 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_utc` |
| TRAP-14 | 重复回调和键冲突 | 静默误算或覆盖证据 | 全字段比较，相同去重冲突隔离 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_duplicate` |
| TRAP-19 | 机器人和频次规则同时命中 | 静默误算或覆盖证据 | 机器人优先且不消耗频次 | `app/modules/m3_model/rules.py` | `tests/test_model.py::test_priority` |
| TRAP-26 | 陈旧复核覆盖新版本 | 静默误算或覆盖证据 | revision条件更新 | `app/modules/m7_batches/rules.py` | `tests/test_batches.py::test_stale` |
| TRAP-31 | 跨渠道重复触达被重复计费 | 各渠道各自结账，广告主为同一次触达多次付费 | 30分钟窗口先到先得，输家渠道按自有CPM形成重叠抵扣 | `app/modules/m8_overlap/rules.py` | `tests/test_overlap.py::test_winner_keeps_revenue_losers_get_credit` |
| TRAP-32 | 窗口边界与锚点漂移 | 滑动窗口导致一条曝光被反复抵扣 | 固定锚点+闭区间30分钟，事件只落一个窗口 | `app/modules/m8_overlap/rules.py` | `tests/test_overlap.py::test_window_boundary_inclusive_and_fixed_anchor` |
| TRAP-33 | 补数失败覆盖旧账单 | 坏补数写入后无法回滚 | 全部校验通过才写新版本，失败保留旧版 | `app/modules/m8_overlap/service.py` `app/store.py` | `tests/test_overlap.py::test_backfill_failure_preserves_old_bill` |
| TRAP-34 | 同批重试新增曝光或重复抵扣 | 重试被当成新批次二次入账 | 输入摘要幂等+事件ID语义去重，命中既有版本 | `app/modules/m8_overlap/service.py` | `tests/test_overlap.py::test_identical_retry_is_idempotent_no_new_version` |
| TRAP-35 | 冲销与重叠双重扣减 | 同一曝光先被冲销又被重叠抵扣 | 已冲销曝光不参与重叠裁决 | `app/modules/m8_overlap/rules.py` | `tests/test_overlap.py::test_reversed_and_bot_excluded_from_overlap` |

## 对账规则
原始行=采信事件+无效曝光+重复回调+其他隔离+空行。原始费用-合法扣减=应付。CPM单位为CNY/千次，先按渠道和北京时间账日求和，再HALF_UP舍入到分。扣减额采用原始舍入总额与净额之差，保证分币守恒。机器事件优先于频次，机器事件不消耗频次；频次按渠道、账日、用户计数。冲销事件本身不计曝光，不占频次，须不早于原事件且渠道相同。ID保留为字符串。

跨渠道账单在上述应付基础上再做重叠裁决：同一 `campaign_id` 对同一用户的曝光，以最早一条为锚点切闭区间 30 分钟窗口；窗口内跨渠道重复触达只计一次有效触达，锚点渠道保留收入，其余渠道形成重叠抵扣。账单身份为 `原始费用-冲销抵扣-重叠抵扣=应付`，并校验每条曝光至多抵扣一次。补数按 `(bill_id, version)` 归档，失败保留旧版、重试幂等。

## 已知不覆盖
本地样例资费按月固定，不实现实时竞价和竞价超时。冲销只处理整次曝光，不支持部分曝光冲销。重复冲销与对未采信曝光的冲销进入隔离，不能由人工直接改为计费。重叠窗口固定 30 分钟且不跨活动自定义。
