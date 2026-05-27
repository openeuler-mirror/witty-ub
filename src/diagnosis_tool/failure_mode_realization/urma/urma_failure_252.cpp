#include "urma_failure_252.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure252> g_urma("urma_252");

bool UrmaFailure252::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty_async' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Not "
        "allowed to bind local jetty:' | grep -F 'of mode:' | grep -F 'with remote jetty:' | grep -F 'of mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure252::GetName() const
{
    return "绑定Jetty过程中依赖步骤失败";
}

std::string UrmaFailure252::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure252::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure252::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure252::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_async，Not allowed to bind local jetty:，of mode:，with "
           "remote jetty:，of mode:。";
}

std::string UrmaFailure252::GetId() const
{
    return "urma_252";
}

} // namespace diag
