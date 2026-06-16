#include "urma_failure_858.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure858> g_urma("urma_858");

bool UrmaFailure858::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_user_ctl' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to excecute user_ctl, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure858::GetName() const
{
    return "执行context过程中依赖步骤失败";
}

std::string UrmaFailure858::GetRootCauseDesc() const
{
    return "函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure858::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure858::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure858::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_user_ctl，Failed to excecute user_ctl, ret:。";
}

std::string UrmaFailure858::GetId() const
{
    return "urma_858";
}

} // namespace diag
