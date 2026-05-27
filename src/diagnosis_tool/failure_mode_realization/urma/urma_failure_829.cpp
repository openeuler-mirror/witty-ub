#include "urma_failure_829.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure829> g_urma("urma_829");

bool UrmaFailure829::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->active_jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure829::GetName() const
{
    return "激活JFR过程中依赖步骤失败";
}

std::string UrmaFailure829::GetRootCauseDesc() const
{
    return "函数用于激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure829::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure829::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure829::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfr，Failed to exec ops->active_jfr.。";
}

std::string UrmaFailure829::GetId() const
{
    return "urma_829";
}

} // namespace diag
