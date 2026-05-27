#include "urma_failure_153.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure153> g_urma("urma_153");

bool UrmaFailure153::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jetty->jetty_cfg.shared.jfc is not exist'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure153::GetName() const
{
    return "设置Jetty过程中依赖步骤失败";
}

std::string UrmaFailure153::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure153::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure153::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure153::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jetty_opt，jetty->jetty_cfg.shared.jfc is not exist。";
}

std::string UrmaFailure153::GetId() const
{
    return "urma_153";
}

} // namespace diag
