# AI协作记录

工具与模型：Claude Code（Anthropic，模型 claude-opus-5-5）。

## 一项真实协作过程

需求与输入：补全三个必做函数——`src/part1_circuit.py` 的 `serve_circuit`、`src/part2_packet.py` 的 `serve_packet`、`src/metrics.py` 的 `summarize`，并用教师提供的 `grading/` 测试与四种业务仿真验证。

AI建议：`serve_circuit` 先按 `tick % cfg.users` 锁定本时隙用户，再在其队列上以 `slot_bits` 为预算逐条 `min(remaining_wire_bits, budget)` 扣减，发完才 `popleft` 并计入完成列表；`serve_packet` 用同样的预算填充规则在共享队首上执行，队首发完才处理下一条，`remaining_wire_bits` 在准入时已含包头、续传时不重加；`summarize` 先做 `generated == delivered + dropped + backlog` 守恒校验，再算利用率与时延，无完成记录时时延返回 `None`。

我的手算与测试：用 2 用户、2 tick、slot_bits=8、header_bits=4 的小例手算（到达：用户0 生成 10 bit、用户1 生成 8 bit）。电路模式 tick0 只服务用户0（发 8 bit 剩 2），tick1 服务用户1（发 8 bit 完成），结果交付 8 bit、积压 10 bit；分组模式按队首连续发送，tick0 发用户0 的 8 bit，tick1 发完用户0 剩 6 bit 后再发用户1 2 bit，结果交付 10 bit、积压 8 bit。手算预期与代码输出一致。边界验证对应 `grading/test_circuit.py::test_partial`、`grading/test_packet.py::test_fifo_no_interleave`、`student_tests/test_my_case.py` 两条用例。

修正或采纳理由：首次生成即正确，`grading/` 下 23 个测试全部通过，自动评分为 70/70。无需修正；补充边界验证确认：跨 tick 续传不会重复加包头、观察窗口末尾仍在途的记录计入积压而非丢失、固定时隙空槽不被借用。

我能解释的核心逻辑：包头只在准入初始化 `remaining_wire_bits` 时加一次，续传只做减法，所以不会每个 tick 重加 32 bit 包头；电路只在 `tick % users` 对应队列服务，其他用户不能借用空时隙；`summarize` 的守恒式把未完成记录计入 `backlog`，避免把积压数据误报成已完成或丢弃，从而防止“只看成功记录平均时延而忽略积压”的误导。
