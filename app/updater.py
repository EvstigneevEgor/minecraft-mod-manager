"""
Модуль автообновления модов с планировщиком задач
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.mod_manager import ModManager
from app.models import UpdateLogEntry

logger = logging.getLogger(__name__)


class UpdateLogger:
    """Логгер обновлений модов"""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._logs: List[UpdateLogEntry] = []
    
    def add_log(self, mod_slug: str, old_version: Optional[str], 
                new_version: str, status: str, message: Optional[str] = None):
        """Добавить запись в лог"""
        entry = UpdateLogEntry(
            timestamp=datetime.now(),
            mod_slug=mod_slug,
            old_version=old_version,
            new_version=new_version,
            status=status,
            message=message
        )
        
        self._logs.append(entry)
        
        # Ограничиваем количество записей
        if len(self._logs) > self.max_entries:
            self._logs = self._logs[-self.max_entries:]
        
        logger.info(f"Лог обновления: {mod_slug} {old_version} -> {new_version} ({status})")
    
    def get_logs(self, limit: Optional[int] = None) -> List[UpdateLogEntry]:
        """Получить логи обновлений"""
        logs = sorted(self._logs, key=lambda x: x.timestamp, reverse=True)
        if limit:
            return logs[:limit]
        return logs
    
    def clear_logs(self):
        """Очистить логи"""
        self._logs.clear()
        logger.info("Логи обновлений очищены")


class AutoUpdater:
    """Автоматический обновлятор модов"""
    
    def __init__(self, settings: Settings, mod_manager: ModManager):
        self.settings = settings
        self.mod_manager = mod_manager
        self.scheduler = AsyncIOScheduler()
        self.update_logger = UpdateLogger()
        self._is_running = False
        self._last_check: Optional[datetime] = None
        self._update_in_progress = False
    
    async def start(self):
        """Запустить планировщик автообновлений"""
        if not self.settings.enable_auto_update:
            logger.info("Автообновления отключены в настройках")
            return
        
        if self._is_running:
            logger.warning("Планировщик уже запущен")
            return
        
        try:
            # Добавляем задачу автообновления
            self.scheduler.add_job(
                self._update_all_mods,
                trigger=IntervalTrigger(hours=self.settings.update_interval),
                id='auto_update_mods',
                name='Автообновление модов',
                max_instances=1,  # Только одна задача одновременно
                coalesce=True,    # Объединять пропущенные запуски
                misfire_grace_time=300  # 5 минут на опоздание
            )
            
            # Добавляем задачу очистки логов (раз в неделю)
            self.scheduler.add_job(
                self._cleanup_logs,
                trigger=CronTrigger(day_of_week=0, hour=2, minute=0),  # Воскресенье в 2:00
                id='cleanup_logs',
                name='Очистка старых логов'
            )
            
            self.scheduler.start()
            self._is_running = True
            
            logger.info(f"Планировщик автообновлений запущен (интервал: {self.settings.update_interval} ч.)")
            
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")
            raise
    
    async def stop(self):
        """Остановить планировщик"""
        if not self._is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Планировщик автообновлений остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки планировщика: {e}")
    
    async def _update_all_mods(self):
        """Обновить все моды с включенным автообновлением"""
        if self._update_in_progress:
            logger.warning("Обновление уже выполняется, пропускаем")
            return
        
        self._update_in_progress = True
        self._last_check = datetime.now()
        
        try:
            logger.info("Начинаем проверку обновлений модов")
            
            # Получаем список модов с включенным автообновлением
            installed_mods = self.mod_manager.get_installed_mods()
            auto_update_mods = [mod for mod in installed_mods if mod.auto_update]
            
            if not auto_update_mods:
                logger.info("Нет модов с включенным автообновлением")
                return
            
            logger.info(f"Проверяем обновления для {len(auto_update_mods)} модов")
            
            updated_count = 0
            failed_count = 0
            
            # Обновляем моды по одному
            for mod in auto_update_mods:
                try:
                    old_version = mod.version
                    success = await self.mod_manager.update_mod(mod.slug)
                    
                    if success:
                        # Получаем новую версию
                        updated_mod = self.mod_manager.state_manager.get_mod(mod.slug)
                        new_version = updated_mod.version if updated_mod else "unknown"
                        
                        if new_version != old_version:
                            self.update_logger.add_log(
                                mod.slug, old_version, new_version, "success",
                                "Мод успешно обновлен"
                            )
                            updated_count += 1
                            logger.info(f"Мод обновлен: {mod.slug} {old_version} -> {new_version}")
                        else:
                            self.update_logger.add_log(
                                mod.slug, old_version, old_version, "skipped",
                                "Мод уже актуален"
                            )
                    else:
                        self.update_logger.add_log(
                            mod.slug, old_version, old_version, "failed",
                            "Не удалось обновить мод"
                        )
                        failed_count += 1
                
                except Exception as e:
                    logger.error(f"Ошибка обновления мода {mod.slug}: {e}")
                    self.update_logger.add_log(
                        mod.slug, mod.version, mod.version, "failed",
                        f"Ошибка: {str(e)}"
                    )
                    failed_count += 1
                
                # Небольшая пауза между обновлениями
                await asyncio.sleep(1)
            
            # Обновляем время последней проверки в состоянии
            self.mod_manager.state_manager._state['metadata']['last_update_check'] = self._last_check.isoformat()
            self.mod_manager.state_manager._save_state()
            
            logger.info(f"Проверка обновлений завершена: обновлено {updated_count}, ошибок {failed_count}")
            
        except Exception as e:
            logger.error(f"Ошибка при автообновлении: {e}")
        finally:
            self._update_in_progress = False
    
    async def _cleanup_logs(self):
        """Очистка старых логов"""
        try:
            # Оставляем только последние 500 записей
            logs = self.update_logger.get_logs()
            if len(logs) > 500:
                self.update_logger._logs = logs[:500]
                logger.info(f"Очищены старые логи, оставлено {len(self.update_logger._logs)} записей")
        except Exception as e:
            logger.error(f"Ошибка очистки логов: {e}")
    
    async def run_update_now(self) -> Dict:
        """Запустить обновление вручную"""
        if self._update_in_progress:
            return {
                "status": "error",
                "message": "Обновление уже выполняется"
            }
        
        try:
            # Запускаем обновление в фоне
            asyncio.create_task(self._update_all_mods())
            
            return {
                "status": "success",
                "message": "Проверка обновлений запущена"
            }
        except Exception as e:
            logger.error(f"Ошибка запуска обновления: {e}")
            return {
                "status": "error",
                "message": f"Ошибка запуска: {e}"
            }
    
    def get_status(self) -> Dict:
        """Получить статус автообновления"""
        next_run = None
        if self._is_running and self.scheduler.get_job('auto_update_mods'):
            job = self.scheduler.get_job('auto_update_mods')
            next_run = job.next_run_time
        
        return {
            "enabled": self.settings.enable_auto_update,
            "running": self._is_running,
            "interval_hours": self.settings.update_interval,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "next_check": next_run.isoformat() if next_run else None,
            "update_in_progress": self._update_in_progress
        }
    
    async def enable_auto_update(self) -> Dict:
        """Включить автообновление"""
        try:
            if not self._is_running:
                await self.start()
            
            return {
                "status": "success",
                "message": "Автообновление включено"
            }
        except Exception as e:
            logger.error(f"Ошибка включения автообновления: {e}")
            return {
                "status": "error",
                "message": f"Ошибка: {e}"
            }
    
    async def disable_auto_update(self) -> Dict:
        """Отключить автообновление"""
        try:
            if self._is_running:
                await self.stop()
            
            return {
                "status": "success",
                "message": "Автообновление отключено"
            }
        except Exception as e:
            logger.error(f"Ошибка отключения автообновления: {e}")
            return {
                "status": "error",
                "message": f"Ошибка: {e}"
            }
    
    def get_update_logs(self, limit: Optional[int] = 50) -> List[UpdateLogEntry]:
        """Получить логи обновлений"""
        return self.update_logger.get_logs(limit)
    
    def clear_update_logs(self):
        """Очистить логи обновлений"""
        self.update_logger.clear_logs()