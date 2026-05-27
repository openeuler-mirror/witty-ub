#include "urma_failure_521.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure521> g_urma("urma_521");

bool UrmaFailure521::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unregister_seg_inner' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed to delete pseg for vseg, token_id:' | grep -F ', handle:' | grep -F 'u.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure521::GetName() const
{
    return "Token清理阶段下层释放操作失败";
}

std::string UrmaFailure521::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Token相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure521::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure521::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure521::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unregister_seg_inner，Failed to delete pseg for vseg, "
           "token_id:，, handle:，u.。";
}

std::string UrmaFailure521::GetId() const
{
    return "urma_521";
}

} // namespace diag
