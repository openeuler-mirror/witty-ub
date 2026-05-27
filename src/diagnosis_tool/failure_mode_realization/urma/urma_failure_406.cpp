#include "urma_failure_406.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure406> g_urma("urma_406");

bool UrmaFailure406::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to free token_id, dev_name:' | grep -F ', eid_idx:' | grep -F ', tid:' | "
        "grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure406::GetName() const
{
    return "Token清理阶段下层释放操作失败";
}

std::string UrmaFailure406::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Token相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure406::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure406::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure406::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_token_id，[DRV_ERR]Failed to free token_id, dev_name:，, eid_idx:，, "
           "tid:，, ret:";
}

std::string UrmaFailure406::GetId() const
{
    return "urma_406";
}

} // namespace diag
