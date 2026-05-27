#include "urma_failure_275.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure275> g_urma("urma_275");

bool UrmaFailure275::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->get_jetty_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure275::GetName() const
{
    return "获取Jetty过程中依赖步骤失败";
}

std::string UrmaFailure275::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure275::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure275::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure275::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jetty_opt，Failed to exec ops->get_jetty_opt.。";
}

std::string UrmaFailure275::GetId() const
{
    return "urma_275";
}

} // namespace diag
