
import pytest_asyncio

from azure_handling.azureevaluator import AzureEvaluator
from mock.mock_azure import MockAzure


class TestAzureEvaluator:

    @pytest_asyncio.fixture(autouse=True)
    async def test_set_up(self):
        self.mock_azure = MockAzure(
        )
        await self.mock_azure.create_vmss(
            'test_vmss'
        )
        self.eval = AzureEvaluator(self.mock_azure)

        await self.eval.initialize()
    
    