#include "urma_failure_783.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure783> g_urma("urma_783");

bool UrmaFailure783::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->active_jfc.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure783::GetName() const
{
    return "激活JFC过程中依赖步骤失败";
}

std::string UrmaFailure783::GetRootCauseDesc() const
{
    return "函数用于激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure783::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure783::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure783::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfc，Failed to exec ops->active_jfc.。";
}

std::string UrmaFailure783::GetId() const
{
    return "urma_783";
}

} // namespace diag
