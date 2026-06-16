#include "urma_failure_256.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure256> g_urma("urma_256");

bool UrmaFailure256::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unbind_jetty_async' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Not "
        "allowed to call unbind as the tp mode of jetty :' | grep -F 'is:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure256::GetName() const
{
    return "解绑TP过程中依赖步骤失败";
}

std::string UrmaFailure256::GetRootCauseDesc() const
{
    return "函数用于解绑TP，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure256::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure256::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure256::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unbind_jetty_async，Not allowed to call unbind as the tp mode of "
           "jetty :，is:。";
}

std::string UrmaFailure256::GetId() const
{
    return "urma_256";
}

} // namespace diag
