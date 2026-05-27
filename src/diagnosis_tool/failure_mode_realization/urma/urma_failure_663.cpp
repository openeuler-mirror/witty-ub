#include "urma_failure_663.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure663> g_urma("urma_663");

bool UrmaFailure663::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete jfs batch.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure663::GetName() const
{
    return "JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure663::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure663::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure663::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure663::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfs_batch，Failed to delete jfs batch.";
}

std::string UrmaFailure663::GetId() const
{
    return "urma_663";
}

} // namespace diag
