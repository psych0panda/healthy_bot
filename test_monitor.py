#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсинга конфигурации сервисов
"""

import os
from service_monitor import ServiceMonitor

def test_services_parsing():
    """Тестирование парсинга конфигурации сервисов"""
    
    # Тестовая конфигурация
    test_config = "http://localhost:8080,http://localhost:3000,postgresql,nginx,redis,wg-quick@wg0,minio,docker:jenkins,docker:eager_robinson"
    
    # Временно устанавливаем переменную окружения
    os.environ['SERVICES_TO_MONITOR'] = test_config
    
    # Создаем монитор
    monitor = ServiceMonitor()
    
    print("🔍 Тестирование парсинга конфигурации сервисов")
    print("=" * 60)
    print(f"Конфигурация: {test_config}")
    print("=" * 60)
    
    # Выводим распарсенные сервисы
    for i, service in enumerate(monitor.services, 1):
        print(f"{i}. Имя: {service['name']}")
        print(f"   Тип: {service['type']}")
        print(f"   Конфигурация: {service['config']}")
        print()
    
    print("=" * 60)
    print(f"Всего сервисов: {len(monitor.services)}")
    
    # Проверяем типы сервисов
    type_counts = {}
    for service in monitor.services:
        service_type = service['type']
        type_counts[service_type] = type_counts.get(service_type, 0) + 1
    
    print("\n📊 Распределение по типам:")
    for service_type, count in type_counts.items():
        print(f"   {service_type}: {count}")

if __name__ == '__main__':
    test_services_parsing()
