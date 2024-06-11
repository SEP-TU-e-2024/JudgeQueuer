import asyncio
import threading

from .base import Azure


class AsyncAzure(Azure):
    """
    An asynchronous wrapper for the Azure class.

    Each function in this class forwards the call to the corresponding function in the Azure class,
    which is executed on its own thread.

    Each function in this class, including initializers, has the exact same signature as its original.

    Note that some functions are excluded, as they do not call Azure functions directly,
    instead relying on other functions in the Azure wrapper.
    """
    
    thread: threading.Thread
    """
    The Azure thread on which each Azure call is performed
    """
    
    loop: asyncio.AbstractEventLoop
    """
    The event loop on which every Azure action is executed.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create an event loop for the Azure thread
        self.loop = asyncio.new_event_loop()
        
        # Entrypoint for the thread
        def run_event_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        
        # Create & start the thread
        self.thread = threading.Thread(target=run_event_loop, args=(self.loop,), daemon=True)
        self.thread.start()

    def __run(self, coro):
        """
        Utility method to run the given coroutine on the Azure thread.
        """
        return asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, self.loop))
    
    def list_skus(self, *args, **kwargs):
        return self.__run(super().list_skus(*args, **kwargs))

    def list_vms(self, *args, **kwargs):
        return self.__run(super().list_vms(*args, **kwargs))

    def delete_vmss(self, *args, **kwargs):
        return self.__run(super().delete_vmss(*args, **kwargs))

    def get_vmss(self, *args, **kwargs):
        return self.__run(super().get_vmss(*args, **kwargs))

    def list_vmss(self, *args, **kwargs):
        return self.__run(super().list_vmss(*args, **kwargs))
    
    def get_vm(self, *args, **kwargs):
        return self.__run(super().get_vm(*args, **kwargs))

    def create_vmss(self, *args, **kwargs):
        return self.__run(super().create_vmss(*args, **kwargs))

    def set_capacity(self, *args, **kwargs):
        return self.__run(super().set_capacity(*args, **kwargs))

    def delete_vm(self, *args, **kwargs):
        return self.__run(super().delete_vm(*args, **kwargs))
    
    async def close(self, *args, **kwargs):
        await self.__run(super().close(*args, **kwargs))
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

