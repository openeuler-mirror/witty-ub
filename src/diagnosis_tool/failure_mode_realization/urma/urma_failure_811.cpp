#include "urma_failure_811.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure811> g_urma("urma_811");

bool UrmaFailure811::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to set opt, jfr has been activated'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure811::GetName() const
{
    return "设置JFR过程中依赖步骤失败";
}

std::string UrmaFailure811::GetRootCauseDesc() const
{
    return "函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure811::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure811::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure811::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfr_opt，Failed to set opt, jfr has been activated";
}

std::string UrmaFailure811::GetId() const
{
    return "urma_811";
}

} // namespace diag
