#include "urma_failure_234.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure234> g_urma("urma_234");

bool UrmaFailure234::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty_ex' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Not "
        "allowed to bind local jetty:' | grep -F ', with remote jetty:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure234::GetName() const
{
    return "绑定Jetty过程中依赖步骤失败";
}

std::string UrmaFailure234::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure234::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure234::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure234::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_ex，Not allowed to bind local jetty:，, with remote "
           "jetty:。";
}

std::string UrmaFailure234::GetId() const
{
    return "urma_234";
}

} // namespace diag
