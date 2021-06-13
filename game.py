import json, argparse, asyncio, requests, logging, sys, time, os
from asyncio import Lock, Queue
from aiohttp import ClientSession
from typing import Tuple, List

class wikiGame:
    url = "https://en.wikipedia.org/w/api.php"
    parameters = {
        "format":"json",
        "action":"query",
        "prop":"links",
        "pllimit":500,
        "plnamespace":0,
        "rawcontinue":"",
    }

    def __init__(self, start: str, end: str, path: str = 'logs'):
        self.start = start
        self.end = end
        self.parameters["titles"] = start
        self.visited = [start]

        self.setup_logging(path=path)

        self.tasks = []
        self.mutex = Lock()
        self.queue = Queue()

        self.final_list = list()

    def setup_logging(self, path: str):
        if not os.path.exists(path):
            os.mkdir(path)

        unix_time = time.time()
        unix_time = str(unix_time).split('.')[0]

        self.logger = logging.getLogger("WikipediaGame")
        self.logger.setLevel(level=logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        shandler = logging.StreamHandler(sys.stdout)
        fhandler = logging.FileHandler(filename=f"{path}/WikipediaGame_{unix_time}.log")
        shandler.setFormatter(formatter)
        fhandler.setFormatter(formatter)

        self.logger.addHandler(shandler)
        self.logger.addHandler(fhandler)


    def sync_get_links(self, parameters: dict) -> list:
        page = requests.get(self.url, params=parameters)
        content = json.loads(page.content.decode())
        page_id = list(content['query']['pages'].keys())[0]

        return [record['title'] for record in content['query']['pages'][page_id]['links']]

    async def get_links(self, num: int, parameters: dict) -> list:
        async with self.session.get(self.url, params=parameters) as page:
            try:
                text = await page.text()
                content = json.loads(text)
            except json.decoder.JSONDecodeError as e:
                self.logger.error(f"THREAD {num}. COULD NOT DECODE JSON. TEXT {text}")
                return []
            page_id = list(content['query']['pages'].keys())[0]

            try:
                return [record['title'] for record in content['query']['pages'][page_id]['links']]
            except KeyError as e:
                self.logger.error(f"THREAD {num}: PAGE: {parameters['titles']}. Content: {content}")
                return []

    async def find_end_link(self, num: int, parent: str, depth: int, params: dict) -> Tuple[list, bool]:
        prev_title = params["titles"]
        params["titles"] = parent
        child_link_titles = await self.get_links(num=num, parameters=params)

        result = False
        links = []
        if self.end in child_link_titles:
            self.logger.info(f"FOUND END {self.end}")
            await self.task_canceller(num)
            return [self.end], True
        elif depth == 10:
            return [], False
        for link in child_link_titles:
            async with self.mutex:
                not_visited = link not in self.visited
            if not_visited:
                self.visited.append(link)
                links, result = await self.find_end_link(num=num, parent=link, depth=depth+1, params=params)
                if result:
                    links.insert(0, link)
                    break

        if depth == 1 and result:
            async with self.mutex:
                await self.queue.put(links)
        return links, result

    async def task_canceller(self, num: int) -> list:
        # if task:
        #     task.cancel()
        #     # self.logger.info(f"THREAD {task.get_name()}. CANCELLED")
        #     return

        self.tasks.pop(num)
        self.final_list = await self.queue.get()
        for task in asyncio.Task.all_tasks():
            task.cancel()
        self.logger.info("finished cancelling routines")

    async def run(self):
        producers = list()
        self.session = ClientSession()
        params = self.parameters.copy()
        self.init_link_titles = await self.get_links(num=0,parameters=params)
        if not self.end in self.init_link_titles:
            for i, link in enumerate(self.init_link_titles):
                if link not in self.visited:
                    self.visited.append(link)

                    params = self.parameters.copy()
                    self.tasks.append(asyncio.create_task(self.find_end_link(num=i, parent=link, depth=1, params=params)))

            try:
                await asyncio.gather(*self.tasks)
            except asyncio.exceptions.CancelledError as e:
                self.logger.warning(f"TASK {task.get_name()} CANCELLED")
        else:
            self.final_list = [self.end]

        await self.session.close()
        output = ""
        self.final_list.insert(0,self.start)
        for link in self.final_list:
            output += f"{link} -> "
        print(output.strip(' ->'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("start", metavar="S", type=str, help="starting link", required=True)
    parser.add_argument("end", metavar="E", type=str, help="ending link to search", required=True)
    parser.add_argument("logs", metavar="L", type=str, help="path to log files")

    args = parser.parse_args()
    arguments = {"start": args.start, "end": args.end}
    if args.logs:
        arguments["path"] = args.logs

    wg = wikiGame(**arguments)
    asyncio.run(wg.run())