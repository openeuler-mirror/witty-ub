#include "urma_failure_189.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure189> g_urma("urma_189");

bool UrmaFailure189::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_add_jetty_to_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'failed to add jetty to jetty_grp.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure189::GetName() const
{
    return "删除Jetty过程中依赖步骤失败";
}

std::string UrmaFailure189::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure189::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure189::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure189::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_add_jetty_to_jetty_grp，failed to add jetty to jetty_grp.";
}

std::string UrmaFailure189::GetId() const
{
    return "urma_189";
}

} // namespace diag
