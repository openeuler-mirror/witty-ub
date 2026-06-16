#include "urma_failure_520.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure520> g_urma("urma_520");

bool UrmaFailure520::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unregister_seg_inner' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed to delete vseg, token_id:' | grep -F ', handle:' | grep -F 'u.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure520::GetName() const
{
    return "Token清理阶段下层释放操作失败";
}

std::string UrmaFailure520::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Token相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure520::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure520::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure520::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unregister_seg_inner，Failed to delete vseg, token_id:，, "
           "handle:，u.。";
}

std::string UrmaFailure520::GetId() const
{
    return "urma_520";
}

} // namespace diag
