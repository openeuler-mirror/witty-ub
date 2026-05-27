#include "urma_failure_789.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure789> g_urma("urma_789");

bool UrmaFailure789::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec urma_jfr_set_options.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure789::GetName() const
{
    return "设置JFR过程中依赖步骤失败";
}

std::string UrmaFailure789::GetRootCauseDesc() const
{
    return "函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure789::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure789::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure789::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfs_opt，Failed to exec urma_jfr_set_options.";
}

std::string UrmaFailure789::GetId() const
{
    return "urma_789";
}

} // namespace diag
