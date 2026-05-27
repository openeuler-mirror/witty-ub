#include "urma_failure_511.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure511> g_urma("urma_511");

bool UrmaFailure511::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pseg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to unregister pseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure511::GetName() const
{
    return "Segment清理阶段下层释放操作失败";
}

std::string UrmaFailure511::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure511::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure511::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure511::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pseg，Failed to unregister pseg。";
}

std::string UrmaFailure511::GetId() const
{
    return "urma_511";
}

} // namespace diag
