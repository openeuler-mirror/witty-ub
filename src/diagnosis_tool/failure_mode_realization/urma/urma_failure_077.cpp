#include "urma_failure_077.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure077> g_urma("urma_077");

bool UrmaFailure077::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete vjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure077::GetName() const
{
    return "虚拟 Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure077::GetRootCauseDesc() const
{
    return "函数负责释放或撤销虚拟 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure077::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure077::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure077::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jetty，Failed to delete vjetty";
}

std::string UrmaFailure077::GetId() const
{
    return "urma_077";
}

} // namespace diag
