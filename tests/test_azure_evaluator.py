import asyncio
import threading

import pytest
import pytest_asyncio

from azure_handling.azureevaluator import AzureEvaluator
from mock.mock_azure import MockAzure
from models import JudgeRequest


class TestAzureEvaluator:

    @pytest_asyncio.fixture(autouse=True)
    async def test_set_up(self):
        self.mock_azure = MockAzure(
                'abc',
                '123'
        )
        await self.mock_azure.create_vmss(
            'test_vmss'
        )
        self.eval = AzureEvaluator(self.mock_azure)
        print(threading.active_count())
        await self.eval.initialize()
        print(threading.active_count())
    
    @pytest.mark.asyncio
    async def test_submit(self):
        request = JudgeRequest(
                None,
                None,
                None,
                1256,
                None,
                None
            )
        print('sukkit')
        #Acquire condition lock (preventing deadlocks)
        with request.fulfilled:
            threading.Thread(target=asyncio.run, args=[self.eval.submit(request)]).start()
            print('lakitu')
            #Unacquire lock and wait until the judge_request has been fulfilled
            request.fulfilled.wait()
        print('wjat')
        assert request.result is not None

