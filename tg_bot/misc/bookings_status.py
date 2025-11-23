import asyncio
import traceback
from multiprocessing import Process

from config import Config
from tg_bot.db_models.quick_commands import DbBooking
from tg_bot.misc.browser_processing import BrowserProcessing
from tg_bot.misc.models import WorkTypes, QueueMessage
from tg_bot.misc.utils import BOOKING_PROCESSES, Utils as Ut


async def bookings_checker(shared_data):
    Config.logger.info("Чекер состояний запущен!")

    while True:
        await asyncio.sleep(0.5)

        try:
            db_bookings_0 = await DbBooking(status=0).select()
            for booking in db_bookings_0:
                booking_proc = BOOKING_PROCESSES.get(booking.account_id)
                if (booking_proc is not None) and booking_proc.is_alive():
                    shared_data[booking].append(QueueMessage(msg_type=Ut.STOP_PROCESS))
                    Config.logger.info(f"Послал запрос на завершение процесса обработки записи №{booking.id}!")

                if booking.account_id in BOOKING_PROCESSES:
                    BOOKING_PROCESSES.pop(booking.account_id)

                if booking.account_id in shared_data:
                    shared_data.pop(booking.account_id)

            db_bookings_1 = await DbBooking(status=1).select()
            for booking in db_bookings_1:
                booking_proc = BOOKING_PROCESSES.get(booking.account_id)
                if (booking_proc is None) or (not booking_proc.is_alive()):
                    new_proc = Process(
                        target=Ut.wrapper,
                        args=(BrowserProcessing(
                            work_type=WorkTypes.BOOKING_PROCESSING, account_id=booking.account_id,
                            shared_data=shared_data, shared_proxies=Config.INPUT_PROXIES
                        ).run_task,)
                    )
                    new_proc.start()
                    BOOKING_PROCESSES.update({booking.account_id: new_proc})
                    shared_data.update({booking.account_id: []})
                    Config.logger.info(f"Запустил новый процесс для записи №{booking.id}!")

        except Exception as ex:
            Config.logger.error(f"Ошибка в bookings_checker\nex: {traceback.format_exc()}")
            await asyncio.sleep(5)
