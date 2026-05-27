#include "urma_failure_088.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure088> g_urma("urma_088");

bool UrmaFailure088::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_bind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'No valid active slice to bind'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure088::GetName() const
{
    return "未找到可用于激活Jetty的有效对象或路由";
}

std::string UrmaFailure088::GetRootCauseDesc() const
{
    return "函数在激活Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure088::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure088::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure088::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_bind_jetty，No valid active slice to bind";
}

std::string UrmaFailure088::GetId() const
{
    return "urma_088";
}

} // namespace diag
