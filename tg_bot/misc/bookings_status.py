import asyncio
from multiprocessing import Process, Queue

from config import Config
from tg_bot.db_models.quick_commands import DbBooking
from tg_bot.misc.browser_processing import BrowserProcessing
from tg_bot.misc.models import WorkTypes, QueueMessage
from tg_bot.misc.utils import BOOKING_PROCESSES, Utils as Ut


async def bookings_checker():
    Config.logger.info("Чекер состояний запущен!")

    while True:
        await asyncio.sleep(0.5)

        try:
            db_bookings_0 = await DbBooking(status=0).select()
            for booking in db_bookings_0:
                booking_proc_data = BOOKING_PROCESSES.get(booking.id)
                if booking_proc_data:
                    booking_process = booking_proc_data.get(Ut.PROCESS_STR)
                    if (booking_process is not None) and booking_process.is_alive():
                        booking_proc_data[Ut.QUEUE_STR].put(QueueMessage(msg_type=Ut.STOP_PROCESS))
                        Config.logger.info(f"Послал запрос на завершение процесса обработки записи №{booking.id}!")

                    BOOKING_PROCESSES.pop(booking.id)

            db_bookings_1 = await DbBooking(status=1).select()
            for booking in db_bookings_1:
                booking_proc_data = BOOKING_PROCESSES.get(booking.id)
                if (booking_proc_data is None) or (not booking_proc_data[Ut.PROCESS_STR].is_alive()):
                    new_queue = Queue()
                    new_proc = Process(
                        target=Ut.wrapper,
                        args=(BrowserProcessing(
                            work_type=WorkTypes.BOOKING_PROCESSING, account_id=booking.account_id, process_queue=new_queue
                        ).run_task,)
                    )
                    new_proc.start()
                    BOOKING_PROCESSES.update({booking.id: {Ut.PROCESS_STR: new_proc, Ut.QUEUE_STR: new_queue}})
                    Config.logger.info(f"Запустил новый процесс для записи №{booking.id}!")

        except Exception as ex:
            Config.logger.error(f"Ошибка в bookings_checker\nex: {ex}")
            await asyncio.sleep(5)
