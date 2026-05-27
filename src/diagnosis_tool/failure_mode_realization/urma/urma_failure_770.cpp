#include "urma_failure_770.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure770> g_urma("urma_770");

bool UrmaFailure770::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec urma_jfc_set_options.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure770::GetName() const
{
    return "设置JFC过程中依赖步骤失败";
}

std::string UrmaFailure770::GetRootCauseDesc() const
{
    return "函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure770::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure770::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure770::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfc_opt，Failed to exec urma_jfc_set_options.";
}

std::string UrmaFailure770::GetId() const
{
    return "urma_770";
}

} // namespace diag
