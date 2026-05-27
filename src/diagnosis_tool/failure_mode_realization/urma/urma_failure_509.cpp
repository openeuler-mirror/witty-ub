#include "urma_failure_509.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure509> g_urma("urma_509");

bool UrmaFailure509::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_vseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to unregister segment, token_id:' | grep -F ', handle:' | grep -F 'u.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure509::GetName() const
{
    return "Segment清理阶段下层释放操作失败";
}

std::string UrmaFailure509::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure509::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure509::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure509::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_vseg，Failed to unregister segment, token_id:，, handle:，u.";
}

std::string UrmaFailure509::GetId() const
{
    return "urma_509";
}

} // namespace diag
