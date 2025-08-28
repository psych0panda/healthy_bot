#!/usr/bin/env python3
"""
Тестовый скрипт для полной проверки мониторинга сервисов
"""

import os
import time
from service_monitor import ServiceMonitor

def test_full_monitoring():
    """Тестирование полной функциональности мониторинга"""
    
    # Тестовая конфигурация
    test_config = "http://localhost:8080,http://localhost:3000,postgresql,nginx,redis,wg-quick@wg0,minio,docker:jenkins,docker:eager_robinson"
    
    # Временно устанавливаем переменную окружения
    os.environ['SERVICES_TO_MONITOR'] = test_config
    
    # Создаем монитор
    monitor = ServiceMonitor()
    
    print("🔍 Тестирование мониторинга сервисов")
    print("=" * 60)
    print(f"Конфигурация: {test_config}")
    print("=" * 60)
    
    # Проверяем все сервисы
    print("\n📊 Проверка статуса сервисов...")
    statuses = monitor.check_all_services()
    
    # Выводим результаты
    for status in statuses:
        emoji = "✅" if status.status == 'healthy' else "❌" if status.status == 'unhealthy' else "❓"
        details = ""
        
        if status.response_time:
            details = f" ({status.response_time:.2f}s)"
        elif status.uptime:
            hours = status.uptime / 3600
            details = f" (uptime: {hours:.1f}h)"
        
        if status.error_message:
            details += f" - {status.error_message}"
        
        print(f"{emoji} {status.name}: {status.status}{details}")
    
    # Выводим сводку
    print("\n" + "=" * 60)
    summary = monitor.get_summary(statuses)
    print(summary)
    
    # Статистика
    healthy_count = sum(1 for s in statuses if s.status == 'healthy')
    total_count = len(statuses)
    
    print(f"\n📈 Статистика: {healthy_count}/{total_count} сервисов здоровы")
    
    if healthy_count == total_count:
        print("🎉 Все сервисы работают нормально!")
    elif healthy_count > 0:
        print("⚠️ Некоторые сервисы имеют проблемы")
    else:
        print("🚨 Все сервисы недоступны!")

if __name__ == '__main__':
    test_full_monitoring()
