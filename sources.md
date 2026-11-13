# Источники к ответам (проверены 12–13.11.2026)

## Т-Инвестиции и T-Invest MCP
1. «Ведомости», 10.09.2026 — T-Invest MCP открыт всем клиентам; по умолчанию только просмотр, торговые права включаются отдельно; В. Савенкова («Велес Капитал»): «финальное подтверждение человеком – недостаточная защита», нужны «ограничение полномочий на уровне настроек и возможность заранее задать границы»; юрист А. Федотова: в журнале брокера невозможно увидеть промпт пользователя и ответ модели. https://www.vedomosti.ru/investments/articles/2026/09/10/1227646-t-investitsii-otkrili-ii-agentam-dostup-k-schetam
2. Блог Т-Инвестиций на smart-lab, 16.10.2026 — «само подключение через MCP не означает, что агент будет запрашивать ваше согласие на каждую сделку»; подтверждение, статусы и ошибки нужно предусмотреть в продукте; три вида токена. https://smart-lab.ru/company/t_invest/blog/1363508.php
3. Туториал Т-Банка на Хабре (26 сентября) — cron-задача в 03:00 ставит take-profit +20% к средней цене; шаг подтверждения в сценарии не описан; для MCP нужны сертификаты Минцифры. https://habr.com/ru/companies/tbank/articles/1086714/
4. «Ридус», 10.11.2026 — со слов А. Гусева (Т-Банк) на мероприятии Frank RG: >14 млн запросов в месяц к ИИ-агентам через MCP; около 5% пользователей ИИ-агентов совершают с их помощью сделки; Frank RG: следовать советам ИИ готовы 5,4–9,9% инвесторов. https://www.ridus.ru/ii-agenty--t-bank--obrabotali-14-mln-investzaprosov-v-mesyac-984305.html
5. Документация T-Invest API (официальный репозиторий): виды токенов, в т.ч. токен на один счёт; ограничений по бумагам и суммам нет; сделки >30 млн ₽ требуют подтверждения. https://raw.githubusercontent.com/RussianInvestments/investAPI/main/src/docs/token.md
6. Контракт счетов: уровни доступа FULL_ACCESS / READ_ONLY / NO_ACCESS. https://raw.githubusercontent.com/RussianInvestments/investAPI/main/src/docs/contracts/users.proto
7. Контракт инструментов: sector, risk_level, флаги облигаций, liquidity_flag, for_qual_investor_flag, asset_uid, brand; уровня листинга и идентификатора эмитента нет. https://raw.githubusercontent.com/RussianInvestments/investAPI/main/src/docs/contracts/instruments.proto
8. FAQ T-Invest API: публичный сервис на основе API сделать нельзя, без права ретрансляции данных. https://raw.githubusercontent.com/RussianInvestments/investAPI/main/src/docs/faq_rules.md
9. Лимиты T-Invest API (50–600 unary-запросов в минуту по сервисам; стоп-заявки — 50). https://raw.githubusercontent.com/RussianInvestments/investAPI/main/src/docs/limits.md
10. Песочница T-Invest API: исполнение по последним сделкам, маржинальные показатели не считаются. https://raw.githubusercontent.com/RussianInvestments/investAPI/main/src/docs/faq_sandbox.md
11. Страница программы «Инвест. Премаркет». https://meetup.tbank-online.com/invest.premarket

## Рынок и регуляторы
12. BFM (через «Рамблер»), 11.09.2026 — «Финам» откроет сделки через ИИ после внедрения риск-менеджмента и механизмов подтверждения. https://finance.rambler.ru/business/57046170-za-posledniy-mesyats-srazu-tri-rossiyskih-brokera-razreshili-investoram-ispolzovat-ii/
13. FINRA, 2026 Annual Regulatory Oversight Report (GenAI): агенты «may act beyond the user's actual or intended scope and authority». https://www.finra.org/rules-guidance/guidance/reports/2026-finra-annual-regulatory-oversight-report/gen-ai
14. StockBrokers.com, обзор от 02.11.2026: Webull — лимит заявки, число акций, белый список; tastytrade — потолок $50 000; IBKR — AI Partition; Robinhood — отдельный счёт, подтверждение для MCP-агентов по умолчанию выключено; kill switch ни у кого не описан. https://www.stockbrokers.com/guides/ai-agent-brokers
15. AWS, Policy in Amazon Bedrock AgentCore (GA 03.03.2026): политики на естественном языке → Cedar, проверка вызовов инструментов на шлюзе; «Policies must be clear and unambiguous». https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html , https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-natural-language.html
16. Банк России, методические рекомендации по ИБ при разработке и применении ИИ на финансовом рынке (16.06.2026), п. 2.5. https://www.cbr.ru/Crosscut/LawActs/File/12204
17. 149-ФЗ, ч. 8 ст. 10 — запрет финансовым организациям передавать ПДн и сведения о счетах через иностранные мессенджеры. https://www.consultant.ru/document/cons_doc_LAW_61798/546dcc703c0a1e08647b40a2eeaf9461168c7cb1/
18. Условия использования MOEX ISS — только для ознакомления; сервисы для третьих лиц — по договору. https://www.moex.com/a2193
19. Мосбиржа, итоги октября 2026: 43 млн частных инвесторов, сделки совершали более 3 млн. https://iss.moex.com/iss/sitenews/105753.json?lang=ru
20. Неофициальный MCP-сервер tinvest-mcp с лимитами в конфиге. https://github.com/plasm-one/tinvest-mcp

## Надёжность агентов и подтверждений
21. Anthropic, 25.03.2026 — пользователи принимают 93% запросов на разрешение. https://www.anthropic.com/engineering/claude-code-auto-mode
22. Anthropic, 07.08.2026 — 97% одобрений; люди-проверяющие остановили 13,6% опасных команд (143 из 1 053). https://claude.com/resources/articles/auto-mode-default-in-claude-code
23. InjecAgent (2024): непрямая инъекция успешна в 24% случаев, с усиленным промптом — 47%. https://arxiv.org/html/2403.02691v3
24. Agent Security Bench (2024): до 84,3% успешных атак. https://arxiv.org/html/2410.02644v2
25. MCPTox (2025): отравление описаний инструментов MCP, до 72,8% успешных атак. https://arxiv.org/html/2508.14925v1
26. Progent (v3, 14.05.2026): политики вне модели снижают успех атак на AgentDojo с 39,9% до 1,0%, на ASB с 70,3% до 3,9%. https://arxiv.org/html/2504.11703v3
27. LlamaFirewall (2025): на AgentDojo с 17,6% до 1,75%. https://arxiv.org/html/2505.03574
28. SEC, дело Knight Capital (2013) — первое дело по Rule 15c3-5 о предторговых контролях. https://www.sec.gov/news/press-release/2013-222

## Данные Банка России
33. Ключевая ставка 14,00% на 12.11.2026 (используется в прочтении «ВДО»). https://www.cbr.ru/hd_base/KeyRate/

## Модели
29. T-pro-it-2.1 (Apache 2.0, на основе Qwen3-32B). https://huggingface.co/t-tech/T-pro-it-2.1

## Собственные расчёты
30. Пилот 1 — MOEX ISS (TQBR, TQCB, история, индексы), 12.11.2026: `pilot/scripts/readings.py`, `pilot/readings.txt`.
31. Пилот 2 — корпус публичных правил частных инвесторов: `pilot/coverage/`.
32. Прототип движка и тесты: `prototype/`.
34. Пилот 3 — компиляция мандатов двумя LLM и стабильность LLM-судьи: `pilot/p3/`.
35. Проверка отброшенной идеи «окно оферты» правилом: `pilot/offer_window/`.
