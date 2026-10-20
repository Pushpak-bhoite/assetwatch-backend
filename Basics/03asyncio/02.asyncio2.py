import asyncio
from datetime import datetime

async def task1():
    print("T-1========start=============")
    await asyncio.sleep(3)
    print("T-1-End")

async def task2():
    print("T-2=========start============")
    await asyncio.sleep(3)
    print("T-2-End")

async def task3():
    print("T-3=======start===========")
    await asyncio.sleep(3)
    print("T-3-End")
    
async def task4():
    print("T-444444 start 44444444")
    await asyncio.sleep(3)
    print("T-End")

async def main():
  
    print("3")
    await asyncio.sleep(2) #when main() reaches here, it gives control to event loop
    print("****sleep complete*****")
    await asyncio.create_task(task1())   
    
    t1 = asyncio.create_task(task2())   
    t2 = asyncio.create_task(task2())   
    asyncio.create_task(task3())   # this createTask doesnt have await but still it completes,becoz there is await with gather below which keeps main alive for 3sec & task3 happens to take same time (3sec) as task1 ans task2
    
    r1,r2 = await asyncio.gather(t1, t2) 
    # or u can take res in single var and then do res[1], res[2]
    print(r1, r2)
    asyncio.create_task(task4())   #for this t-4End wont be printed since we doesn't have await
    
asyncio.run(main())


                #     asyncio.run(main()) #basically event loop gets creates when we use asyncio.run, with normal func it doesn't gets created  
                #             │
                #             ▼
                #  ┌─────────────────────┐
                #  │ Create event loop   │
                #  └──────────┬──────────┘
                #             │
                #             ▼
                #     Start event loop
                #             │
                #             ▼
                #   Run coroutine: main()
                #             │
                #             ▼
                #  ┌─────────────────────┐
                #  │      main()         │
                #  └──────────┬──────────┘
                #             │
                #     executes normally
                #             │
                #             ▼
                #    create_task(...)
                #             │
                #     Task gets scheduled
                #             │
                #             ▼
                #        await ...
                #             │
                #     main() PAUSES
                #             │
                #             ▼
                #  ┌─────────────────────┐
                #  │    EVENT LOOP       │
                #  │                     │
                #  │ Run scheduled tasks │
                #  │ Check timers        │
                #  │ Handle I/O          │
                #  │ Resume coroutines   │
                #  └─────────────────────┘