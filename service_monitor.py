import os
import time
import logging
import requests
import psutil
import docker
import schedule
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceStatus:
    """Класс для хранения статуса сервиса"""
    name: str
    status: str  # 'healthy', 'unhealthy', 'unknown'
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None
    uptime: Optional[float] = None

class ServiceMonitor:
    """Класс для мониторинга различных типов сервисов"""
    
    def __init__(self):
        self.docker_client = None
        self._init_docker_client()
        self.services = self._parse_services_config()
    
    def _parse_services_config(self) -> List[Dict]:
        """Парсинг конфигурации сервисов из переменной окружения"""
        services_config = os.getenv('SERVICES_TO_MONITOR', '')
        services = []
        
        try:
            # Поддерживаемые форматы:
            # 1. "service1:http://localhost:8080,service2:docker:nginx" (полный формат)
            # 2. "http://localhost:8080,http://localhost:3000,postgresql,nginx" (упрощенный формат)
            if services_config:
                for service_config in services_config.split(','):
                    service_config = service_config.strip()
                    if not service_config:
                        continue
                    
                    # Проверяем, есть ли двоеточие в конфигурации
                    if ':' in service_config:
                        # Сначала проверяем, не является ли это URL
                        if service_config.startswith('http://') or service_config.startswith('https://'):
                            service_type = 'http'
                            logger.info(f"Добавляем HTTP сервис: {service_config}")
                            services.append({
                                'name': service_config,  # Используем URL как имя
                                'type': service_type,
                                'config': service_config
                            })
                        else:
                            # Это формат name:config
                            parts = service_config.split(':', 1)
                            if len(parts) == 2:
                                name, config = parts
                                service_type = self._detect_service_type(config)
                                
                                services.append({
                                    'name': name.strip(),
                                    'type': service_type,
                                    'config': config.strip()
                                })
                            else:
                                # Возможно это URL без имени
                                service_type = self._detect_service_type(service_config)
                                services.append({
                                    'name': service_config,  # Используем конфигурацию как имя
                                    'type': service_type,
                                    'config': service_config
                                })
                    else:
                        # Простое имя сервиса без конфигурации
                        # Пытаемся определить тип автоматически
                        service_type = self._detect_service_type(service_config)
                        services.append({
                            'name': service_config,
                            'type': service_type,
                            'config': service_config
                        })
            
            # Добавляем все запущенные Docker контейнеры
            docker_services = self._get_running_docker_containers()
            services.extend(docker_services)
                
        except Exception as e:
            logger.error(f"Ошибка парсинга SERVICES_TO_MONITOR: {e}")
        
        return services
    
    def _detect_service_type(self, config: str) -> str:
        """Определение типа сервиса по конфигурации"""
        if config.startswith('http://') or config.startswith('https://'):
            return 'http'
        elif config.startswith('docker:'):
            return 'docker'
        elif config.startswith('process:'):
            return 'process'
        elif config.startswith('systemd:'):
            return 'systemd'
        else:
            # Попытка определить тип по имени сервиса
            config_lower = config.lower()
            
            # Известные systemd сервисы
            systemd_services = ['redis', 'redis-server', 'postgresql', 'postgres', 'mysql', 'nginx', 'apache2', 'ssh', 'cron']
            if config_lower in systemd_services:
                return 'systemd'
            
            # Известные Docker контейнеры (только те, которые обычно в Docker)
            docker_services = ['jenkins', 'minio', 'grafana', 'prometheus']
            if config_lower in docker_services:
                return 'docker'
            
            # Известные системные процессы
            system_services = ['wg-quick', 'systemd', 'cron']
            if any(service in config_lower for service in system_services):
                return 'process'
            
            # По умолчанию считаем systemd сервисом
            return 'systemd'
    
    def _init_docker_client(self):
        """Инициализация Docker клиента"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker клиент инициализирован")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Docker клиент: {e}")
            self.docker_client = None
    
    def _get_running_docker_containers(self) -> List[Dict]:
        """Получение всех запущенных Docker контейнеров"""
        containers = []
        
        if not self.docker_client:
            return containers
        
        try:
            running_containers = self.docker_client.containers.list()
            
            for container in running_containers:
                container_name = container.name
                containers.append({
                    'name': container_name,
                    'type': 'docker',
                    'config': container_name,
                    'auto_discovered': True  # Флаг для автоматически обнаруженных контейнеров
                })
            
            if containers:
                logger.info(f"Автоматически обнаружено {len(containers)} Docker контейнеров")
                
        except Exception as e:
            logger.error(f"Ошибка при получении Docker контейнеров: {e}")
        
        return containers
    
    def check_http_service(self, url: str, timeout: int = 10) -> ServiceStatus:
        """Проверка HTTP сервиса
        
        Логика проверки:
        - 2xx, 3xx, 4xx (включая 404) - сервер работает нормально
        - 5xx - ошибка сервера, сервис не работает
        """
        # Очищаем URL от лишних символов
        url = url.strip()
        # Убираем лишние символы в конце URL
        while url.endswith('*') or url.endswith('/'):
            url = url.rstrip('*/')
        
        start_time = time.time()
        try:
            logger.info(f"Проверяем HTTP сервис: {url}")
            response = requests.get(url, timeout=timeout, verify=False)
            response_time = time.time() - start_time
            
            # 404 означает, что сервер работает, но страница не найдена - это нормально
            # 5xx ошибки - это проблемы сервера
            if response.status_code < 500:
                return ServiceStatus(
                    name=url,
                    status='healthy',
                    response_time=response_time,
                    last_check=datetime.now()
                )
            else:
                return ServiceStatus(
                    name=url,
                    status='unhealthy',
                    response_time=response_time,
                    error_message=f"HTTP {response.status_code}",
                    last_check=datetime.now()
                )
                
        except requests.exceptions.Timeout:
            return ServiceStatus(
                name=url,
                status='unhealthy',
                error_message="Timeout",
                last_check=datetime.now()
            )
        except requests.exceptions.ConnectionError:
            return ServiceStatus(
                name=url,
                status='unhealthy',
                error_message="Connection Error",
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceStatus(
                name=url,
                status='unhealthy',
                error_message=str(e),
                last_check=datetime.now()
            )
    
    def check_docker_service(self, container_name: str) -> ServiceStatus:
        """Проверка Docker контейнера"""
        if not self.docker_client:
            return ServiceStatus(
                name=container_name,
                status='unknown',
                error_message="Docker клиент недоступен",
                last_check=datetime.now()
            )
        
        try:
            # Убираем префикс docker: если он есть
            if container_name.startswith('docker:'):
                container_name = container_name.replace('docker:', '')
            
            # Сначала пытаемся найти контейнер по точному имени
            try:
                container = self.docker_client.containers.get(container_name)
            except docker.errors.NotFound:
                # Если не найден, ищем по частичному совпадению
                containers = self.docker_client.containers.list(all=True)
                matching_containers = []
                
                for container in containers:
                    # Проверяем различные варианты совпадения
                    if (container_name.lower() in container.name.lower() or
                        container_name.lower() in container.attrs.get('Config', {}).get('Image', '').lower() or
                        any(tag.lower().startswith(container_name.lower()) for tag in container.image.tags)):
                        matching_containers.append(container)
                
                if not matching_containers:
                    return ServiceStatus(
                        name=container_name,
                        status='unhealthy',
                        error_message="Container not found",
                        last_check=datetime.now()
                    )
                
                # Берем первый найденный контейнер
                container = matching_containers[0]
            
            container_info = container.attrs
            
            status = container_info['State']['Status']
            health_status = container_info['State'].get('Health', {}).get('Status', 'unknown')
            
            if status == 'running':
                # Контейнер считается здоровым если он запущен
                # Health check может быть 'healthy', 'none' или 'unknown' - все это нормально для запущенного контейнера
                return ServiceStatus(
                    name=container_name,
                    status='healthy',
                    last_check=datetime.now()
                )
            else:
                return ServiceStatus(
                    name=container_name,
                    status='unhealthy',
                    error_message=f"Status: {status}, Health: {health_status}",
                    last_check=datetime.now()
                )
                
        except docker.errors.NotFound:
            return ServiceStatus(
                name=container_name,
                status='unhealthy',
                error_message="Container not found",
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceStatus(
                name=container_name,
                status='unhealthy',
                error_message=str(e),
                last_check=datetime.now()
            )
    
    def check_systemd_service(self, service_name: str) -> ServiceStatus:
        """Проверка systemd сервиса"""
        try:
            # Убираем префикс systemd: если он есть
            if service_name.startswith('systemd:'):
                service_name = service_name.replace('systemd:', '')
            
            # Добавляем .service если его нет
            if not service_name.endswith('.service'):
                service_name = f"{service_name}.service"
            
            import subprocess
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip() == 'active':
                # Получаем дополнительную информацию о сервисе
                try:
                    status_result = subprocess.run(
                        ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    uptime = None
                    if status_result.returncode == 0:
                        # Парсим время запуска
                        for line in status_result.stdout.split('\n'):
                            if line.startswith('ActiveEnterTimestamp='):
                                timestamp_str = line.split('=', 1)[1]
                                if timestamp_str:
                                    try:
                                        # Парсим timestamp в формате systemd
                                        if timestamp_str.startswith('Mon '):
                                            # Формат: Mon 2025-08-28 18:48:36 UTC
                                            dt = datetime.strptime(timestamp_str, '%a %Y-%m-%d %H:%M:%S %Z')
                                        else:
                                            # Другие форматы timestamp
                                            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                        
                                        uptime = time.time() - dt.timestamp()
                                    except:
                                        pass
                                break
                    
                    return ServiceStatus(
                        name=service_name.replace('.service', ''),
                        status='healthy',
                        uptime=uptime,
                        last_check=datetime.now()
                    )
                    
                except Exception as e:
                    return ServiceStatus(
                        name=service_name.replace('.service', ''),
                        status='healthy',
                        last_check=datetime.now()
                    )
            else:
                return ServiceStatus(
                    name=service_name.replace('.service', ''),
                    status='unhealthy',
                    error_message=f"Service not active: {result.stdout.strip()}",
                    last_check=datetime.now()
                )
                
        except subprocess.TimeoutExpired:
            return ServiceStatus(
                name=service_name.replace('.service', ''),
                status='unhealthy',
                error_message="Timeout checking service",
                last_check=datetime.now()
            )
        except Exception as e:
            return ServiceStatus(
                name=service_name.replace('.service', ''),
                status='unhealthy',
                error_message=str(e),
                last_check=datetime.now()
            )
    
    def check_process_service(self, process_name: str) -> ServiceStatus:
        """Проверка системного процесса"""
        try:
            # Убираем префикс process: если он есть
            if process_name.startswith('process:'):
                process_name = process_name.replace('process:', '')
            
            found_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    proc_name = proc.info['name'].lower()
                    cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                    
                    # Проверяем различные варианты совпадения
                    if (process_name.lower() in proc_name or 
                        process_name.lower() in cmdline or
                        proc_name in process_name.lower()):
                        found_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if found_processes:
                # Берем самый старый процесс для расчета uptime
                oldest_proc = min(found_processes, key=lambda p: p.info['create_time'])
                uptime = time.time() - oldest_proc.info['create_time']
                
                return ServiceStatus(
                    name=process_name,
                    status='healthy',
                    uptime=uptime,
                    last_check=datetime.now()
                )
            else:
                return ServiceStatus(
                    name=process_name,
                    status='unhealthy',
                    error_message="Process not found",
                    last_check=datetime.now()
                )
                
        except Exception as e:
            return ServiceStatus(
                name=process_name,
                status='unhealthy',
                error_message=str(e),
                last_check=datetime.now()
            )
    
    def check_service(self, service_config: Dict) -> ServiceStatus:
        """Проверка сервиса по конфигурации"""
        service_type = service_config['type']
        config = service_config['config']
        name = service_config['name']
        
        if service_type == 'http':
            return self.check_http_service(config)
        elif service_type == 'docker':
            container_name = config.replace('docker:', '')
            return self.check_docker_service(container_name)
        elif service_type == 'systemd':
            service_name = config.replace('systemd:', '')
            return self.check_systemd_service(service_name)
        elif service_type == 'process':
            process_name = config.replace('process:', '')
            return self.check_process_service(process_name)
        else:
            return ServiceStatus(
                name=name,
                status='unknown',
                error_message=f"Unknown service type: {service_type}",
                last_check=datetime.now()
            )
    
    def check_all_services(self) -> List[ServiceStatus]:
        """Проверка всех сервисов"""
        results = []
        for service_config in self.services:
            try:
                status = self.check_service(service_config)
                results.append(status)
                logger.info(f"Service {status.name}: {status.status}")
            except Exception as e:
                logger.error(f"Ошибка проверки сервиса {service_config['name']}: {e}")
                results.append(ServiceStatus(
                    name=service_config['name'],
                    status='unknown',
                    error_message=str(e),
                    last_check=datetime.now()
                ))
        
        return results
    
    def get_summary(self, statuses: List[ServiceStatus]) -> str:
        """Получение сводки по статусам сервисов"""
        healthy_count = sum(1 for s in statuses if s.status == 'healthy')
        total_count = len(statuses)
        
        summary = f"📊 **Мониторинг сервисов** ({healthy_count}/{total_count} здоровы)\n\n"
        
        for status in statuses:
            if status.status == 'healthy':
                emoji = "✅"
                details = ""
                if status.response_time:
                    details = f" ({status.response_time:.2f}s)"
                elif status.uptime:
                    hours = status.uptime / 3600
                    details = f" (uptime: {hours:.1f}h)"
            elif status.status == 'unhealthy':
                emoji = "❌"
                details = f" - {status.error_message}" if status.error_message else ""
            else:
                emoji = "❓"
                details = f" - {status.error_message}" if status.error_message else ""
            
            summary += f"{emoji} **{status.name}**: {status.status}{details}\n"
        
        return summary
    
    def start_monitoring(self, callback_func=None, interval_minutes: int = 5):
        """Запуск периодического мониторинга"""
        def monitoring_job():
            statuses = self.check_all_services()
            if callback_func:
                callback_func(statuses)
        
        # Запускаем сразу
        monitoring_job()
        
        # Планируем периодические проверки
        schedule.every(interval_minutes).minutes.do(monitoring_job)
        
        logger.info(f"Мониторинг запущен с интервалом {interval_minutes} минут")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту

# Пример использования
if __name__ == '__main__':
    monitor = ServiceMonitor()
    
    def print_status(statuses):
        print("\n" + "="*50)
        print(monitor.get_summary(statuses))
        print("="*50)
    
    monitor.start_monitoring(callback_func=print_status, interval_minutes=2)
