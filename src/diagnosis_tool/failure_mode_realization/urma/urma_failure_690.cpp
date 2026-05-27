#include "urma_failure_690.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure690> g_urma("urma_690");

bool UrmaFailure690::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_notifier' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete notifier, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure690::GetName() const
{
    return "Notifier清理阶段下层释放操作失败";
}

std::string UrmaFailure690::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Notifier相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure690::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure690::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure690::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_notifier，Failed to delete notifier, ret:。";
}

std::string UrmaFailure690::GetId() const
{
    return "urma_690";
}

} // namespace diag
