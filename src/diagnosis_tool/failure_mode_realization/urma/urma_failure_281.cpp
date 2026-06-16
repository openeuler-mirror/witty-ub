#include "urma_failure_281.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure281> g_urma("urma_281");

bool UrmaFailure281::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfc or jfr has not activated.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure281::GetName() const
{
    return "激活JFC过程中依赖步骤失败";
}

std::string UrmaFailure281::GetRootCauseDesc() const
{
    return "函数用于激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure281::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure281::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure281::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，jfc or jfr has not activated.。";
}

std::string UrmaFailure281::GetId() const
{
    return "urma_281";
}

} // namespace diag
