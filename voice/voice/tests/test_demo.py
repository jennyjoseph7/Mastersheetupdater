import asyncio

queue = asyncio.Queue() 

async def p(x):

    for i in range(x):
        await queue.put({i:i+1})

async def c(x):
    
    for i in range(x):
        x = await queue.get()
        queue.task_done()

    return x

async def main():

    x = await asyncio.gather(p(3), c(3))

    print(x.result())


print(asyncio.run(main()))