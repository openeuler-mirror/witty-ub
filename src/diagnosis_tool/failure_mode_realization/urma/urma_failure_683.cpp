#include "urma_failure_683.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure683> g_urma("urma_683");

bool UrmaFailure683::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_notifier' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete notifier, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure683::GetName() const
{
    return "Notifier清理阶段下层释放操作失败";
}

std::string UrmaFailure683::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Notifier相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure683::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure683::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure683::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_notifier，Failed to delete notifier, ret:";
}

std::string UrmaFailure683::GetId() const
{
    return "urma_683";
}

} // namespace diag
