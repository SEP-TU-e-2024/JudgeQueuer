from unittest.mock import patch

import pytest
import pytest_asyncio

from azure_handling.judgevm import JudgeVM
from mock.mock_azure import MockAzure
from mock.mock_vm import MockVM
from mock.protocol.commands.mock_check_command import MockCheckCommand
from mock.protocol.commands.mock_start_command import MockStartCommand
from mock.protocol.mock_judge_protocol import MockJudgeProtocol
from models import JudgeRequest, MachineType, Submission, SubmissionType


class TestVM:
    def create_mock_start_command(self, success):
        command = MockStartCommand(success)
        return command

    @pytest_asyncio.fixture
    async def patch_start_command_success(self):
        with patch('azure_handling.judgevm.StartCommand', new=MockStartCommand) as mock_start_command:
            mock_start_command.success = True
            yield mock_start_command

    @pytest_asyncio.fixture
    async def patch_start_command_fail(self):
        with patch('azure_handling.judgevm.StartCommand', new=MockStartCommand) as mock_start_command:
            mock_start_command.success = False
            yield mock_start_command

    @pytest_asyncio.fixture
    async def patch_check_command_fail(self):
        with patch('azure_handling.judgevm.CheckCommand', new=MockCheckCommand) as mock_start_command:
            mock_start_command.success = False
            yield mock_start_command
    
    @pytest_asyncio.fixture
    async def patch_check_command_success(self):
        with patch('azure_handling.judgevm.CheckCommand', new=MockCheckCommand) as mock_start_command:
            mock_start_command.success = True
            yield mock_start_command
    
    @pytest_asyncio.fixture
    async def patch_protocol(self):
        with patch('azure_handling.judgevm.get_protocol_from_machine_name') as mock_get_protocol:
            mock_get_protocol.return_value = MockJudgeProtocol()
            yield mock_get_protocol

    @pytest_asyncio.fixture(autouse=True)
    async def set_up(self, patch_protocol):
        self.azure = MockAzure()
        self.remote_vm = MockVM()
        #Set up a basic vm with 16 CPUs and 1024 MB memory
        self.judge_vm = JudgeVM(
            self.remote_vm,
            "badoof",
            self.azure,
            16,
            1024,
            False
        )


    @pytest_asyncio.fixture
    async def setup_submission(self):
        self.submission = Submission(
            SubmissionType(
                1
            ),
            "test/source_url",
            "test/validator_url"
        )

        self.request = JudgeRequest(
            self.submission,
            MachineType(
                'test machine type',
                'test tier'
            ),
            16,
            1024,
            None,
            None
        )

    @pytest.mark.asyncio
    async def test_submission_successful(self, patch_start_command_success, setup_submission):
        await self.judge_vm.submit(self.request)
        
        with self.request.fulfilled:
            self.request.fulfilled.wait()

        assert self.request.result.result == "test result"

    @pytest.mark.asyncio
    async def test_submission_fail(self, patch_start_command_fail, setup_submission):
        await self.judge_vm.submit(self.request)
        
        with self.request.fulfilled:
            self.request.fulfilled.wait()

        assert self.request.result.cause == "test error"

    @pytest.mark.asyncio
    async def test_wake_dormant(self):
        self.azure = MockAzure()
        self.remote_vm = MockVM()
        #Set up a basic vm with 16 CPUs and 1024 MB memory
        self.judge_vm = JudgeVM(
            self.remote_vm,
            "badoof",
            self.azure,
            16,
            1024,
            True #Start out as dormant
        )

        with self.judge_vm.dormant_condition:
            self.judge_vm.dormant_condition.notify_all()

    @pytest.mark.asyncio
    async def test_check_idle_queue(self, setup_submission):
        #make dormant vm (so it does not consume request)
        dormant_judge_vm = JudgeVM(
            self.remote_vm,
            "badoof",
            self.azure,
            16,
            1024,
            True
        )

        assert dormant_judge_vm.check_idle_queue() is True

        #add a requests until full
        for i in range(dormant_judge_vm.max_idle):
            await dormant_judge_vm.submit(self.submission)

        assert dormant_judge_vm.check_idle_queue() is False

    @pytest.mark.asyncio
    async def test_check_capacity(self, setup_submission):
        #make dormant vm (so it does not consume request)
        judge_vm = JudgeVM(
            self.remote_vm,
            "badoof",
            self.azure,
            1,
            1024,
            True
        )

        #Create request that consumes all resources
        request = JudgeRequest(
            self.submission,
            MachineType(
                'test machine type',
                'test tier'
            ),
            1,
            1024,
            None,
            None
        )

        #Check for more capacity than it has
        assert await judge_vm.check_capacity(3, 1024) is False
        assert await judge_vm.check_capacity(1, 1025) is False
        assert await judge_vm.check_capacity(3, 1025) is False
        assert await judge_vm.check_capacity(1, 1024) is True
        
    @pytest.mark.asyncio
    async def test_is_busy(self, setup_submission):
        judge_vm = JudgeVM(
            self.remote_vm,
            "badoof",
            self.azure,
            1,
            1024,
            True
        )

        assert judge_vm.is_busy() is False

        await judge_vm.submit(self.request)

        assert judge_vm.is_busy() is True

    @pytest.mark.asyncio
    async def test_alive_success(self, set_up, patch_protocol, patch_check_command_success):
        assert await self.judge_vm.alive() is True

    @pytest.mark.asyncio
    async def test_alive_fail(self, set_up, patch_protocol, patch_check_command_fail):
        assert await self.judge_vm.alive() is False