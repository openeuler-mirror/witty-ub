#include "urma_failure_605.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure605> g_urma("urma_605");

bool UrmaFailure605::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete pcontext'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure605::GetName() const
{
    return "context清理阶段下层释放操作失败";
}

std::string UrmaFailure605::GetRootCauseDesc() const
{
    return "函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure605::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure605::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure605::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_context，Failed to delete pcontext";
}

std::string UrmaFailure605::GetId() const
{
    return "urma_605";
}

} // namespace diag
