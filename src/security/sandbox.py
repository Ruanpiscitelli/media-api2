class GPUSandbox:
    async def isolate_process(self, pid: int, gpu_id: int):
        """Isola processo na GPU usando cgroups"""
        cmd = (
            f"cgcreate -g devices:/gpu{gpu_id}-isolated && "
            f"cgclassify -g devices:/gpu{gpu_id}-isolated {pid} && "
            f"echo 'c 195:{gpu_id} rwm' > /sys/fs/cgroup/devices/gpu{gpu_id}-isolated/devices.deny"
        )
        await run_shell(cmd) 