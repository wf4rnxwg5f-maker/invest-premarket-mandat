"""Тесты движка мандата (stdlib unittest, без внешних зависимостей).
Запуск из каталога prototype:  python3 -m unittest test_engine -v
"""
import random
import unittest

from mandate_engine import Instrument, Order, Rule, State, cancel, decide, fill, place

REF = {
    "GAZP": Instrument("GAZP", "share", "ПАО Газпром", "Газпром", lot=10, listing_level=1, median_turnover=9.8e9),
    "GAZB": Instrument("GAZB", "bond", "ООО Газпром капитал", "Газпром", lot=1, listing_level=1, median_turnover=5e7),
    "SIBN": Instrument("SIBN", "share", "ПАО Газпром нефть", "Газпром", lot=1, listing_level=3, median_turnover=6.6e8),
    "MGNT": Instrument("MGNT", "share", "ПАО Магнит", "Магнит", lot=1, listing_level=3, median_turnover=1.03e9),
    "SBER": Instrument("SBER", "share", "ПАО Сбербанк", "Сбер", lot=1, listing_level=1, median_turnover=6.7e9),
    "ILLQ": Instrument("ILLQ", "share", "ПАО Неликвид", "Неликвид", lot=10, listing_level=1, median_turnover=5.7e6),
    "OFZ1": Instrument("OFZ1", "bond", "Минфин РФ", "РФ", lot=1, listing_level=1, median_turnover=2e9, is_ofz=True),
    "FUT1": Instrument("FUT1", "futures", "Мосбиржа", "Мосбиржа", lot=1),
}
PRICES = {"GAZP": 130.0, "GAZB": 950.0, "SIBN": 530.0, "MGNT": 2000.0, "SBER": 300.0,
          "ILLQ": 50.0, "OFZ1": 700.0, "FUT1": 1000.0}

# Мандат из сценария анкеты: 8 правил из текста клиента (R0–R7) + 1 системное (S1).
RULES = [
    Rule("R0", "allow_only", {"buy_classes": ["share"]}, "Покупай акции на свободные деньги"),
    Rule("R1", "max_share_after", {"scope": "group", "pct": 10, "exclude_ofz": True, "denominator": "with_cash"},
         "Не больше 10% портфеля в одну компанию (группа; ОФЗ не в счёт; доля от портфеля с деньгами)"),
    Rule("R2", "max_order_value", {"rub": 30_000}, "заявка до 30 тыс. ₽"),
    Rule("R3", "max_day_value", {"rub": 100_000}, "за день до 100 тыс. ₽ (по выставленным заявкам)"),
    Rule("R4", "no_sell", {"ofz": True}, "ОФЗ не продавай"),
    Rule("R5", "min_median_turnover", {"rub": 10e6, "classes": ["share"]}, "третий эшелон не бери → оборот ≥ 10 млн ₽/день"),
    Rule("R6", "no_margin_short", {}, "без плеча (на свободные деньги) и без шортов"),
    Rule("R7", "ban_classes", {"classes": ["futures", "option"]}, "без фьючерсов"),
    Rule("S1", "max_day_orders", {"n": 20}, "системное: не более 20 заявок в день"),
]


def fresh_state():
    # итого 839 тыс. ₽: деньги 350, ОФЗ 350, SBER 60, MGNT 40, GAZP 39
    books = {t: {"asks": [(p, 10_000)], "bids": [(p, 10_000)]} for t, p in PRICES.items()}
    return State(cash=350_000.0, positions={"SBER": 200, "OFZ1": 500, "MGNT": 20, "GAZP": 300},
                 prices=dict(PRICES), books=books)


def total(st):
    return st.cash + sum(q * st.prices[t] for t, q in st.positions.items())


def group_share(st, group):
    v = sum(q * st.prices[t] for t, q in st.positions.items() if REF[t].group == group)
    return v / total(st)


def D(rules, st, o):
    return decide(rules, st, REF, o).decision


class TestScenario(unittest.TestCase):
    def test_four_orders_from_the_form(self):
        st = fresh_state()
        orders = [Order("GAZP", "buy", 20, 130.0), Order("MGNT", "buy", 10, 2000.0),
                  Order("SBER", "buy", 50, 300.0), Order("ILLQ", "buy", 40, 50.0)]
        got = []
        for o in orders:
            v = decide(RULES, st, REF, o)
            got.append(v.decision)
            if v.decision == "allow":
                place(st, REF, o)
        self.assertEqual(got, ["allow", "allow", "allow", "deny"])
        self.assertIn("R5", decide(RULES, st, REF, orders[3]).rule_ids)

    def test_whitelist_asks_outside_permissions(self):
        st = fresh_state()
        self.assertEqual(D(RULES, st, Order("SBER", "sell", 50, 300.0)), "ask")   # продажа не разрешена явно
        self.assertEqual(D(RULES, st, Order("GAZB", "buy", 5, 950.0)), "ask")    # облигации не разрешены явно
        self.assertEqual(D(RULES, st, Order("OFZ1", "sell", 10, 700.0)), "deny")  # прямо запрещено
        self.assertEqual(D(RULES, st, Order("FUT1", "buy", 1, 1000.0)), "deny")   # прямо запрещено
        self.assertEqual(D([r for r in RULES if r.id != "R0"], st, Order("SBER", "buy", 1, 300.0)), "ask")

    def test_listing_vs_turnover_reading(self):
        # MGNT: 3-й уровень листинга, но ликвидна; ILLQ: 1-й уровень, но неликвидна.
        st = fresh_state()
        by_listing = [RULES[0], Rule("RL", "max_listing_level", {"level": 2})]
        by_turnover = [RULES[0], RULES[5]]
        self.assertEqual(D(by_listing, st, Order("MGNT", "buy", 1, 2000.0)), "deny")
        self.assertEqual(D(by_listing, st, Order("ILLQ", "buy", 10, 50.0)), "allow")
        self.assertEqual(D(by_turnover, st, Order("MGNT", "buy", 1, 2000.0)), "allow")
        self.assertEqual(D(by_turnover, st, Order("ILLQ", "buy", 10, 50.0)), "deny")

    def test_group_vs_security(self):
        st = fresh_state()
        st.positions.update({"GAZP": 500, "SIBN": 30})        # группа «Газпром»: 65k + 15.9k ≈ 9.2%
        o = Order("GAZB", "buy", 20, 950.0)                   # облигации «Газпром капитала» на 19k
        allow_bonds = Rule("R0b", "allow_only", {"buy_classes": ["share", "bond"]})
        self.assertEqual(D([allow_bonds, RULES[1]], st, o), "deny")
        by_security = Rule("RS", "max_share_after", {"scope": "security", "pct": 10})
        self.assertEqual(D([allow_bonds, by_security], st, o), "allow")

    def test_denominator_is_a_convention(self):
        st = fresh_state()                                    # GAZP 39k: 4.6% с деньгами, 8.0% без денег
        o = Order("GAZP", "buy", 30, 130.0)                   # +39k
        with_cash = Rule("D1", "max_share_after", {"scope": "group", "pct": 10, "denominator": "with_cash"})
        no_cash = Rule("D2", "max_share_after", {"scope": "group", "pct": 10, "denominator": "securities"})
        self.assertEqual(D([RULES[0], with_cash], st, o), "allow")
        self.assertEqual(D([RULES[0], no_cash], st, o), "deny")


class TestLimits(unittest.TestCase):
    def test_order_value(self):
        st = fresh_state()
        self.assertEqual(D(RULES, st, Order("MGNT", "buy", 15, 2000.0)), "allow")   # 30 000 — ровно порог
        v = decide(RULES, st, REF, Order("MGNT", "buy", 16, 2000.0))               # 32 000
        self.assertEqual((v.decision, v.rule_ids), ("deny", ("R2",)))

    def test_day_value_counts_active_orders(self):
        st = fresh_state()
        rules = [RULES[0], RULES[2], RULES[3], RULES[6]]
        results = []
        for _ in range(5):
            o = Order("SBER", "buy", 95, 300.0)               # 28.5k: ниже порога на заявку
            d = D(rules, st, o)
            results.append(d)
            if d == "allow":
                place(st, REF, o)                             # выставлена, но НЕ исполнена
        self.assertEqual(results, ["allow", "allow", "allow", "deny", "deny"])

    def test_day_orders(self):
        st = fresh_state()
        rules = [RULES[0], RULES[8]]
        for _ in range(20):
            o = Order("SBER", "buy", 1, 300.0)
            self.assertEqual(D(rules, st, o), "allow")
            place(st, REF, o)
        self.assertEqual(D(rules, st, Order("SBER", "buy", 1, 300.0)), "deny")

    def test_no_margin_counts_reserved_cash(self):
        st = fresh_state()
        st.cash = 40_000.0
        rules = [RULES[0], RULES[6]]
        place(st, REF, Order("SBER", "buy", 100, 300.0))       # резерв 30k
        self.assertEqual(D(rules, st, Order("MGNT", "buy", 5, 2000.0)), "allow")  # 30k резерв + 10k = 40k — ровно
        st.cash = 39_999.0
        self.assertEqual(D(rules, st, Order("MGNT", "buy", 5, 2000.0)), "deny")

    def test_no_short_counts_active_sells(self):
        st = fresh_state()
        rules = [Rule("R0s", "allow_only", {"buy_classes": ["share"], "sell_classes": ["share"]}), RULES[6]]
        place(st, REF, Order("SBER", "sell", 150, 300.0))      # из 200 шт.
        self.assertEqual(D(rules, st, Order("SBER", "sell", 50, 300.0)), "allow")
        self.assertEqual(D(rules, st, Order("SBER", "sell", 51, 300.0)), "deny")


class TestFailClosed(unittest.TestCase):
    def test_market_order_walks_the_book(self):
        st = fresh_state()
        st.books["MGNT"] = {"asks": [(2000.0, 5), (2010.0, 5), (2100.0, 100)], "bids": []}
        v = decide([RULES[0], RULES[2]], st, REF, Order("MGNT", "buy", 12, None))
        self.assertEqual(v.decision, "allow")                 # 24 250 ₽ < 30 000 ₽
        v = decide([RULES[0], RULES[2]], st, REF, Order("MGNT", "buy", 16, None))
        self.assertEqual(v.decision, "deny")                  # 5·2000 + 5·2010 + 6·2100 = 32 650 ₽ > 30 000 ₽
        self.assertEqual(D([RULES[0], RULES[2]], st, Order("MGNT", "buy", 200, None)), "ask")  # глубины не хватает

    def test_missing_data_asks(self):
        st = fresh_state()
        self.assertEqual(D(RULES, st, Order("XXXX", "buy", 1, 10.0)), "ask")      # нет в справочнике
        st.prices.pop("SIBN")
        st.positions["SIBN"] = 10
        self.assertEqual(D(RULES, st, Order("GAZP", "buy", 1, 130.0)), "ask")     # позиция без цены
        st2 = fresh_state()
        st2.books.pop("MGNT")
        self.assertEqual(D(RULES, st2, Order("MGNT", "buy", 1, None)), "ask")     # нет стакана
        self.assertEqual(D(RULES, st2, Order("MGNT", "buy", 1, None, stop=True)), "ask")

    def test_bad_input_is_denied(self):
        st = fresh_state()
        self.assertEqual(D(RULES, st, Order("SBER", "buy", 0, 300.0)), "deny")


class TestInvariants(unittest.TestCase):
    """Случайные последовательности «выставить / исполнить частично / снять»."""

    def _run(self, rules, n_runs, seed, sells):
        rng = random.Random(seed)
        tickers = [t for t in REF if t != "FUT1"]
        for _ in range(n_runs):
            st = fresh_state()
            ofz0 = st.positions["OFZ1"]
            for _ in range(rng.randint(1, 60)):
                act = rng.random()
                if act < 0.55 or not st.active:
                    t = rng.choice(tickers)
                    side = "sell" if sells and rng.random() < 0.35 else "buy"
                    o = Order(t, side, rng.randint(1, 80), rng.choice([PRICES[t], None]))
                    if D(rules, st, o) == "allow":
                        place(st, REF, o)
                elif act < 0.9:
                    i = rng.randrange(len(st.active))
                    fill(st, REF, i, rng.randint(1, st.active[i].lots), PRICES[st.active[i].ticker])
                else:
                    cancel(st, rng.randrange(len(st.active)))
                self.assertGreaterEqual(st.cash, -1e-6)                       # без плеча
                self.assertTrue(all(q >= 0 for q in st.positions.values()))   # без шортов
                self.assertLessEqual(st.placed_value_today, 100_000 + 1e-6)
                self.assertLessEqual(st.placed_count_today, 20)
                self.assertGreaterEqual(st.positions.get("OFZ1", 0), ofz0)    # ОФЗ не продаются
                for g in ("Газпром", "Магнит", "Неликвид", "Сбер"):
                    if sells:
                        continue
                    self.assertLessEqual(group_share(st, g), 0.10 + 1e-9, g)

    def test_mandate_from_the_form(self):
        self._run(RULES, 1500, 20261113, sells=False)

    def test_trader_mandate_with_sells(self):
        rules = [Rule("R0s", "allow_only", {"buy_classes": ["share"], "sell_classes": ["share"]}),
                 RULES[3], RULES[4], RULES[6], RULES[8]]
        self._run(rules, 1500, 7, sells=True)


if __name__ == "__main__":
    unittest.main()
