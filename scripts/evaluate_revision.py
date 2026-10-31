import asyncio
from evaluate import case, questions, store
from biolens.schemas import TurnIn

async def main():
    store.init()
    for name, question in questions:
        await case(name + "_off_v2", TurnIn(prompt=question, external=False))
        await case(name + "_on_v2", TurnIn(prompt=question, external=True))
asyncio.run(main())
