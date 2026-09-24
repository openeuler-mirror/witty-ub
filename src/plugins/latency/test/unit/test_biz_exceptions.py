# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.exceptions.biz_exceptions 单元测试。"""
import pytest

from latency.exceptions.biz_exceptions import (
    BadRequestBizException,
    BaseBizException,
    ConflictBizException,
    NotFoundBizException,
)


class TestBaseBizException:
    def test_message_and_detail(self):
        exc = BaseBizException("oops", "some detail")
        assert exc.message == "oops"
        assert exc.detail == "some detail"

    def test_str_returns_message(self):
        exc = BaseBizException("oops")
        assert str(exc) == "oops"

    def test_default_detail(self):
        assert BaseBizException("m").detail == ""

    def test_is_exception(self):
        with pytest.raises(BaseBizException):
            raise BaseBizException("boom")


class TestNotFoundBizException:
    def test_default(self):
        exc = NotFoundBizException()
        assert exc.message == "资源不存在"

    def test_custom_resource(self):
        exc = NotFoundBizException("日志文件")
        assert exc.message == "日志文件不存在"


class TestConflictBizException:
    def test_default(self):
        exc = ConflictBizException()
        assert exc.message == "操作状态冲突"

    def test_custom(self):
        exc = ConflictBizException("任务正在运行")
        assert exc.message == "任务正在运行"


class TestBadRequestBizException:
    def test_default(self):
        exc = BadRequestBizException()
        assert exc.message == "请求参数错误"

    def test_custom(self):
        exc = BadRequestBizException("时间格式非法")
        assert exc.message == "时间格式非法"

    def test_inheritance_chain(self):
        exc = BadRequestBizException()
        assert isinstance(exc, BaseBizException)
        assert isinstance(exc, Exception)
