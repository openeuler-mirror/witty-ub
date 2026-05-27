#include "urma_failure_670.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure670> g_urma("urma_670");

bool UrmaFailure670::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete jfs batch.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure670::GetName() const
{
    return "JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure670::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure670::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure670::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure670::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Failed to delete jfs batch.。";
}

std::string UrmaFailure670::GetId() const
{
    return "urma_670";
}

} // namespace diag
