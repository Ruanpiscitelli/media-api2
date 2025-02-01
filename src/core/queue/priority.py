import asyncio

class PriorityQueue:
    def __init__(self):
        self.queues = {
            "realtime": asyncio.Queue(),
            "high": asyncio.Queue(),
            "normal": asyncio.Queue(),
            "batch": asyncio.Queue()
        }

    async def put(self, task: Task, priority: str):
        if priority not in self.queues:
            raise InvalidPriorityError()
            
        await self.queues[priority].put(task)

    async def get(self) -> Task:
        for queue in ["realtime", "high", "normal", "batch"]:
            if not self.queues[queue].empty():
                return await self.queues[queue].get()
                
        return await self.queues["batch"].get() 