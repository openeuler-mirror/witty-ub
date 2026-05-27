#include "urma_failure_871.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure871> g_urma("urma_871");

bool UrmaFailure871::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_open_drivers' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'snprintf_s' | grep -F 'failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure871::GetName() const
{
    return "打开URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure871::GetRootCauseDesc() const
{
    return "函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure871::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure871::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure871::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，snprintf_s，failed。";
}

std::string UrmaFailure871::GetId() const
{
    return "urma_871";
}

} // namespace diag
