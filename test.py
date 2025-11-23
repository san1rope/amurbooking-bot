import asyncio
import time
from multiprocessing import Process, Manager

from tg_bot.misc.models import QueueMessage


def wrapper(func, *args, **kwargs):
    return asyncio.run(func(*args, **kwargs))


async def proc1(shared_data):
    time.sleep(1)
    shared_data["test2"] = QueueMessage(msg_type="abc124", data="123")


async def proc2(shared_data):
    time.sleep(5)
    print(f"proc2: {shared_data}")
    shared_data["test3"] = QueueMessage(msg_type="abc1251", data="123")


async def main():
    with Manager() as manager:
        shared_data = manager.dict()
        shared_data["test1"] = QueueMessage(msg_type="abc", data="123")

        Process(target=wrapper, args=(proc1, shared_data,)).start()
        Process(target=wrapper, args=(proc2, shared_data,)).start()

        time.sleep(10)

        print(f"main: {shared_data}")


if __name__ == "__main__":
    asyncio.run(main())
