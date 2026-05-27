#include "urma_failure_506.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure506> g_urma("urma_506");

bool UrmaFailure506::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to unregister pseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure506::GetName() const
{
    return "Segment清理阶段下层释放操作失败";
}

std::string UrmaFailure506::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure506::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure506::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure506::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_pseg，Failed to unregister pseg";
}

std::string UrmaFailure506::GetId() const
{
    return "urma_506";
}

} // namespace diag
