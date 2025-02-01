class GPURateLimiter:
    def __init__(self):
        self.redis = RedisRateLimiter(
            limits={
                "image_512": {"cost": 2, "limit": 100},
                "video_1080p": {"cost": 10, "limit": 20}
            }
        )

    async def __call__(self, request: Request):
        user_id = request.state.user.id
        endpoint = request.url.path
        cost = self.get_endpoint_cost(endpoint)
        
        if not await self.redis.check_limit(user_id, cost):
            raise HTTPException(429, "GPU quota exceeded") 