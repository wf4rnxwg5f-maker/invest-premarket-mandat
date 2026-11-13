"""Детерминированный движок мандата: политика × состояние × заявка → решение.

LLM в этом модуле нет: он только исполняет политику, которую составил компилятор
и подписал владелец счёта. Решение воспроизводимо и объяснимо (номер правила).

Принципы:
- белый список действий: что мандат явно не разрешил — «спросить владельца»;
- лимиты считаются по ВЫСТАВЛЕННЫМ заявкам (исполненные + активные + новая),
  а не по исполненным: дробление и пачки неисполненных заявок их не обходят;
- рыночная заявка оценивается по худшему исходу в стакане на весь объём;
- нет данных → «спросить», ошибка в движке → «отклонить» (fail-closed).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Decision = Literal["allow", "ask", "deny"]


@dataclass(frozen=True)
class Instrument:
    ticker: str
    klass: str                 # share | bond | etf | futures | option | currency
    issuer: str                # юрлицо-эмитент (emitent_id)
    group: str                 # группа компаний (собственный справочник)
    lot: int = 1
    listing_level: int | None = None
    median_turnover: float | None = None   # ₽ в день, медиана за 20 торговых дней
    is_ofz: bool = False


@dataclass(frozen=True)
class Order:
    ticker: str
    side: Literal["buy", "sell"]
    lots: int
    price: float | None        # None = рыночная заявка
    stop: bool = False         # стоп-заявка: проверяется при выставлении как исполненная


@dataclass
class State:
    cash: float
    positions: dict[str, int] = field(default_factory=dict)      # ticker -> штук
    prices: dict[str, float] = field(default_factory=dict)       # последняя цена (оценка позиций)
    books: dict[str, dict] = field(default_factory=dict)         # ticker -> {"asks": [(цена, штук)], "bids": [...]}
    active: list[Order] = field(default_factory=list)            # выставленные и не исполненные (в т.ч. стоп)
    placed_value_today: float = 0.0                              # стоимость выставленных сегодня заявок
    placed_count_today: int = 0


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    params: dict
    source: str = ""           # фрагмент мандата или «системное правило»


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    rule_ids: tuple
    reasons: tuple


class NoData(Exception):
    """Не хватает данных для честного расчёта — решает владелец."""


def worst_value(o: Order, inst: Instrument, st: State) -> float:
    """Стоимость заявки в худшем исходе. Лимитная — по цене заявки; рыночная — проходом по стакану."""
    qty = o.lots * inst.lot
    if o.lots <= 0:
        raise ValueError("lots must be positive")
    if o.price is not None:
        return o.price * qty
    book = st.books.get(o.ticker)
    if not book:
        raise NoData(f"нет стакана по {o.ticker}")
    levels = book["asks"] if o.side == "buy" else book["bids"]
    left, value = qty, 0.0
    for px, q in levels:
        take = min(left, q)
        value += take * px
        left -= take
        if left == 0:
            break
    if left > 0:
        raise NoData(f"глубины стакана {o.ticker} не хватает на {qty} шт.")
    if o.side == "sell":
        # для продажи худший исход — минимальная выручка; для лимитов берём её же
        return value
    return value


def _position_value(st: State, t: str) -> float:
    if st.positions.get(t, 0) == 0:
        return 0.0
    if t not in st.prices:
        raise NoData(f"нет цены по позиции {t}")
    return st.positions[t] * st.prices[t]


def _exposure(rule: Rule, st: State, ref: dict[str, Instrument], new: Order) -> tuple[float, float, str]:
    p = rule.params
    keyf = {"security": lambda i: i.ticker, "issuer": lambda i: i.issuer, "group": lambda i: i.group}[p["scope"]]
    inst = ref[new.ticker]
    key = keyf(inst)
    held = 0.0
    securities = 0.0
    for t in st.positions:
        if t not in ref:
            raise NoData(f"бумаги {t} нет в справочнике")
        v = _position_value(st, t)
        securities += v
        if keyf(ref[t]) == key:
            held += v
    for o in st.active + [new]:
        if o.side != "buy":
            continue
        if o.ticker not in ref:
            raise NoData(f"бумаги {o.ticker} нет в справочнике")
        if keyf(ref[o.ticker]) == key:
            held += worst_value(o, ref[o.ticker], st)
    denom = st.cash + securities if p.get("denominator", "with_cash") == "with_cash" else securities + sum(
        worst_value(o, ref[o.ticker], st) for o in st.active + [new] if o.side == "buy")
    return held, denom, key


def _decide(rules: list[Rule], st: State, ref: dict[str, Instrument], o: Order) -> Verdict:
    if o.ticker not in ref:
        return Verdict("ask", ("SYS",), ("бумаги нет в справочнике — решает владелец",))
    inst = ref[o.ticker]
    if o.stop and o.price is None:
        return Verdict("ask", ("SYS",), ("у стоп-заявки нет цены исполнения — худший исход не оценить",))
    value = worst_value(o, inst, st)
    qty = o.lots * inst.lot
    deny, ask = [], []
    allowed_by_whitelist = None

    for r in rules:
        p = r.params
        k = r.kind
        if k == "allow_only":
            ok = (o.side == "buy" and inst.klass in p.get("buy_classes", ())) or \
                 (o.side == "sell" and inst.klass in p.get("sell_classes", ()))
            allowed_by_whitelist = ok
            if not ok:
                ask.append((r.id, "действие не разрешено мандатом явно"))
        elif k == "ban_classes" and inst.klass in p["classes"]:
            deny.append((r.id, f"класс «{inst.klass}» запрещён"))
        elif k == "no_margin_short":
            if o.side == "sell":
                reserved = sum(a.lots * ref[a.ticker].lot for a in st.active
                               if a.side == "sell" and a.ticker == o.ticker)
                if qty > st.positions.get(o.ticker, 0) - reserved:
                    deny.append((r.id, "продажа больше свободной позиции — это короткая продажа"))
            else:
                committed = sum(worst_value(a, ref[a.ticker], st) for a in st.active if a.side == "buy")
                if committed + value > st.cash + 1e-9:
                    deny.append((r.id, "на заявку не хватает свободных денег — это плечо"))
        elif k == "max_order_value" and value > p["rub"]:
            deny.append((r.id, f"заявка {value:,.0f} ₽ > {p['rub']:,.0f} ₽"))
        elif k == "max_day_value" and st.placed_value_today + value > p["rub"]:
            deny.append((r.id, f"выставлено за день {st.placed_value_today + value:,.0f} ₽ > {p['rub']:,.0f} ₽"))
        elif k == "max_day_orders" and st.placed_count_today + 1 > p["n"]:
            deny.append((r.id, f"заявок за день больше {p['n']}"))
        elif k == "no_sell" and o.side == "sell" and ((p.get("ofz") and inst.is_ofz) or o.ticker in p.get("tickers", ())):
            deny.append((r.id, "продажа этой бумаги запрещена мандатом"))
        elif k == "min_median_turnover" and o.side == "buy" and inst.klass in p.get("classes", (inst.klass,)):
            if inst.median_turnover is None:
                ask.append((r.id, "нет данных об обороте"))
            elif inst.median_turnover < p["rub"]:
                deny.append((r.id, f"медианный оборот {inst.median_turnover/1e6:.1f} млн ₽ < {p['rub']/1e6:.0f} млн ₽"))
        elif k == "max_listing_level" and o.side == "buy":
            if inst.listing_level is None:
                ask.append((r.id, "нет уровня листинга"))
            elif inst.listing_level > p["level"]:
                deny.append((r.id, f"уровень листинга {inst.listing_level} > {p['level']}"))
        elif k == "max_share_after" and o.side == "buy":
            if p.get("exclude_ofz") and inst.is_ofz:
                continue                       # «в одну компанию»: государство компанией не считаем
            held, denom, key = _exposure(r, st, ref, o)
            share = held / denom if denom > 0 else 1.0
            if share > p["pct"] / 100 + 1e-12:
                deny.append((r.id, f"доля «{key}» после заявки {share:.1%} > {p['pct']}%"))

    if deny:
        return Verdict("deny", tuple(i for i, _ in deny), tuple(t for _, t in deny))
    if ask:
        return Verdict("ask", tuple(i for i, _ in ask), tuple(t for _, t in ask))
    if allowed_by_whitelist is None:
        return Verdict("ask", ("SYS",), ("в мандате нет разрешающего правила — решает владелец",))
    return Verdict("allow", (), ())


def decide(rules: list[Rule], st: State, ref: dict[str, Instrument], o: Order) -> Verdict:
    try:
        return _decide(rules, st, ref, o)
    except NoData as e:
        return Verdict("ask", ("SYS",), (str(e),))
    except Exception as e:  # noqa: BLE001 — fail-closed
        return Verdict("deny", ("SYS",), (f"ошибка проверки: {e}",))


# ---------- модель исполнения (для тестов на инварианты) ----------

def place(st: State, ref: dict[str, Instrument], o: Order) -> None:
    """Выставить разрешённую заявку: она резервирует дневные лимиты сразу."""
    st.placed_value_today += worst_value(o, ref[o.ticker], st)
    st.placed_count_today += 1
    st.active.append(o)


def fill(st: State, ref: dict[str, Instrument], idx: int, lots: int, px: float) -> None:
    """Исполнить lots лотов активной заявки idx по цене px (частичное исполнение допустимо)."""
    o = st.active[idx]
    lots = min(lots, o.lots)
    qty = lots * ref[o.ticker].lot
    if o.side == "buy":
        st.cash -= qty * px
        st.positions[o.ticker] = st.positions.get(o.ticker, 0) + qty
    else:
        st.cash += qty * px
        st.positions[o.ticker] = st.positions.get(o.ticker, 0) - qty
    rest = o.lots - lots
    if rest:
        st.active[idx] = Order(o.ticker, o.side, rest, o.price, o.stop)
    else:
        st.active.pop(idx)


def cancel(st: State, idx: int) -> None:
    """Снять заявку. Дневной лимит выставленного она не возвращает (консервативно)."""
    st.active.pop(idx)
