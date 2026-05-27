#include "urma_failure_606.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure606> g_urma("urma_606");

bool UrmaFailure606::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete vcontext'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure606::GetName() const
{
    return "context清理阶段下层释放操作失败";
}

std::string UrmaFailure606::GetRootCauseDesc() const
{
    return "函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure606::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure606::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure606::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_context，Failed to delete vcontext";
}

std::string UrmaFailure606::GetId() const
{
    return "urma_606";
}

} // namespace diag
