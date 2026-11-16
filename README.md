# 广告曝光有效性与费用结算

按曝光ID裁决重复与冲突，按时间及ID确定日频次，再聚合有效CPM。冲销引用采信的原曝光，同一曝光最多冲销一次，费用回到原曝光账日。同一活动对同一用户的跨渠道曝光按 30 分钟触达窗口去重：最早曝光渠道保留收入，其余渠道按各自合同形成重叠抵扣，广告主只为一次有效触达付费。

使用者按采信、规则复算、异常复核和归档顺序处理一批数据。启动后自动装入异常样例，切换基准样例可比较两者结论；跨渠道账单页使用 overlap 样例演示重叠裁决与晚到补数。

## 启动与测试
```sh
docker compose up --build -d
docker compose exec -T app pytest -q
docker compose config --quiet
```

浏览器打开 [工作台](http://localhost:18205)。

## 业务模块

- 日志采信：读取曝光和冲销台账，入口 `/intake` 与 `GET /api/intake`。
- 计费契约：核查曝光ID、时区和渠道资费，入口 `/contract` 与 `GET /api/contract`。
- 有效性判定：排除机器曝光与超过频次事件，入口 `/model` 与 `GET /api/model`。
- 费用聚合：按渠道账日结算并核查冲销限额，入口 `/calculate` 与 `GET /api/calculate`。
- 争议隔离：定位冲突和无法合法冲销事件，入口 `/quarantine` 与 `GET /api/quarantine`。
- 渠道对账：逐渠道复算账单差额，入口 `/reconcile` 与 `GET /api/reconcile`。
- 跨渠道账单：30分钟窗口重叠裁决、正式账单与补数版本链，入口 `/overlap` 与 `GET /api/overlap`。
- 批次复核：幂等重算与版本归档，入口 `/batches` 与 `GET /api/batches`。

## 演示
选择样例后运行，核对业务结论与来源行。异常行保留原值和原因码。复核提交使用当前版本；旧版本返回 409。CSV证据只保留一个归档入口。

## API
- `POST /api/runs`：JSON 中可指定 `sample`、`text` 与 `params`。
- `POST /api/runs/{run_id}/review`：提交 `revision`、`decision`。
- `GET /api/runs/{run_id}/evidence.csv`：来源证据。
- `GET /api/overlap?sample=overlap`：按样例首次结算，生成跨渠道正式账单 V1。
- `GET /api/overlap/bills/{bill_id}?version=N`：取回指定版本账单，缺省取最新版。
- `POST /api/overlap/bills/{bill_id}/backfill`：提交晚到曝光 `text` 再次结算，生成新版本；结构错误返回 `BACKFILL_SCHEMA`、ID 字段冲突返回 `BACKFILL_CONFLICT`，失败时旧版账单原样保留。
- `GET /api/overlap/bills/{bill_id}/evidence.csv`：含渠道账单、重叠组判断依据与版本链的账单证据。
- `GET /docs`：接口定义。

## 数据保存
SQLite 位于命名卷 records。相同内容、参数与规则版本只产生一条运行记录。仅需重启时执行 `docker compose restart app`。要重新初始化样例数据，先备份所需记录，再执行 `docker compose down -v` 与 `docker compose up --build -d`；此操作会删除当前项目的历史与复核数据。

## 定义与边界
原始行=采信事件+无效曝光+重复回调+其他隔离+空行。原始费用-合法扣减=应付。CPM单位为CNY/千次，先按渠道和北京时间账日求和，再HALF_UP舍入到分。扣减额采用原始舍入总额与净额之差，保证分币守恒。机器事件优先于频次，机器事件不消耗频次；频次按渠道、账日、用户计数。冲销事件本身不计曝光，不占频次，须不早于原事件且渠道相同。ID保留为字符串。

跨渠道重叠：以 `campaign_id`（缺省台账归并为 `CMP-DEFAULT`）加用户分组，组内以最早曝光为锚点切出闭区间 30 分钟触达窗口；窗口内出现多个渠道时，锚点渠道按“先到先得”保留该次有效触达收入，其余渠道的跨渠道曝光按各自 CPM 计为重叠抵扣，同渠道后续曝光仍按频次合同计费。已被合法冲销的曝光不参与重叠裁决，每条曝光至多抵扣一次。重叠抵扣同样按渠道账日聚合后轧差，尾差归入抵扣，保证 `原始费用-冲销抵扣-重叠抵扣=应付`。

补数与版本：补数 CSV 表头须与原台账一致；同 ID 字段完全相同视为重复回调幂等跳过，字段不同即 `BACKFILL_CONFLICT` 拒绝。任何校验失败都在写入前抛出，旧版账单永久保留。账单按 `(bill_id, version)` 归档，相同输入摘要命中同一版本，同批重试不新增曝光、不重复抵扣。

## 已知不覆盖
本地样例资费按月固定，不实现实时竞价和竞价超时。冲销只处理整次曝光，不支持部分曝光冲销。重复冲销与对未采信曝光的冲销进入隔离，不能由人工直接改为计费。重叠窗口固定 30 分钟、按活动+用户判定，不支持活动级自定义窗口或跨账日窗口。

## 目录
`app/modules/` 为八个业务模块，`sample_data/` 提供基准、异常、跨渠道重叠与补数台账，`tests/` 包含模块测试与端到端测试，`docs/` 保存定义与深度登记。
