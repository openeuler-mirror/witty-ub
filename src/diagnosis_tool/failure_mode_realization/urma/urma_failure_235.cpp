#include "urma_failure_235.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure235> g_urma("urma_235");

bool UrmaFailure235::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unbind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Not allowed to call unbind as the tp mode of jetty :' | grep -F 'is:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure235::GetName() const
{
    return "解绑TP过程中依赖步骤失败";
}

std::string UrmaFailure235::GetRootCauseDesc() const
{
    return "函数用于解绑TP，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure235::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure235::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure235::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unbind_jetty，Not allowed to call unbind as the tp mode of jetty :，is:";
}

std::string UrmaFailure235::GetId() const
{
    return "urma_235";
}

} // namespace diag
