#include "urma_failure_417.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure417> g_urma("urma_417");

bool UrmaFailure417::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'resend_jfs_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get comp, local_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure417::GetName() const
{
    return "获取组件过程中依赖步骤失败";
}

std::string UrmaFailure417::GetRootCauseDesc() const
{
    return "函数用于获取组件，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure417::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure417::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure417::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：resend_jfs_wr，Failed to get comp, local_id:";
}

std::string UrmaFailure417::GetId() const
{
    return "urma_417";
}

} // namespace diag
