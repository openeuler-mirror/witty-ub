#include "urma_failure_720.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure720> g_urma("urma_720");

bool UrmaFailure720::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_rearm_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to rearm jfc: JFCE is NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure720::GetName() const
{
    return "执行JFC过程中依赖步骤失败";
}

std::string UrmaFailure720::GetRootCauseDesc() const
{
    return "函数用于执行JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure720::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure720::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure720::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_rearm_jfc，Failed to rearm jfc: JFCE is NULL";
}

std::string UrmaFailure720::GetId() const
{
    return "urma_720";
}

} // namespace diag
