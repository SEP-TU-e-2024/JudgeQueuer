from unittest.mock import patch

import pytest
import pytest_asyncio

from azure_handling.judgevmss import JudgeVMSS
from mock.mock_azure import MockAzure
from models import JudgeRequest, JudgeResult, MachineType, Submission, SubmissionType


class TestVMSS:

    @pytest_asyncio.fixture(autouse=True)
    async def set_up(
        self,
        patch_is_machine_name_connected,
        patch_vms_alive,
        patch_submit_to_vm,
        ):
        azure = MockAzure()
        remote_vmss = await azure.create_vmss(
            'test_judge_vmss'
        )
        vmss = JudgeVMSS(
            MachineType(
                'test_machine_type_name',
                'test_machine_type_tier'
            ),
            'test_judge_vmss',
            remote_vmss,
            azure,
        )
        self.azure = azure
        self.remote_vmss = remote_vmss
        self.vmss = vmss

        yield



    @pytest_asyncio.fixture
    async def patch_vms_alive(self):
        with patch('azure_handling.judgevmss.is_machine_name_connected') as mock_start_command:
            mock_start_command.return_value = True
            yield mock_start_command

    @pytest_asyncio.fixture
    async def patch_is_machine_name_connected(self):
        with patch('azure_handling.judgevmss.JudgeVM.alive') as mock_alive:
            mock_alive.return_value = True
            yield mock_alive

    async def mock_submit_to_vm(self, judge_request):
        #Acquire the fulfilled condition lock
        with judge_request.fulfilled:
            judge_request.result = JudgeResult.success('test_result')
            #Notify those waiting for the fulfilled condition
            judge_request.fulfilled.notifyAll()

        #WARNING: This method does not free up CPU and Memory, don't call it twice in a row


    @pytest_asyncio.fixture
    async def patch_submit_to_vm(self):
        with patch('azure_handling.judgevmss.JudgeVM.submit_to_vm', new=self.mock_submit_to_vm) as mock_submit_to_vm:
            yield mock_submit_to_vm

    @pytest.mark.asyncio
    async def test_update(
        self
        ):
        for i in range(10):
            with self.vmss.judge_dict_lock:
                assert len(self.vmss.judgevm_dict.keys()) == i
            await self.vmss.add_capacity()

    @pytest.mark.asyncio
    async def test_submit_new_vm(
        self
        ):
        submission = Submission(
            SubmissionType(
                1
            ),
            "test/source_url",
            "test/validator_url"
        )

        request = JudgeRequest(
            submission,
            MachineType(
                'test machine type',
                'test tier'
            ),
            1,
            100,
            None,
            None
        )

        await self.vmss.submit(request)


        with request.fulfilled:
            request.fulfilled.wait()

        assert request.result.result == "test_result"

    @pytest.mark.asyncio
    async def test_removal(self, monkeypatch):
        await self.vmss.add_capacity()
        with self.vmss.judge_dict_lock:
            vm = list(self.vmss.judgevm_dict.values())[0]
        monkeypatch.setenv('MAX_VM_IDLE_TIME', '1')
        await self.vmss.start_vm_removal_time(vm)
        
    @pytest.mark.asyncio
    async def test_check_capacity(self):
        await self.vmss.add_capacity()
        with self.vmss.judge_dict_lock:
            vm = list(self.vmss.judgevm_dict.values())[0]
        assert await vm.check_capacity(100, 2000) is False
        assert await self.vmss.is_empty() is False
        try:
            await self.vmss.close()
        except Exception:
            return