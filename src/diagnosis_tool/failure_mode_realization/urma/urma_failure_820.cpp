#include "urma_failure_820.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure820> g_urma("urma_820");

bool UrmaFailure820::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to set opt, jfr has been activated'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure820::GetName() const
{
    return "设置JFR过程中依赖步骤失败";
}

std::string UrmaFailure820::GetRootCauseDesc() const
{
    return "函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure820::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure820::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure820::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，Failed to set opt, jfr has been activated。";
}

std::string UrmaFailure820::GetId() const
{
    return "urma_820";
}

} // namespace diag
