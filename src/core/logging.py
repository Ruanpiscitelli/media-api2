class GPULogFilter(logging.Filter):
    def filter(self, record):
        record.gpu_stats = gpu_manager.get_status()
        return True 