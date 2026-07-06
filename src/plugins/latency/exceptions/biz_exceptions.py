class BaseBizException(Exception):
    """业务异常基类"""
    def __init__(self, message: str, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class NotFoundBizException(BaseBizException):
    """资源不存在异常 (404)"""
    def __init__(self, resource: str = "资源", detail: str = ""):
        super().__init__(f"{resource}不存在", detail)


class ConflictBizException(BaseBizException):
    """状态冲突异常 (409)"""
    def __init__(self, message: str = "操作状态冲突", detail: str = ""):
        super().__init__(message, detail)


class BadRequestBizException(BaseBizException):
    """请求参数错误异常 (400)"""
    def __init__(self, message: str = "请求参数错误", detail: str = ""):
        super().__init__(message, detail)
