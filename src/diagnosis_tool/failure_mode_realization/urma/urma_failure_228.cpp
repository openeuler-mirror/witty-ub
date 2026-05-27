#include "urma_failure_228.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure228> g_urma("urma_228");

bool UrmaFailure228::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Not allowed to bind local jetty:' | grep -F 'of mode:' | grep -F 'with remote jetty:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure228::GetName() const
{
    return "绑定Jetty过程中依赖步骤失败";
}

std::string UrmaFailure228::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure228::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure228::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure228::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_bind_jetty，Not allowed to bind local jetty:，of mode:，with remote jetty:";
}

std::string UrmaFailure228::GetId() const
{
    return "urma_228";
}

} // namespace diag
