#include "urma_failure_089.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure089> g_urma("urma_089");

bool UrmaFailure089::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unbind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to unbind tjetty ['");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure089::GetName() const
{
    return "解绑Jetty过程中依赖步骤失败";
}

std::string UrmaFailure089::GetRootCauseDesc() const
{
    return "函数用于解绑Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure089::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure089::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure089::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unbind_jetty，Failed to unbind tjetty [";
}

std::string UrmaFailure089::GetId() const
{
    return "urma_089";
}

} // namespace diag
