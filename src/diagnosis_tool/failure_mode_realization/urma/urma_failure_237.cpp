#include "urma_failure_237.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure237> g_urma("urma_237");

bool UrmaFailure237::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unbind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Not "
        "allowed to call unbind as the tp mode of jetty :' | grep -F 'is:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure237::GetName() const
{
    return "解绑TP过程中依赖步骤失败";
}

std::string UrmaFailure237::GetRootCauseDesc() const
{
    return "函数用于解绑TP，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure237::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure237::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure237::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unbind_jetty，Not allowed to call unbind as the tp mode of jetty "
           ":，is:。";
}

std::string UrmaFailure237::GetId() const
{
    return "urma_237";
}

} // namespace diag
