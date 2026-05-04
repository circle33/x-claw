import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # r = httpx.request('GET','https://www.cnblogs.com/blueberry-mint/p/15250125.html')
        r = await client.request('GET','https://www.cnblogs.com/blueberry-mint/p/15250125.html')
        print(r.text)

if __name__ == "__main__":
    asyncio.run(main())
