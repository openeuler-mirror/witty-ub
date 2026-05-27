#include "urma_failure_452.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure452> g_urma("urma_452");

bool UrmaFailure452::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfc_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->get_jfc_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure452::GetName() const
{
    return "获取JFC过程中依赖步骤失败";
}

std::string UrmaFailure452::GetRootCauseDesc() const
{
    return "函数用于获取JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure452::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure452::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure452::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfc_opt，Failed to exec ops->get_jfc_opt.。";
}

std::string UrmaFailure452::GetId() const
{
    return "urma_452";
}

} // namespace diag
