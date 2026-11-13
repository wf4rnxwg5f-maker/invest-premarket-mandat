# Закрытый язык правил мандата (v0, для пилота 3)

Мандат — то, что владелец счёта разрешает и запрещает своему ИИ-агенту. Шлюз проверяет каждую заявку агента по правилам ДО отправки брокеру. Правило должно проверяться кодом по данным заявки, портфеля и справочников, без суждений.

## Статусы для каждого пункта мандата
- `rule` — пункт точно выражается одним или несколькими правилами ниже (params заполнены конкретными значениями).
- `needs_clarification` — пункт опирается на понятие без единственного определения («третий эшелон», «мусорные», «дивидендные», «надёжные», «короткие», «дорогие»): разумные прочтения дадут разные решения по реальным бумагам. Укажи понятие и 2–4 конкретных прочтения (через какие данные его можно определить).
- `cannot_express` — пункт проверяем в принципе, но в этом языке нет подходящего правила (укажи, чего не хватает).
- `principle` — принцип, процесс или философия, которые не проверяются на уровне заявки («без эмоций», «изучаю отчётность», «держу долго»).
- `duty` — обязанность что-то СДЕЛАТЬ, а не ограничение («ставлю стоп-лосс», «реинвестирую», «ребалансирую раз в квартал»). Шлюз её не исполняет; её можно передать агенту как задачу.

## Типы правил (rule_kind) и параметры
1. `allow_only` — что агенту разрешено: buy_classes, sell_classes (share, bond, etf, futures, option, currency, metal).
2. `ban_classes` — запрещённые классы: classes.
3. `ban_instruments` / `allow_instruments` — конкретные бумаги или списки: tickers или описание списка.
4. `max_share` — потолок доли: scope (security | issuer | group | sector | asset_class | currency | custom_group), pct, denominator (with_cash | securities), exclude (например, ОФЗ).
5. `min_share` — нижняя граница доли: scope, pct.
6. `target_range` — целевой диапазон доли класса: asset_class, min_pct, max_pct.
7. `max_order_value` — потолок одной заявки: rub.
8. `max_position_value` — потолок стоимости одной позиции: rub, scope.
9. `max_day_value` / `max_day_orders` — потолки выставленного за день: rub / n.
10. `max_positions_count` — число позиций или эмитентов: scope, n.
11. `no_sell` — запрет продаж: tickers или classes.
12. `no_margin_short` — без плеча и коротких продаж (или лимит плеча: max_leverage).
13. `min_liquidity` — медианный дневной оборот не ниже rub.
14. `max_listing_level` — уровень листинга не выше level.
15. `index_member` — только бумаги индекса: index.
16. `bond_filter` — фильтр облигаций: min_rating (агентство и шкала), max_maturity_years, max_duration_years, min_issue_size_rub, min_yield, max_yield, ban_flags (subordinated, perpetual, floating, amortization).
17. `share_filter` — фильтр акций: country, has_dividends, min_dividend_yield, sector_ban.
18. `loss_limit` — лимит убытка: period (day | week | month), pct или rub, action (stop_trading_until_period_end | block_new_positions).
19. `position_rule` — правила по состоянию позиции: no_averaging_down, new_position_max_pct, min_holding_days, max_add_to_position_rub.
20. `time_rule` — ограничения во времени: min_days_between_changes, max_changes_per_period, trading_hours.

Если пункт содержит несколько правил, перечисли их все в rules. Если часть пункта выражается, а часть нет — укажи статус по самой проблемной части и опиши выражаемую часть в rules.
