"""Топики Kafka для обмена событиями между сервисами.
Все названия собраны в одном месте для единообразия.
"""

# События домена (факты)
ORDERS_EVENTS = "orders.events"
PAYMENTS_EVENTS = "payments.events"
INVENTORY_EVENTS = "inventory.events"

# Команды (запросы к сервисам)
PAYMENTS_COMMANDS = "payments.commands"
INVENTORY_COMMANDS = "inventory.commands"
