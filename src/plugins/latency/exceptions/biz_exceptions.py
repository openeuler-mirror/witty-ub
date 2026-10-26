class BaseBizException(Exception):
    """业务异常基类"""
    def __init__(self, message: str, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class NotFoundBizException(BaseBizException):
    """资源不存在异常"""
    def __init__(self, resource: str = "资源", detail: str = ""):
        super().__init__(f"{resource}不存在", detail)


class ConflictBizException(BaseBizException):
    """状态冲突异常"""
    def __init__(self, message: str = "操作状态冲突", detail: str = ""):
        super().__init__(message, detail)


class BadRequestBizException(BaseBizException):
    """请求参数错误异常"""
    def __init__(self, message: str = "请求参数错误", detail: str = ""):
        super().__init__(message, detail)


class UnprocessableBizException(BaseBizException):
    """资源存在但数据不完整，无法完成操作"""
    def __init__(self, message: str = "资源数据不完整", detail: str = ""):
        super().__init__(message, detail)


class UpstreamContractBizException(BaseBizException):
    """上游依赖返回了不符合冻结契约的响应"""
    def __init__(self, message: str = "上游响应契约错误", detail: str = ""):
        self.retryable = False
        super().__init__(message, detail)


class DependencyUnavailableBizException(BaseBizException):
    """上游依赖不可用，调用方可退避重试"""
    def __init__(self, message: str = "依赖服务暂时不可用", detail: str = ""):
        self.retryable = True
        super().__init__(message, detail)


class FeatureDisabledBizException(BaseBizException):
    """功能灰度未开启"""
    def __init__(self, message: str = "功能未启用", detail: str = ""):
        self.retryable = False
        super().__init__(message, detail)
