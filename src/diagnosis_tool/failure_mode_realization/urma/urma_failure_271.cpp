#include "urma_failure_271.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure271> g_urma("urma_271");

bool UrmaFailure271::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->set_jetty_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure271::GetName() const
{
    return "设置Jetty过程中依赖步骤失败";
}

std::string UrmaFailure271::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure271::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure271::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure271::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to exec ops->set_jetty_opt.。";
}

std::string UrmaFailure271::GetId() const
{
    return "urma_271";
}

} // namespace diag
