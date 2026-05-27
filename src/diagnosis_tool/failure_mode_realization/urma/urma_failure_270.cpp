#include "urma_failure_270.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure270> g_urma("urma_270");

bool UrmaFailure270::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'UB dev should use share jfr!'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure270::GetName() const
{
    return "设置设备过程中依赖步骤失败";
}

std::string UrmaFailure270::GetRootCauseDesc() const
{
    return "函数用于设置设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure270::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure270::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure270::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，UB dev should use share jfr!。";
}

std::string UrmaFailure270::GetId() const
{
    return "urma_270";
}

} // namespace diag
