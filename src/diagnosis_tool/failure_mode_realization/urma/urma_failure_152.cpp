#include "urma_failure_152.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure152> g_urma("urma_152");

bool UrmaFailure152::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty->jetty_cfg.shared.jfr is not exist'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure152::GetName() const
{
    return "设置Jetty过程中依赖步骤失败";
}

std::string UrmaFailure152::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure152::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure152::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure152::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jetty_opt，jetty->jetty_cfg.shared.jfr is not exist";
}

std::string UrmaFailure152::GetId() const
{
    return "urma_152";
}

} // namespace diag
