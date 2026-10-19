"""自拟反例：验证两个教师样例未覆盖的边界行为。

1. 观察窗口末尾：大分组跨 tick 未发完，剩余部分必须计入积压(backlog)，
   而不能误判为尾丢弃(loss)；已完成的记录仍要正常统计时延。
2. 电路交换固定时隙：非本时隙用户即使有数据排队，也不能借用空时隙。
"""
from src.models import Config, Arrival
from src.utils import simulate
from src.metrics import summarize


def test_window_end_inflight_record_is_backlog_not_loss():
    # 128 bit 载荷 + 32 bit 包头 = 160 wire bit；2 tick 窗口共 256 wire bit。
    # 两条记录共 320 wire bit，第二条在窗口结束时仍在途，只能算积压。
    cfg = Config(ticks=2, slot_bits=128, buffer_payload_bits=4096)
    arrivals = [Arrival(0, 0, 128), Arrival(0, 0, 128)]
    raw = simulate(arrivals, cfg, 'packet')
    # 第一条在 tick1 完成(时延 2 ms)；第二条未完成，保留 128 bit 原始载荷。
    assert raw['delivered_payload_bits'] == 128
    assert raw['dropped_payload_bits'] == 0
    assert raw['backlog_payload_bits'] == 128
    m = summarize(raw, cfg)
    # 守恒：generated = delivered + dropped + backlog，不相等会抛 ValueError。
    assert m['payload_utilization'] == 128 / 256
    assert m['mean_delay_ms'] == 2.0
    assert m['max_delay_ms'] == 2.0
    assert m['loss_ratio'] == 0.0


def test_circuit_idle_slot_cannot_be_borrowed():
    # 只有用户0在 tick0 有 200 bit 载荷；2 tick 窗口内：
    # tick0 服务用户0(发 128 bit)，tick1 服务用户1(空)，用户0不能借用。
    cfg = Config(users=2, ticks=2, slot_bits=128)
    raw = simulate([Arrival(0, 0, 200)], cfg, 'circuit')
    assert raw['delivered_payload_bits'] == 0
    assert raw['wire_sent_bits'] == 128
    assert raw['backlog_payload_bits'] == 200
